from __future__ import annotations

import base64
import io
import threading
import uuid
from typing import Optional
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from fetch_logo import fetch_logo
from names import display_name
import store
from fill import (
    ascii_filename,
    fill_deck,
    fill_from_csv,
    get_template,
    links_csv,
    load_catalog,
    pack_selected,
    render_filename,
    unpack_logo_zip,
)
from poster import fill_poster, fill_posters_from_csv, poster_filename

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = FastAPI(title="Презентации для партнёров")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

JOBS: dict[str, dict] = {}
FILLS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
BUSY_LOCK = threading.Lock()
BUSY: dict = {
    "on": False,
    "kind": "",
    "done": 0,
    "total": 0,
    "token": "",
}

SEC = {"fill": 7, "share": 5}


def _ru_wait(sec: int) -> str:
    sec = max(0, int(sec))
    if sec <= 20:
        return "около 20 секунд"
    if sec < 50:
        return "меньше минуты"
    n = max(1, round(sec / 60))
    mod10, mod100 = n % 10, n % 100
    if mod10 == 1 and mod100 != 11:
        unit = "минуту"
    elif mod10 in (2, 3, 4) and mod100 not in (12, 13, 14):
        unit = "минуты"
    else:
        unit = "минут"
    return f"около {n} {unit}"


def _busy_snapshot() -> dict:
    with BUSY_LOCK:
        if not BUSY["on"]:
            return {"busy": False, "wait_sec": 0, "message": "", "token": ""}
        kind = BUSY["kind"]
        done = int(BUSY["done"] or 0)
        total = int(BUSY["total"] or 0)
        left = max(0, total - done)
        wait = left * SEC.get(kind, 7)
        if kind == "share":
            action = "заливает ссылки"
        else:
            action = "собирает презентации"
        if total:
            msg = (
                f"Коллега сейчас {action} ({done} из {total}). "
                f"Подожди {_ru_wait(wait)}."
            )
        else:
            msg = f"Коллега сейчас {action}. Подожди {_ru_wait(max(wait, 20))}."
        return {
            "busy": True,
            "wait_sec": wait,
            "message": msg,
            "token": BUSY["token"],
            "done": done,
            "total": total,
            "kind": kind,
        }


def _busy_acquire(kind: str, total: int) -> str | None:
    with BUSY_LOCK:
        if BUSY["on"]:
            return None
        token = uuid.uuid4().hex
        BUSY.update(on=True, kind=kind, done=0, total=max(0, int(total)), token=token)
        return token


def _busy_progress(done: int, total: int | None = None) -> None:
    with BUSY_LOCK:
        if not BUSY["on"]:
            return
        BUSY["done"] = done
        if total is not None:
            BUSY["total"] = total


def _busy_release(token: str | None = None) -> None:
    with BUSY_LOCK:
        if token and BUSY.get("token") and token != BUSY["token"]:
            return
        BUSY.update(on=False, kind="", done=0, total=0, token="")


class PackBody(BaseModel):
    skip: list[int] = []


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC / "index.html").read_text()


@app.get("/busy")
def busy_status():
    return _busy_snapshot()


@app.get("/templates")
def templates():
    return JSONResponse(load_catalog())


def _person(name: str, company: str) -> str:
    return (name or company or "").strip()


def _disposition(filename: str) -> str:
    return (
        f'attachment; filename="{ascii_filename(filename)}"; '
        f"filename*=UTF-8''{quote(filename)}"
    )


@app.post("/fill")
async def fill_one(
    name: str = Form(""),
    company: str = Form(""),
    template: str = Form("media-partner"),
    photo: Optional[UploadFile] = File(None),
    logo: Optional[UploadFile] = File(None),
    url: str = Form(""),
    filename_pattern: str = Form(""),
):
    person = _person(name, company)
    if not person:
        raise HTTPException(400, "укажи имя или название компании")
    try:
        item = get_template(template)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(400, str(e)) from e
    image = None
    chosen = photo if (photo is not None and photo.filename) else logo
    if chosen is not None and chosen.filename:
        image = io.BytesIO(await chosen.read())
    elif url.strip():
        try:
            image = fetch_logo(url)
        except Exception as e:
            raise HTTPException(400, str(e)) from e
    token = _busy_acquire("fill", 1)
    if not token:
        raise HTTPException(409, _busy_snapshot()["message"])
    try:
        _busy_progress(0, 1)
        data, preview = fill_deck(person, logo=image, template=item["path"])
        _busy_progress(1, 1)
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    finally:
        _busy_release(token)
    shown = display_name(person) or person
    filename = render_filename(
        filename_pattern,
        name=shown,
        template=item["label"],
    )
    fill_id = uuid.uuid4().hex
    FILLS[fill_id] = {
        "pdf": data,
        "filename": filename,
        "preview": preview,
        "template_id": template,
        "content_type": "application/pdf",
    }
    return JSONResponse(
        {
            "id": fill_id,
            "name": shown,
            "filename": filename,
            "preview": "data:image/jpeg;base64," + base64.b64encode(preview).decode(),
        }
    )


