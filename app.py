from __future__ import annotations

import base64
import io
import os
import secrets
import tempfile
import threading
import uuid
import zipfile
from datetime import date
from typing import Optional
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.background import BackgroundTask
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
    item_payload,
    links_csv,
    load_catalog,
    pack_selected,
    render_filename,
    unpack_logo_zip,
)
from poster import fill_poster, fill_posters_from_csv, poster_filename
import materials
import notion as notionmod
import db
import partners
import digest

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"

app = FastAPI(title="Презентации для партнёров")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def admin_basic_auth(request: Request, call_next):
    if request.url.path in ("/health", "/telegram/webhook", "/cron/digest"):
        return await call_next(request)
    password = os.environ.get("ADMIN_PASSWORD", "").strip()
    if not password:
        return await call_next(request)
    header = request.headers.get("authorization") or ""
    user, pw = "", ""
    if header.lower().startswith("basic "):
        try:
            raw = base64.b64decode(header.split(" ", 1)[1].strip()).decode()
            user, _, pw = raw.partition(":")
        except Exception:
            pw = ""
    if secrets.compare_digest(pw, password):
        return await call_next(request)
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="VC Conf"'},
        content="auth required",
    )

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


class PartnerIn(BaseModel):
    company: str
    code: str = ""
    reg_url: str = ""
    notion_page_url: str = ""
    posting_dates_raw: str = ""
    first_post_date: str = ""
    notes: str = ""
    update: bool = False
    confirmed: bool = False


class PartnerPatch(BaseModel):
    company: Optional[str] = None
    code: Optional[str] = None
    reg_url: Optional[str] = None
    notion_page_url: Optional[str] = None
    posting_dates_raw: Optional[str] = None
    first_post_date: Optional[str] = None
    notes: Optional[str] = None
    confirmed: Optional[bool] = None


class PubCreate(BaseModel):
    date: str
    channel: str = "newsletter"
    post_number: int = 1
    notes: str = ""
    url: str = ""


class RebuildIn(BaseModel):
    posting_dates_raw: str = ""
    first_post_date: str = ""


class ImportR2In(BaseModel):
    skip: list[str] = []


class PubPatch(BaseModel):
    date: Optional[str] = None
    channel: Optional[str] = None
    post_number: Optional[int] = None
    needs_check: Optional[bool] = None
    url: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


