"""Telegram digest for the Today panel. Empty days stay silent unless force=True."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

import db
import partners

YEREVAN = ZoneInfo("Asia/Yerevan")
SITE = os.environ.get("RENDER_EXTERNAL_URL", "https://vc-conf-partner-decks.onrender.com").rstrip("/")
MISSING = "Нет TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID в env Render."


def configured() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() and os.environ.get("TELEGRAM_CHAT_ID", "").strip())


def _now():
    return datetime.now(YEREVAN)


def _line(ev: dict) -> str:
    draft = "" if ev.get("confirmed") else " [черновик]"
    return f"• {ev['company']} · {ev['channel']} · Post {ev['post_number']} ({ev['date']}){draft}"


def build_text(panel: dict, today: str) -> str:
    parts = [f"MP выходы · {today} (Ереван)", ""]
    labels = (
        ("today", "Сегодня"),
        ("remind", "Напомнить (3 дня)"),
        ("overdue", "Просрочено"),
        ("missed", "Missed"),
        ("no_url", "Вышло без ссылки"),
        ("needs_check", "Проверить даты"),
    )
    any_rows = False
    for key, title in labels:
        rows = panel.get(key) or []
        if not rows:
            continue
        any_rows = True
        parts.append(f"{title}:")
        parts.extend(_line(r) for r in rows[:20])
        if len(rows) > 20:
            parts.append(f"… ещё {len(rows) - 20}")
        parts.append("")
    if not any_rows:
        return ""
    parts.append(f"Календарь: {SITE}/")
    text = "\n".join(parts).strip()
    return text[:3900]


def send_telegram(text: str) -> dict:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        raise RuntimeError(MISSING)
    body = json.dumps(
        {"chat_id": chat, "text": text, "disable_web_page_preview": True},
        ensure_ascii=False,
    ).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"Telegram {e.code}: {detail}") from e


def _already_sent(day) -> bool:
    with db.connect() as conn:
        row = conn.execute("SELECT sent_on FROM digest_log WHERE sent_on=%s", (day,)).fetchone()
        return bool(row)


def _mark_sent(day) -> None:
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO digest_log (sent_on) VALUES (%s) ON CONFLICT (sent_on) DO NOTHING",
            (day,),
        )
        conn.commit()


def maybe_send(*, force: bool = False, bundle: dict | None = None) -> dict:
    if not configured():
        return {"sent": False, "reason": MISSING}
    now = _now()
    day = now.date()
    bundle = bundle or partners.calendar_bundle()
    text = build_text(bundle["today_panel"], bundle["today"])
    if not text:
        if force:
            send_telegram(f"MP выходы · {bundle['today']}: пусто.\n{SITE}/")
            return {"sent": True, "empty": True}
        return {"sent": False, "reason": "пусто"}
    if not force:
        if now.hour < 10:
            return {"sent": False, "reason": "ещё не 10:00 по Еревану"}
        if _already_sent(day):
            return {"sent": False, "reason": "уже отправлен сегодня"}
    send_telegram(text)
    _mark_sent(day)
    return {"sent": True, "empty": False}