@app.get("/fill/{fill_id}/download")
def fill_download(fill_id: str):
    item = FILLS.get(fill_id)
    if not item:
        raise HTTPException(404, "превью уже не доступно — собери ещё раз")
    return Response(
        item["pdf"],
        media_type=item.get("content_type") or "application/pdf",
        headers={"Content-Disposition": _disposition(item["filename"])},
    )


def _set_job(job_id: str, **fields) -> None:
    with JOBS_LOCK:
        JOBS[job_id].update(fields)


@app.post("/batch/start")
async def batch_start(
    csv_file: UploadFile = File(...),
    template: str = Form("media-partner"),
    photos_zip: Optional[UploadFile] = File(None),
    logos_zip: Optional[UploadFile] = File(None),
    filename_pattern: str = Form(""),
):
    try:
        item = get_template(template)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(400, str(e)) from e
    csv_text = (await csv_file.read()).decode("utf-8-sig")
    z = photos_zip if (photos_zip is not None and photos_zip.filename) else logos_zip
    logos_map = {}
    if z is not None and z.filename:
        logos_map = unpack_logo_zip(await z.read())

    approx = max(csv_text.count("\n") - 1, 0)
    token = _busy_acquire("fill", approx)
    if not token:
        raise HTTPException(409, _busy_snapshot()["message"])
    job_id = uuid.uuid4().hex
    zip_name = render_filename(
        filename_pattern, name=item["label"], template=item["label"]
    ).replace(".pdf", ".zip")
    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": "running",
            "done": 0,
            "total": max(csv_text.count("\n") - 1, 0),
            "current": "начинаем",
            "failed": [],
            "zip_name": zip_name,
            "previews": [],
            "fieldnames": [],
            "rows": [],
            "error": "",
            "share_status": "idle",
            "share_done": 0,
            "share_total": 0,
            "share_current": "",
            "share_error": "",
            "share_csv": b"",
            "share_csv_name": "links.csv",
            "template_id": item["id"],
            "content_type": "application/pdf",
        }

    def run() -> None:
        try:

            def progress(done, total, name):
                _set_job(job_id, done=done, total=total, current=name)
                _busy_progress(done, total)

            failed, previews, fieldnames, rows = fill_from_csv(
                io.StringIO(csv_text),
                logos_map=logos_map,
                template=item["path"],
                template_label=item["label"],
                name_pattern=filename_pattern,
                on_progress=progress,
            )
            _set_job(
                job_id,
                status="done",
                failed=failed,
                previews=previews,
                fieldnames=fieldnames,
                rows=rows,
                current="готово",
            )
        except Exception as e:
            _set_job(job_id, status="error", error=str(e), current="")
        finally:
            _busy_release(token)

    threading.Thread(target=run, daemon=True).start()
    return JSONResponse({"job_id": job_id, "token": token})


@app.get("/batch/{job_id}")
def batch_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            raise HTTPException(404, "задача не найдена")
        return {
            "status": job["status"],
            "done": job["done"],
            "total": job["total"],
            "current": job["current"],
            "failed": [
                {"name": f.get("name"), "url": f.get("url"), "reason": f.get("reason")}
                for f in (job["failed"] or [])
            ],
            "error": job["error"],
            "ok": job["total"] - len(job["failed"]) if job["status"] == "done" else job["done"],
            "previews": [
                {"name": p["name"], "index": i}
                for i, p in enumerate(job.get("previews") or [])
            ]
            if job["status"] == "done"
            else [],
            "share_status": job.get("share_status") or "idle",
            "share_done": job.get("share_done") or 0,
            "share_total": job.get("share_total") or 0,
            "share_current": job.get("share_current") or "",
            "share_error": job.get("share_error") or "",
        }


