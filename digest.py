"""Telegram digest for the Today panel. Empty days stay silent unless force=True."""

from __future__ import annotations

import json
import os
import re
import uuid
import urllib.error
import urllib.request
from datetime import date, datetime
from zoneinfo import ZoneInfo

import db
import partners

YEREVAN = ZoneInfo("Asia/Yerevan")
SITE = os.environ.get("RENDER_EXTERNAL_URL", "https://vc-conf-partner-decks.onrender.com").rstrip("/")
MISSING = "Нет TELEGRAM_BOT_TOKEN или TELEGRAM_CHAT_ID в env Render."
RU_MONTHS = {
    "янв": 1, "января": 1, "январь": 1,
    "фев": 2, "февраля": 2, "февраль": 2,
    "мар": 3, "марта": 3, "март": 3,
    "апр": 4, "апреля": 4, "апрель": 4,
    "май": 5, "мая": 5,
    "июн": 6, "июня": 6, "июнь": 6,
    "июл": 7, "июля": 7, "июль": 7,
    "авг": 8, "августа": 8, "август": 8,
    "сен": 9, "сентября": 9, "сентябрь": 9,
    "окт": 10, "октября": 10, "октябрь": 10,
    "ноя": 11, "ноября": 11, "ноябрь": 11,
    "дек": 12, "декабря": 12, "декабрь": 12,
}


def configured() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() and os.environ.get("TELEGRAM_CHAT_ID", "").strip())


def _now():
    return datetime.now(YEREVAN)


def _chat_ok(chat_id) -> bool:
    want = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    return bool(want) and str(chat_id) == want


def _token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()


def _api(method: str, payload: dict) -> dict:
    token = _token()
    if not token:
        raise RuntimeError(MISSING)
    body = json.dumps(payload, ensure_ascii=False).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
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


def send_telegram(text: str, reply_markup: dict | None = None) -> dict:
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not _token() or not chat:
        raise RuntimeError(MISSING)
    payload = {"chat_id": chat, "text": text, "disable_web_page_preview": True}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _api("sendMessage", payload)


def ensure_webhook() -> None:
    if not _token():
        return
    url = f"{SITE}/telegram/webhook"
    try:
        _api(
            "setWebhook",
            {
                "url": url,
                "allowed_updates": ["message", "callback_query"],
                "drop_pending_updates": False,
            },
        )
    except Exception:
        pass


def _put_action(ids: list[int]) -> str:
    token = uuid.uuid4().hex[:10]
    csv = ",".join(str(i) for i in ids)
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO telegram_action (token, pub_ids) VALUES (%s, %s)",
            (token, csv),
        )
        conn.commit()
    return token


def _ids_for(token: str) -> list[int]:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT pub_ids FROM telegram_action WHERE token=%s", (token,)
        ).fetchone()
    if not row:
        return []
    return [int(x) for x in (row[0] or "").split(",") if x.strip().isdigit()]


def _set_wait(chat_id, action: str, token: str) -> None:
    with db.connect() as conn:
        conn.execute(
            "INSERT INTO telegram_wait (chat_id, action, token) VALUES (%s, %s, %s) "
            "ON CONFLICT (chat_id) DO UPDATE SET action=EXCLUDED.action, token=EXCLUDED.token, created_at=NOW()",
            (str(chat_id), action, token),
        )
        conn.commit()


def _pop_wait(chat_id) -> dict | None:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT action, token FROM telegram_wait WHERE chat_id=%s", (str(chat_id),)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM telegram_wait WHERE chat_id=%s", (str(chat_id),))
            conn.commit()
            return {"action": row[0], "token": row[1]}
    return None


def parse_human_date(text: str) -> date | None:
    raw = (text or "").strip()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"(\d{1,2})[.\-/](\d{1,2})(?:[.\-/](\d{2,4}))?", raw)
    if m and not re.search(r"[а-яa-z]", raw.lower()):
        day, month = int(m.group(1)), int(m.group(2))
        year = int(m.group(3)) if m.group(3) else partners.season_year(month)
        if year < 100:
            year += 2000
        return date(year, month, day)
    m = re.search(r"(\d{1,2})\s+([а-яa-z.]+)", raw.lower())
    if m:
        day = int(m.group(1))
        mon = re.sub(r"[.]", "", m.group(2))
        month = RU_MONTHS.get(mon) or partners.MONTHS.get(mon[:3] if len(mon) >= 3 else mon)
        if month:
            return date(partners.season_year(month), month, day)
    d, _ = partners._parse_one_date(raw)
    return d


def _first_url(text: str) -> str:
    m = re.search(r"https?://\S+", text or "")
    return (m.group(0).rstrip(").,]>") if m else "").strip()


def build_blocks(panel: dict) -> list[tuple[str, list[dict]]]:
    labels = (
        ("today", "Сегодня"),
        ("remind", "Напомнить (через 3 дня)"),
        ("overdue", "Просрочено"),
        ("no_url", "Вышли без ссылки"),
        ("week", "На этой неделе"),
    )
    out = []
    for key, title in labels:
        groups = partners.group_digest_rows(panel.get(key) or [])
        if groups:
            out.append((title, groups))
    return out


def build_text(panel: dict, today: str) -> str:
    parts = [f"MP выходы · {today} (Ереван)", ""]
    any_rows = False
    for title, groups in build_blocks(panel):
        any_rows = True
        parts.append(f"{title}:")
        parts.extend(f"• {g['line']}" for g in groups[:20])
        if len(groups) > 20:
            parts.append(f"… ещё {len(groups) - 20}")
        parts.append("")
    n = int(panel.get("drafts_n") or 0)
    if n:
        parts.append(f"Черновиков на проверку: {n}")
        parts.append("")
        any_rows = True
    if not any_rows:
        return ""
    parts.append(f"Календарь: {SITE}/calendar")
    return "\n".join(parts).strip()[:3900]


