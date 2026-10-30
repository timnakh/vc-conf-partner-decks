"""Create a media-partner announcement page in Notion. Optional: needs token + parent."""

from __future__ import annotations

import json
import os
import re
import urllib.error
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