@app.get("/batch/{job_id}/preview/{index}")
def batch_preview(job_id: str, index: int):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job or job["status"] != "done":
            raise HTTPException(404, "превью ещё не готово")
        previews = job.get("previews") or []
        if index < 0 or index >= len(previews):
            raise HTTPException(404, "нет такого превью")
        data = previews[index]["jpeg"]
    return Response(data, media_type="image/jpeg")


@app.get("/storage")
def storage_status():
    return {"ok": store.configured(), "base": store.public_base() if store.configured() else ""}


@app.get("/posters")
def posters():
    return JSONResponse(
        [
            {
                "id": "media-partner",
                "label": "Медиапартнёр",
                "note": "MVP по примеру 1:1 Pitch Conf. Остальные роли — когда будут шаблоны.",
            }
        ]
    )


@app.post("/poster/fill")
async def poster_fill(
    company: str = Form(""),
    name: str = Form(""),
    url: str = Form(""),
    promo: str = Form(""),
    website: str = Form(""),
    logo: Optional[UploadFile] = File(None),
    photo: Optional[UploadFile] = File(None),
    filename_pattern: str = Form(""),
):
    person = display_name((company or name or "").strip()) or (company or name or "").strip()
    if not person:
        raise HTTPException(400, "укажи название компании")
    image = None
    chosen = logo if (logo is not None and logo.filename) else photo
    if chosen is not None and chosen.filename:
        image = io.BytesIO(await chosen.read())
    elif website.strip():
        try:
            image = fetch_logo(website)
        except Exception as e:
            raise HTTPException(400, str(e)) from e
    token = _busy_acquire("fill", 1)
    if not token:
        raise HTTPException(409, _busy_snapshot()["message"])
    try:
        _busy_progress(0, 1)
        data, preview, meta = fill_poster(
            person, logo=image, url=url, promo=promo
        )
        _busy_progress(1, 1)
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    finally:
        _busy_release(token)
    filename = poster_filename(filename_pattern, person)
    fill_id = uuid.uuid4().hex
    FILLS[fill_id] = {
        "pdf": data,
        "filename": filename,
        "preview": preview,
        "template_id": "poster-mp",
        "content_type": "image/png",
        "meta": meta,
    }
    return JSONResponse(
        {
            "id": fill_id,
            "name": person,
            "filename": filename,
            "track_url": meta["url"],
            "promo": meta["promo"],
            "preview": "data:image/jpeg;base64," + base64.b64encode(preview).decode(),
        }
    )


@app.post("/poster/batch/start")
async def poster_batch_start(
    csv_file: UploadFile = File(...),
    photos_zip: Optional[UploadFile] = File(None),
    logos_zip: Optional[UploadFile] = File(None),
    filename_pattern: str = Form(""),
):
    csv_text = (await csv_file.read()).decode("utf-8-sig")
    z = photos_zip if (photos_zip is not None and photos_zip.filename) else logos_zip
    logos_map = {}
    if z is not None and z.filename:
        logos_map = unpack_logo_zip(await z.read())
    approx = max(csv_text.count("\n") - 1, 0)
    token = _busy_acquire("fill", approx)
    if not token:
        raise HTTPException(409, _busy_snapshot()["message"])
    job_id = uuid.uuid4().hex
    zip_name = poster_filename(
        filename_pattern or "VC Conf posters — {name}.png", "медиапартнёр"
    ).replace(".png", ".zip")
    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": "running",
            "done": 0,
            "total": approx,
            "current": "начинаем",
            "failed": [],
            "zip_name": zip_name,
            "previews": [],
            "fieldnames": [],
            "rows": [],
            "error": "",
            "share_status": "idle",
            "share_done": 0,
            "share_total": 0,
            "share_current": "",
            "share_error": "",
            "share_csv": b"",
            "share_csv_name": "poster-links.csv",
            "template_id": "poster-mp",
            "content_type": "image/png",
        }

    def run() -> None:
        try:

            def progress(done, total, name):
                _set_job(job_id, done=done, total=total, current=name)
                _busy_progress(done, total)

            failed, previews, fieldnames, rows = fill_posters_from_csv(
                io.StringIO(csv_text),
                logos_map=logos_map,
                on_progress=progress,
            )
            _set_job(
                job_id,
                status="done",
                failed=failed,
                previews=previews,
                fieldnames=fieldnames,
                rows=rows,
                current="готово",
            )
        except Exception as e:
            _set_job(job_id, status="error", error=str(e), current="")
        finally:
            _busy_release(token)

    threading.Thread(target=run, daemon=True).start()
    return JSONResponse({"job_id": job_id, "token": token})