def _html(name: str) -> HTMLResponse:
    return HTMLResponse(
        (STATIC / name).read_text(),
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return _html("calendar.html")


@app.get("/calendar", response_class=HTMLResponse)
def calendar_page() -> HTMLResponse:
    return _html("calendar.html")


@app.get("/kits", response_class=HTMLResponse)
def kits_page() -> HTMLResponse:
    return _html("index.html")


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
    files = item.get("files") or []
    if files:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for blob in files:
                zf.writestr(
                    blob["filename"],
                    item_payload(blob),
                    compress_type=zipfile.ZIP_STORED,
                )
        name = item["filename"]
        if not name.lower().endswith(".zip"):
            name = Path(name).stem + ".zip"
        return Response(
            buf.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": _disposition(name)},
        )
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


@app.get("/notion")
def notion_status():
    return {"ok": notionmod.configured(), "storage": store.configured()}


@app.post("/poster/{fill_id}/materials")
def poster_materials(fill_id: str, update_partner: bool = False):
    item = FILLS.get(fill_id)
    if not item:
        raise HTTPException(404, "превью уже не доступно — собери ещё раз")
    meta = item.get("meta") or {}
    company = meta.get("company") or "partner"
    track = meta.get("url") or ""
    promo = meta.get("promo") or ""
    first_name = meta.get("first_name") or ""
    posting_dates = meta.get("posting_dates") or ""
    first_post_date = meta.get("first_post_date") or ""
    if not store.configured():
        md = materials.markdown(
            company=company,
            track_url=track,
            promo=promo,
            poster_url="",
            poster_square_url="",
            poster_banner_url="",
            first_name=first_name,
            posting_dates=posting_dates,
            first_post_date=first_post_date,
        )
        return JSONResponse(
            {
                "title": materials.page_title(company),
                "markdown": md,
                "poster_url": "",
                "html_url": "",
                "notion_url": "",
                "hint": store.MISSING,
            }
        )
    token = _busy_acquire("share", 1)
    if not token:
        raise HTTPException(409, _busy_snapshot()["message"])
    try:
        folder = item.get("template_id") or "poster-mp"
        poster_url = ""
        poster_square_url = ""
        poster_banner_url = ""
        files = item.get("files") or []
        if files:
            for blob in files:
                url = store.put_file(
                    store.object_key(blob["filename"], folder),
                    item_payload(blob),
                    blob["filename"],
                    blob.get("content_type") or "image/png",
                )
                kind = blob.get("kind")
                if kind == "square":
                    poster_square_url = url
                elif kind == "banner":
                    poster_banner_url = url
                else:
                    poster_url = url
        else:
            poster_url = store.put_file(
                store.object_key(item["filename"], folder),
                item["pdf"],
                item["filename"],
                item.get("content_type") or "image/png",
            )
        html = materials.html_page(
            company=company,
            track_url=track,
            promo=promo,
            poster_url=poster_url,
            poster_square_url=poster_square_url,
            poster_banner_url=poster_banner_url,
            first_name=first_name,
            posting_dates=posting_dates,
            first_post_date=first_post_date,
        )
        html_name = f"{company} — materials.html"
        html_url = store.put_file(
            store.object_key(html_name, "poster-mp"),
            html.encode("utf-8"),
            html_name,
            "text/html",
        )
        md = materials.markdown(
            company=company,
            track_url=track,
            promo=promo,
            poster_url=poster_url,
            poster_square_url=poster_square_url,
            poster_banner_url=poster_banner_url,
            first_name=first_name,
            posting_dates=posting_dates,
            first_post_date=first_post_date,
        )
        notion_url = ""
        notion_error = ""
        if notionmod.configured():
            try:
                notion_url = notionmod.create_mp_page(
                    company=company,
                    track_url=track,
                    promo=promo,
                    poster_url=poster_url,
                    poster_square_url=poster_square_url,
                    poster_banner_url=poster_banner_url,
                    first_name=first_name,
                    posting_dates=posting_dates,
                    first_post_date=first_post_date,
                )
            except Exception as e:
                notion_error = str(e)
        partner_conflict = False
        partner_id = 0
        if db.configured():
            try:
                saved = partners.create_or_conflict(
                    company=company,
                    code=promo,
                    reg_url=track,
                    notion_page_url=notion_url,
                    posting_dates_raw=posting_dates,
                    first_post_date=first_post_date,
                    confirmed=True,
                    update_existing=update_partner,
                    rebuild_pubs=None,
                )
                partner_conflict = bool(saved.get("conflict"))
                partner_id = (saved.get("partner") or saved.get("existing") or {}).get("id") or 0
            except Exception as e:
                notion_error = (notion_error + " | " if notion_error else "") + f"БД: {e}"
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    finally:
        _busy_release(token)
    return JSONResponse(
        {
            "title": materials.page_title(company),
            "markdown": md,
            "poster_url": poster_url,
            "poster_square_url": poster_square_url,
            "poster_banner_url": poster_banner_url,
            "html_url": html_url,
            "notion_url": notion_url,
            "notion_error": notion_error,
            "hint": "" if notion_url else notionmod.MISSING,
            "partner_conflict": partner_conflict,
            "partner_id": partner_id,
        }
    )


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
    first_name: str = Form(""),
    posting_dates: str = Form(""),
    first_post_date: str = Form(""),
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
        filled = fill_poster(
            person,
            logo=image,
            url=url,
            promo=promo,
            first_name=first_name,
            posting_dates=posting_dates,
            first_post_date=first_post_date,
        )
        _busy_progress(1, 1)
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    finally:
        _busy_release(token)
    filename = poster_filename(filename_pattern, person)
    square_name = f"VC Conf poster — {person} (LinkedIn).png"
    zip_name = filename.rsplit(".", 1)[0] + ".zip"
    fill_id = uuid.uuid4().hex
    FILLS[fill_id] = {
        "pdf": filled["portrait"],
        "filename": zip_name,
        "preview": filled["preview"],
        "preview_square": filled["preview_square"],
        "preview_banner": filled["preview_banner"],
        "template_id": "poster-mp",
        "content_type": "application/zip",
        "meta": filled["meta"],
        "files": [
            {
                "filename": filename,
                "pdf": filled["portrait"],
                "content_type": "image/png",
                "kind": "portrait",
            },
            {
                "filename": square_name,
                "pdf": filled["square"],
                "content_type": "image/png",
                "kind": "square",
            },
            {
                "filename": f"VC Conf banner — {person}.png",
                "pdf": filled["banner"],
                "content_type": "image/png",
                "kind": "banner",
            },
        ],
    }
    return JSONResponse(
        {
            "id": fill_id,
            "name": person,
            "filename": zip_name,
            "track_url": filled["meta"]["url"],
            "promo": filled["meta"]["promo"],
            "preview": "data:image/jpeg;base64," + base64.b64encode(filled["preview"]).decode(),
            "preview_square": "data:image/jpeg;base64,"
            + base64.b64encode(filled["preview_square"]).decode(),
            "preview_banner": "data:image/jpeg;base64,"
            + base64.b64encode(filled["preview_banner"]).decode(),
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
        files = item.get("files") or []
        if files:
            urls = {}
            for blob in files:
                urls[blob.get("kind") or "file"] = store.put_file(
                    store.object_key(blob["filename"], item.get("template_id") or "decks"),
                    item_payload(blob),
                    blob["filename"],
                    blob.get("content_type") or "image/png",
                )
            url = urls.get("portrait") or next(iter(urls.values()))
            return {
                "url": url,
                "square_url": urls.get("square") or "",
                "banner_url": urls.get("banner") or "",
                "filename": item["filename"],
            }
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
                row_i = int(item["row_index"])
                blobs = item.get("files") or [item]
                portrait_url = ""
                square_url = ""
                banner_url = ""
                for blob in blobs:
                    put = store.put_file(
                        store.object_key(blob["filename"], folder),
                        item_payload(blob),
                        blob["filename"],
                        blob.get("content_type") or content_type,
                    )
                    kind = blob.get("kind")
                    if kind == "square":
                        square_url = put
                    elif kind == "banner":
                        banner_url = put
                    else:
                        portrait_url = put
                urls[row_i] = portrait_url or square_url or banner_url
                item["_square_url"] = square_url
                item["_banner_url"] = banner_url
                _set_job(job_id, share_done=n)
                _busy_progress(n, len(todo))
            csv_name = zip_name.replace(".zip", "-links.csv")
            if not csv_name.endswith(".csv"):
                csv_name = "links.csv"
            extras: dict[int, dict] = {}
            poster_job = (folder or "").startswith("poster")
            for item in todo:
                meta = item.get("meta") or {}
                extra: dict = {}
                if meta.get("url"):
                    extra["track_url"] = meta["url"]
                if poster_job:
                    company = meta.get("company") or item.get("name") or "partner"
                    poster_url = urls.get(int(item["row_index"])) or ""
                    poster_square_url = item.get("_square_url") or ""
                    poster_banner_url = item.get("_banner_url") or ""
                    html = materials.html_page(
                        company=company,
                        track_url=meta.get("url") or "",
                        promo=meta.get("promo") or "",
                        poster_url=poster_url,
                        poster_square_url=poster_square_url,
                        poster_banner_url=poster_banner_url,
                        first_name=meta.get("first_name") or "",
                        posting_dates=meta.get("posting_dates") or "",
                        first_post_date=meta.get("first_post_date") or "",
                    )
                    html_name = f"{company} — materials.html"
                    extra["materials_url"] = store.put_file(
                        store.object_key(html_name, folder),
                        html.encode("utf-8"),
                        html_name,
                        "text/html",
                    )
                    extra["poster_square_url"] = poster_square_url
                    extra["poster_banner_url"] = poster_banner_url
                    extra["markdown"] = materials.markdown(
                        company=company,
                        track_url=meta.get("url") or "",
                        promo=meta.get("promo") or "",
                        poster_url=poster_url,
                        poster_square_url=poster_square_url,
                        poster_banner_url=poster_banner_url,
                        first_name=meta.get("first_name") or "",
                        posting_dates=meta.get("posting_dates") or "",
                        first_post_date=meta.get("first_post_date") or "",
                    )
                if extra:
                    extras[int(item["row_index"])] = extra
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
        previews = list(job.get("previews") or [])
        fieldnames = list(job.get("fieldnames") or [])
        failed = list(job.get("failed") or [])
        name = job["zip_name"]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()
    dest = Path(tmp.name)
    try:
        pack_selected(previews, body.skip, fieldnames, failed, dest=dest)
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    return FileResponse(
        dest,
        media_type="application/zip",
        headers={"Content-Disposition": _disposition(name)},
        background=BackgroundTask(dest.unlink, missing_ok=True),
    )


@app.get("/api/calendar")
def api_calendar():
    try:
        data = partners.calendar_bundle()
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    data["telegram"] = digest.configured()
    def _tick():
        try:
            digest.maybe_send(bundle=data)
        except Exception:
            pass
    threading.Thread(target=_tick, daemon=True).start()
    return data


@app.post("/api/digest")
def api_digest():
    try:
        return digest.maybe_send(force=True)
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "bad json") from None
    try:
        return digest.handle_update(body if isinstance(body, dict) else {})
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/publications/{pub_id}/reminder")
def api_reminder(pub_id: int):
    try:
        return partners.get_publication(pub_id)
    except Exception as e:
        raise HTTPException(404, str(e)) from e


@app.get("/import", response_class=HTMLResponse)
def import_page() -> HTMLResponse:
    return _html("import.html")


@app.get("/partners", response_class=HTMLResponse)
def partners_page() -> HTMLResponse:
    return _html("partners.html")


@app.get("/partners/{pid}", response_class=HTMLResponse)
def partner_page(pid: int) -> HTMLResponse:
    return _html("partner.html")


@app.get("/api/partners")
def api_partners(q: str = ""):
    try:
        return {"partners": partners.list_partners(q)}
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/partners")
def api_add_partner(body: PartnerIn):
    if not partners.ready_for_db(body.company, body.code):
        raise HTTPException(400, "нужны company и code")
    try:
        saved = partners.create_or_conflict(
            company=body.company,
            code=body.code,
            reg_url=body.reg_url,
            notion_page_url=body.notion_page_url,
            posting_dates_raw=body.posting_dates_raw,
            first_post_date=body.first_post_date,
            notes=body.notes,
            confirmed=body.confirmed,
            update_existing=body.update,
        )
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    if saved.get("conflict"):
        return JSONResponse(saved, status_code=409)
    return saved


@app.get("/api/partners/{pid}")
def api_get_partner(pid: int):
    try:
        return partners.get_partner(pid)
    except Exception as e:
        raise HTTPException(404, str(e)) from e


@app.patch("/api/partners/{pid}")
def api_patch_partner(pid: int, body: PartnerPatch):
    try:
        return partners.save_partner(pid, **body.model_dump(exclude_none=True))
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/partners/{pid}/publications")
def api_add_pub(pid: int, body: PubCreate):
    try:
        return partners.add_publication(
            pid,
            date_value=date.fromisoformat(body.date),
            channel=body.channel,
            post_number=body.post_number,
            notes=body.notes,
            url=body.url,
        )
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/partners/{pid}/rebuild-preview")
def api_rebuild_preview(pid: int, body: RebuildIn):
    try:
        return partners.preview_rebuild(pid, body.posting_dates_raw, body.first_post_date)
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/partners/{pid}/rebuild")
def api_rebuild(pid: int, body: RebuildIn):
    try:
        return partners.apply_rebuild(pid, body.posting_dates_raw, body.first_post_date)
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.patch("/api/publications/{pub_id}")
def api_patch_pub(pub_id: int, body: PubPatch):
    return import_patch_pub(pub_id, body)


@app.delete("/api/publications/{pub_id}")
def api_del_pub(pub_id: int):
    return import_del_pub(pub_id)


@app.get("/api/db")
def db_status():
    if not db.configured():
        return {"ok": False, "hint": db.MISSING}
    try:
        with db.connect() as conn:
            n = conn.execute("SELECT count(*) FROM partner").fetchone()[0]
        return {"ok": True, "partners": n}
    except Exception as e:
        msg = str(e)
        hint = ""
        if "channel_binding" in msg.lower():
            hint = "Убери channel_binding из DATABASE_URL в Neon/Render."
        return JSONResponse({"ok": False, "error": msg, "hint": hint}, status_code=503)


@app.get("/api/import/scan")
def import_scan():
    try:
        return {"scanned": partners.scan_r2_kits()}
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/import/from-r2")
def import_from_r2(body: ImportR2In = ImportR2In()):
    try:
        return partners.import_from_r2(skip_keys=body.skip)
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/import/partners")
def import_partners():
    try:
        return {"partners": partners.unconfirmed()}
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/import/partners")
def import_add_partner(body: PartnerIn):
    return api_add_partner(body)


@app.patch("/api/import/publications/{pub_id}")
def import_patch_pub(pub_id: int, body: PubPatch):
    fields = body.model_dump(exclude_none=True)
    if "date" in fields:
        fields["date"] = date.fromisoformat(fields["date"])
    try:
        return partners.update_publication(pub_id, **fields)
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.delete("/api/import/publications/{pub_id}")
def import_del_pub(pub_id: int):
    try:
        partners.delete_publication(pub_id)
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True}


@app.delete("/api/import/partners/{pid}")
def import_del_partner(pid: int):
    try:
        partners.delete_partner(pid)
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True}


@app.post("/api/import/partners/{pid}/confirm")
def import_confirm(pid: int):
    try:
        return partners.confirm_partner(pid)
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.get("/cron/digest")
def cron_digest(key: str = ""):
    secret = os.environ.get("CRON_SECRET", "").strip()
    if not secret:
        raise HTTPException(503, "нет CRON_SECRET")
    if not key or len(key) != len(secret) or not secrets.compare_digest(key, secret):
        raise HTTPException(401, "bad key")
    try:
        return digest.cron_send()
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.get("/health")
def health():
    return {"ok": True}


@app.on_event("startup")
def _telegram_webhook_on_boot():
    threading.Thread(target=digest.ensure_webhook, daemon=True).start()


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8765")),
    )
