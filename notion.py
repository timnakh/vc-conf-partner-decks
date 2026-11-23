"""Create a media-partner announcement page in Notion. Optional: needs token + parent."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from materials import notion_children, page_title

VERSION = "2022-06-28"
MISSING = (
    "Нет Notion. Создай Internal integration на notion.so/my-integrations, "
    "открой родительскую страницу → ••• → Connections → добавь интеграцию, "
    "в Render → Environment: NOTION_TOKEN и NOTION_PARENT_PAGE_ID."
)


def configured() -> bool:
    return bool(
        os.environ.get("NOTION_TOKEN", "").strip()
        and os.environ.get("NOTION_PARENT_PAGE_ID", "").strip()
    )


def is_notion_url(url: str) -> bool:
    host = (url or "").lower()
    return "notion.so" in host or "notion.site" in host


def _page_id(url: str) -> str:
    compact = re.sub(r"[^0-9a-fA-F]", "", (url or "").split("?", 1)[0])
    if len(compact) < 32:
        raise ValueError("в ссылке нет id страницы Notion")
    return _uuid(compact[-32:])


def _api(method: str, path: str, payload: dict | None = None) -> dict:
    if not configured():
        raise RuntimeError(MISSING)
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.notion.com/v1/" + path.lstrip("/"),
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + os.environ["NOTION_TOKEN"].strip(),
            "Notion-Version": VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:800]
        raise RuntimeError(f"Notion {e.code}: {detail}") from e


def _uuid(raw: str) -> str:
    h = re.sub(r"[^0-9a-fA-F]", "", raw)
    if len(h) != 32:
        raise ValueError("NOTION_PARENT_PAGE_ID должен быть id страницы Notion (32 hex)")
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def create_mp_page(
    *,
    company: str,
    track_url: str,
    promo: str,
    poster_url: str,
    poster_square_url: str = "",
    poster_banner_url: str = "",
    first_name: str = "",
    posting_dates: str = "",
    first_post_date: str = "",
    confirmed: bool = True,
    is_speaker: bool = False,
    speaker_name: str = "",
    speaker_role: str = "",
    speaker_topic: str = "",
) -> str:
    if not configured():
        raise RuntimeError(MISSING)
    parent = _uuid(os.environ["NOTION_PARENT_PAGE_ID"])
    payload = {
        "parent": {"page_id": parent},
        "icon": {"type": "emoji", "emoji": "🎯"},
        "properties": {
            "title": {
                "title": [{"type": "text", "text": {"content": page_title(company)}}]
            }
        },
        "children": notion_children(
            company=company,
            track_url=track_url,
            promo=promo,
            poster_url=poster_url,
            poster_square_url=poster_square_url,
            poster_banner_url=poster_banner_url,
            first_name=first_name,
            posting_dates=posting_dates,
            first_post_date=first_post_date,
            confirmed=confirmed,
            is_speaker=is_speaker,
            speaker_name=speaker_name,
            speaker_role=speaker_role,
            speaker_topic=speaker_topic,
        ),
    }
    cover = poster_banner_url or poster_url
    if cover:
        payload["cover"] = {"type": "external", "external": {"url": cover}}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages",
        data=data,
        method="POST",
        headers={
            "Authorization": "Bearer " + os.environ["NOTION_TOKEN"].strip(),
            "Notion-Version": VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:800]
        raise RuntimeError(f"Notion {e.code}: {detail}") from e
    url = body.get("url") or ""
    if not url:
        raise RuntimeError("Notion не вернул url страницы")
    return url


def replace_mp_page(url: str, **kwargs) -> str:
    """Replace the body of an existing kit page. The link stays."""
    page_id = _page_id(url)
    cursor = ""
    ids: list[str] = []
    while True:
        path = f"blocks/{page_id}/children?page_size=100"
        if cursor:
            path += "&start_cursor=" + urllib.parse.quote(cursor)
        body = _api("GET", path)
        for block in body.get("results") or []:
            bid = block.get("id")
            if bid:
                ids.append(bid)
        if not body.get("has_more"):
            break
        cursor = body.get("next_cursor") or ""
        if not cursor:
            break
    for bid in ids:
        _api("DELETE", f"blocks/{bid}")
    kids = notion_children(**kwargs)
    for i in range(0, len(kids), 100):
        chunk = kids[i:i + 100]
        if chunk:
            _api("PATCH", f"blocks/{page_id}/children", {"children": chunk})
    return url