@app.post("/fill/{fill_id}/share")
def fill_share(fill_id: str):
    item = FILLS.get(fill_id)
    if not item:
        raise HTTPException(404, "превью уже не доступно — собери ещё раз")
    if not store.configured():
        raise HTTPException(400, store.MISSING)
    key = store.object_key(item["filename"], item.get("template_id") or "decks")
    token = _busy_acquire("share", 1)
    if not token:
        raise HTTPException(409, _busy_snapshot()["message"])
    try:
        url = store.put_file(
            key,
            item["pdf"],
            item["filename"],
            item.get("content_type") or "application/pdf",
        )
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    finally:
        _busy_release(token)
    return {"url": url, "filename": item["filename"]}


@app.post("/batch/{job_id}/share")
def batch_share(job_id: str, body: PackBody):
    if not store.configured():
        raise HTTPException(400, store.MISSING)
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job or job["status"] != "done":
            raise HTTPException(404, "ещё не готово")
        if job.get("share_status") == "running":
            raise HTTPException(409, "уже заливаем")
        previews = list(job.get("previews") or [])
        rows = list(job.get("rows") or [])
        fieldnames = list(job.get("fieldnames") or [])
        zip_name = job["zip_name"]
        folder = job.get("template_id") or "decks"
        content_type = job.get("content_type") or "application/pdf"
        skip_set = set(body.skip)
        todo = [p for i, p in enumerate(previews) if i not in skip_set]
        job["share_status"] = "running"
        job["share_done"] = 0
        job["share_total"] = len(todo)
        job["share_current"] = "начинаем"
        job["share_error"] = ""
        job["share_csv"] = b""
    token = _busy_acquire("share", len(todo))
    if not token:
        with JOBS_LOCK:
            job["share_status"] = "idle"
        raise HTTPException(409, _busy_snapshot()["message"])

    def run() -> None:
        urls: dict[int, str] = {}
        try:
            for n, item in enumerate(todo, start=1):
                _set_job(job_id, share_current=item.get("name") or item["filename"], share_done=n - 1)
                _busy_progress(n - 1, len(todo))
                key = store.object_key(item["filename"], folder)
                urls[int(item["row_index"])] = store.put_file(
                    key, item["pdf"], item["filename"], content_type
                )
                _set_job(job_id, share_done=n)
                _busy_progress(n, len(todo))
            csv_name = zip_name.replace(".zip", "-links.csv")
            if not csv_name.endswith(".csv"):
                csv_name = "links.csv"
            extras: dict[int, dict] = {}
            for item in todo:
                meta = item.get("meta") or {}
                if meta.get("url"):
                    extras[int(item["row_index"])] = {"track_url": meta["url"]}
            _set_job(
                job_id,
                share_status="done",
                share_current="готово",
                share_csv=links_csv(rows, fieldnames, urls, extras),
                share_csv_name=csv_name,
            )
        except Exception as e:
            _set_job(job_id, share_status="error", share_error=str(e), share_current="")
        finally:
            _busy_release(token)

    threading.Thread(target=run, daemon=True).start()
    return JSONResponse({"ok": True, "total": len(todo), "token": token})


@app.get("/batch/{job_id}/share.csv")
def batch_share_csv(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job or job.get("share_status") != "done" or not job.get("share_csv"):
            raise HTTPException(404, "CSV ещё не готово")
        data = job["share_csv"]
        name = job.get("share_csv_name") or "links.csv"
    return Response(
        data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": _disposition(name)},
    )


@app.post("/batch/{job_id}/pack")
def batch_pack(job_id: str, body: PackBody):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job or job["status"] != "done":
            raise HTTPException(404, "ещё не готово")
        zip_bytes = pack_selected(
            job.get("previews") or [],
            body.skip,
            job.get("fieldnames") or [],
            job.get("failed") or [],
        )
        name = job["zip_name"]
    return Response(
        zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": _disposition(name)},
    )


@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8765")),
    )