def _keyboard(groups: list[dict]) -> dict:
    rows = []
    for g in groups[:20]:
        token = _put_action(g["ids"])
        rows.append(
            [
                {"text": "Напомнил", "callback_data": f"r:{token}"},
                {"text": "Вышел", "callback_data": f"p:{token}"},
                {"text": "Перенести", "callback_data": f"m:{token}"},
            ]
        )
    return {"inline_keyboard": rows}


def send_digest(panel: dict, today: str, *, empty_force: bool = False) -> dict:
    ensure_webhook()
    blocks = build_blocks(panel)
    n = int(panel.get("drafts_n") or 0)
    if not blocks and not n:
        if empty_force:
            send_telegram(f"MP выходы · {today}: пусто.\n{SITE}/calendar")
            return {"sent": True, "empty": True}
        return {"sent": False, "reason": "пусто"}
    head = [f"MP выходы · {today} (Ереван)"]
    send_telegram("\n".join(head))
    for title, groups in blocks:
        text = title + ":\n" + "\n".join(f"• {g['line']}" for g in groups[:20])
        send_telegram(text[:3900], _keyboard(groups))
    tail = []
    if n:
        tail.append(f"Черновиков на проверку: {n}")
    tail.append(f"Календарь: {SITE}/calendar")
    send_telegram("\n".join(tail))
    return {"sent": True, "empty": False}


def handle_update(body: dict) -> dict:
    cb = body.get("callback_query") or {}
    msg = body.get("message") or {}
    if cb:
        from_id = (cb.get("from") or {}).get("id")
        chat_id = ((cb.get("message") or {}).get("chat") or {}).get("id") or from_id
        if not _chat_ok(chat_id) and not _chat_ok(from_id):
            return {"ok": True, "ignored": True}
        data = (cb.get("data") or "").strip()
        cq_id = cb.get("id")
        op, _, token = data.partition(":")
        ids = _ids_for(token)
        try:
            if op == "r":
                for pid in ids:
                    partners.update_publication(pid, status="reminded")
                _api("answerCallbackQuery", {"callback_query_id": cq_id, "text": "Напомнил"})
                send_telegram("Ок, статус reminded.")
            elif op == "p":
                _set_wait(chat_id, "url", token)
                _api("answerCallbackQuery", {"callback_query_id": cq_id, "text": "Жду ссылку"})
                send_telegram("Пришли ссылку на выход (один URL).")
            elif op == "m":
                _set_wait(chat_id, "date", token)
                _api("answerCallbackQuery", {"callback_query_id": cq_id, "text": "Жду дату"})
                send_telegram("Пришли новую дату, например 12 ноя или 2026-11-12.")
            else:
                _api("answerCallbackQuery", {"callback_query_id": cq_id, "text": "не понял"})
        except Exception as e:
            try:
                _api("answerCallbackQuery", {"callback_query_id": cq_id, "text": str(e)[:180]})
            except Exception:
                pass
        return {"ok": True}
    if msg:
        chat_id = (msg.get("chat") or {}).get("id")
        if not _chat_ok(chat_id):
            return {"ok": True, "ignored": True}
        wait = _pop_wait(chat_id)
        if not wait:
            return {"ok": True, "noop": True}
        text = (msg.get("text") or "").strip()
        ids = _ids_for(wait["token"])
        if not ids:
            send_telegram("Не нашёл выходы — открой календарь.")
            return {"ok": True}
        try:
            if wait["action"] == "url":
                url = _first_url(text)
                if not url:
                    _set_wait(chat_id, "url", wait["token"])
                    send_telegram("Нужен URL, например https://…")
                    return {"ok": True}
                for pid in ids:
                    partners.update_publication(pid, url=url, status="published")
                send_telegram("Сохранил ссылку, статус published.")
            elif wait["action"] == "date":
                d = parse_human_date(text)
                if not d:
                    _set_wait(chat_id, "date", wait["token"])
                    send_telegram("Не разобрал дату. Пример: 12 ноя или 2026-11-12.")
                    return {"ok": True}
                for pid in ids:
                    partners.update_publication(pid, date=d)
                send_telegram(f"Перенёс на {partners.ru_day(d)}.")
        except Exception as e:
            send_telegram(f"Не вышло: {e}")
        return {"ok": True}
    return {"ok": True}


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
    panel = bundle["today_panel"]
    text = build_text(panel, bundle["today"])
    if not text and not force:
        return {"sent": False, "reason": "пусто"}
    if not force:
        if now.hour < 10:
            return {"sent": False, "reason": "ещё не 10:00 по Еревану"}
        if _already_sent(day):
            return {"sent": False, "reason": "уже отправлен сегодня"}
    result = send_digest(panel, bundle["today"], empty_force=force and not text)
    if result.get("sent"):
        _mark_sent(day)
    return result


def cron_send() -> dict:
    """Clock is cron-job.org. Skip the local 10:00 check; still one send per day."""
    ensure_webhook()
    if not configured():
        return {"sent": False, "reason": MISSING}
    day = _now().date()
    if _already_sent(day):
        return {"sent": False, "reason": "уже отправлен сегодня"}
    bundle = partners.calendar_bundle()
    panel = bundle["today_panel"]
    text = build_text(panel, bundle["today"])
    if not text:
        return {"sent": False, "reason": "пусто"}
    result = send_digest(panel, bundle["today"], empty_force=False)
    if result.get("sent"):
        _mark_sent(day)
    return result
