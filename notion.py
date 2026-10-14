"""Create a media-partner announcement page in Notion. Optional: needs token + parent."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from materials import (
    BULLETS,
    CLOSING,
    HEADLINE,
    LEAD,
    intro,
    page_title,
    promo_line,
)

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


def _text(content: str, link: str | None = None) -> dict:
    node = {"type": "text", "text": {"content": content[:2000]}}
    if link:
        node["text"]["link"] = {"url": link}
    return node


def create_mp_page(*, company: str, track_url: str, promo: str, poster_url: str) -> str:
    if not configured():
        raise RuntimeError(MISSING)
    parent = _uuid(os.environ["NOTION_PARENT_PAGE_ID"])
    children: list[dict] = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [_text(intro(company))]},
        },
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [_text("Template:")]},
        },
        {
            "object": "block",
            "type": "heading_3",
            "heading_3": {"rich_text": [_text(HEADLINE)]},
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [_text(LEAD)]},
        },
    ]
    for b in BULLETS:
        children.append(
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [_text(b)]},
            }
        )
    children.append(
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [_text(CLOSING)]},
        }
    )
    if poster_url:
        children.append(
            {
                "object": "block",
                "type": "image",
                "image": {"type": "external", "external": {"url": poster_url}},
            }
        )
    children.append(
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [_text("Register for free", track_url)]
            },
        }
    )
    children.append(
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [_text(promo_line(promo))]},
        }
    )
    payload = {
        "parent": {"page_id": parent},
        "icon": {"type": "emoji", "emoji": "🎯"},
        "properties": {
            "title": {
                "title": [{"type": "text", "text": {"content": page_title(company)}}]
            }
        },
        "children": children,
    }
    if poster_url:
        payload["cover"] = {"type": "external", "external": {"url": poster_url}}
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
