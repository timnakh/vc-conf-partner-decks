"""Partner + publication rows. Dates parsed from kit text; R2 HTML is the archive."""

from __future__ import annotations

import re
from datetime import date, timedelta
from html.parser import HTMLParser

import db

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
POST_LABELS = {
    1: "Announcement",
    2: "Speakers",
    3: "New year",
    4: "Last call",
}


def season_year(month: int) -> int:
    return 2026 if month >= 9 else 2027


def _weekday(d: date) -> tuple[date, bool]:
    if d.weekday() >= 5:
        return d + timedelta(days=7 - d.weekday()), True
    return d, False


def _parse_one_date(text: str) -> tuple[date | None, bool]:
    raw = (text or "").strip()
    if not raw:
        return None, True
    low = raw.lower().replace("–", "-").replace("—", "-")
    if "next week" in low:
        today = date.today()
        d = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
        d, _ = _weekday(d)
        return d, True
    early = "early" in low
    m = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|"
        r"aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        r"\.?\s*(\d{1,2})(?:\s*-\s*(\d{1,2}))?",
        low,
    )
    if m:
        month = MONTHS.get(m.group(1)) or MONTHS.get(m.group(1)[:3])
        day = int(m.group(2))
        d = date(season_year(month), month, day)
        d, shifted = _weekday(d)
        return d, True if m.group(3) or shifted else False
    m = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|"
        r"aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
        low,
    )
    if m:
        key = m.group(1)
        month = MONTHS.get(key) or MONTHS[key[:3]]
        day = 1 if (early or "dec" in key) else (5 if month == 1 else 1)
        if month == 12:
            day = 1
        if month == 1 and early:
            day = 5
        d = date(season_year(month), month, day)
        d, shifted = _weekday(d)
        return d, True
    return None, True


def parse_posting_dates(
    posting_dates_raw: str,
    first_post_date: str = "",
) -> list[dict]:
    text = (posting_dates_raw or "").strip()
    text = re.split(r"Posting Mon", text, maxsplit=1, flags=re.I)[0]
    text = re.sub(
        r"^[\d–\-]+\s*posts?\s*(\([^)]*\))?\s*:?\s*",
        "",
        text,
        flags=re.I,
    )
    chunks = [c.strip(" .;") for c in re.split(r"[,;]", text) if c.strip(" .;")]
    if not chunks:
        chunks = ["by Nov 20", "early Dec", "early Jan", "Jan 19-22"]
    rows: list[dict] = []
    for i, chunk in enumerate(chunks[:4], start=1):
        d, fuzzy = _parse_one_date(chunk)
        if d is None:
            continue
        low = chunk.lower()
        if "linkedin" in low and "newsletter" not in low:
            channels = ["linkedin"]
        elif "newsletter" in low and "linkedin" not in low:
            channels = ["newsletter"]
        else:
            channels = ["newsletter", "linkedin"]
        for ch in channels:
            rows.append(
                {
                    "date": d,
                    "channel": ch,
                    "post_number": i,
                    "needs_check": True if fuzzy or "by " in low or "early" in low else fuzzy,
                    "notes": chunk,
                }
            )
    first = (first_post_date or "").strip()
    if first:
        d, _ = _parse_one_date(first)
        if d:
            for row in rows:
                if row["post_number"] == 1:
                    row["date"] = d
                    row["needs_check"] = True
                    row["notes"] = (row["notes"] + f"; first_post_date {first}").strip("; ")
    if not rows:
        d, _ = _parse_one_date("Nov 20")
        for ch in ("newsletter", "linkedin"):
            rows.append(
                {
                    "date": d or date(2026, 11, 20),
                    "channel": ch,
                    "post_number": 1,
                    "needs_check": True,
                    "notes": posting_dates_raw or "",
                }
            )
    return rows


class _KitParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._bits: list[str] = []
        self._hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if href.startswith("http"):
                self._hrefs.append(href)

    def handle_data(self, data):
        t = " ".join((data or "").split())
        if t:
            self._bits.append(t)


def parse_kit_html(html: str, *, source_url: str = "") -> dict:
    p = _KitParser()
    p.feed(html or "")
    blob = " ".join(p._bits)
    company = ""
    m = re.search(r"(.+?)\s*×\s*Virtual VC Conf", blob)
    if m:
        company = m.group(1).strip()
    link = ""
    m = re.search(r"Your link:\s*(\S+)", blob, re.I)
    if m:
        link = m.group(1).strip()
    if p._hrefs:
        for href in p._hrefs:
            if "vcconf.com" in href.lower():
                link = href
                break
        if not link:
            link = p._hrefs[0]
    code = ""
    m = re.search(r"Your code:\s*([A-Z0-9_-]+)", blob, re.I)
    if m:
        code = m.group(1).strip().upper()
    dates = ""
    m = re.search(r"Planned posting dates:\s*(.+?)(?:Below is ready-to-use|Visuals:|$)", blob, re.I)
    if m:
        dates = m.group(1).strip()
    first = ""
    m = re.search(r"ideally\s+([^,]+),\s*at the latest", blob, re.I)
    if m:
        first = m.group(1).strip()
    else:
        m = re.search(r"first post \(ideally\s+([^)]+)\)", blob, re.I)
        if m:
            first = m.group(1).strip()
    missing = [
        name
        for name, val in (
            ("company", company),
            ("reg_url", link),
            ("code", code),
            ("posting_dates", dates),
        )
        if not val
    ]
    return {
        "company": company,
        "reg_url": link,
        "code": code,
        "posting_dates": dates,
        "first_post_date": first,
        "source_url": source_url,
        "missing": missing,
    }


def scan_r2_kits() -> list[dict]:
    import store

    items = store.list_keys("vc-conf-2027/poster-mp/")
    htmls = [
        it
        for it in items
        if it["key"].lower().endswith(".html") and "materials" in it["key"].lower()
    ]
    by_company: dict[str, dict] = {}
    for it in sorted(htmls, key=lambda x: x["last_modified"]):
        raw = store.get_bytes(it["key"]).decode("utf-8", errors="replace")
        parsed = parse_kit_html(raw, source_url=it["url"])
        parsed["r2_key"] = it["key"]
        parsed["last_modified"] = it["last_modified"].isoformat()
        key = (parsed["company"] or it["key"]).strip().lower()
        by_company[key] = parsed
    return sorted(by_company.values(), key=lambda r: (r["company"] or r["r2_key"]).lower())


def _partner_row(cur, pid: int) -> dict | None:
    row = cur.execute(
        "SELECT id, company, code, reg_url, notion_page_url, posting_dates_raw, "
        "first_post_date, confirmed, created_at FROM partner WHERE id=%s",
        (pid,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "company": row[1],
        "code": row[2],
        "reg_url": row[3],
        "notion_page_url": row[4],
        "posting_dates_raw": row[5],
        "first_post_date": row[6],
        "confirmed": row[7],
        "created_at": row[8].isoformat() if row[8] else "",
    }


def _pubs(cur, pid: int) -> list[dict]:
    rows = cur.execute(
        "SELECT id, date, channel, post_number, status, needs_check, url, notes, "
        "reminded_at, published_at, updated_at FROM publication "
        "WHERE partner_id=%s ORDER BY date, post_number, channel",
        (pid,),
    ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r[0],
                "date": r[1].isoformat(),
                "channel": r[2],
                "post_number": r[3],
                "post_label": POST_LABELS.get(r[3], str(r[3])),
                "status": r[4],
                "needs_check": r[5],
                "url": r[6],
                "notes": r[7],
                "reminded_at": r[8].isoformat() if r[8] else "",
                "published_at": r[9].isoformat() if r[9] else "",
                "updated_at": r[10].isoformat() if r[10] else "",
            }
        )
    return out


def replace_publications(cur, partner_id: int, drafts: list[dict]) -> None:
    cur.execute("DELETE FROM publication WHERE partner_id=%s AND status='planned'", (partner_id,))
    for d in drafts:
        cur.execute(
            "INSERT INTO publication (partner_id, date, channel, post_number, status, needs_check, notes) "
            "VALUES (%s, %s, %s, %s, 'planned', %s, %s)",
            (
                partner_id,
                d["date"],
                d["channel"],
                d["post_number"],
                bool(d.get("needs_check")),
                d.get("notes") or "",
            ),
        )


def upsert_partner(
    *,
    company: str,
    code: str = "",
    reg_url: str = "",
    notion_page_url: str = "",
    posting_dates_raw: str = "",
    first_post_date: str = "",
    confirmed: bool = False,
    rebuild_pubs: bool = True,
) -> dict:
    company = (company or "").strip()
    if not company:
        raise ValueError("нужно название компании")
    code = (code or "").strip().upper()
    reg_url = (reg_url or "").strip()
    notion_page_url = (notion_page_url or "").strip()
    posting_dates_raw = (posting_dates_raw or "").strip()
    first_post_date = (first_post_date or "").strip()
    drafts = parse_posting_dates(posting_dates_raw, first_post_date)
    with db.connect() as conn:
        cur = conn.cursor()
        found = cur.execute(
            "SELECT id, confirmed FROM partner WHERE lower(company)=lower(%s)",
            (company,),
        ).fetchone()
        if found:
            pid, already = found
            cur.execute(
                "UPDATE partner SET code=CASE WHEN %s='' THEN code ELSE %s END, "
                "reg_url=CASE WHEN %s='' THEN reg_url ELSE %s END, "
                "notion_page_url=CASE WHEN %s='' THEN notion_page_url ELSE %s END, "
                "posting_dates_raw=CASE WHEN %s='' THEN posting_dates_raw ELSE %s END, "
                "first_post_date=CASE WHEN %s='' THEN first_post_date ELSE %s END, "
                "confirmed=confirmed OR %s WHERE id=%s",
                (
                    code, code, reg_url, reg_url, notion_page_url, notion_page_url,
                    posting_dates_raw, posting_dates_raw, first_post_date, first_post_date,
                    confirmed, pid,
                ),
            )
            if rebuild_pubs and not already:
                replace_publications(cur, pid, drafts)
            elif rebuild_pubs and confirmed and already:
                n = cur.execute(
                    "SELECT count(*) FROM publication WHERE partner_id=%s", (pid,)
                ).fetchone()[0]
                if n == 0:
                    replace_publications(cur, pid, drafts)
        else:
            row = cur.execute(
                "INSERT INTO partner (company, code, reg_url, notion_page_url, posting_dates_raw, "
                "first_post_date, confirmed) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (company, code, reg_url, notion_page_url, posting_dates_raw, first_post_date, confirmed),
            ).fetchone()
            pid = row[0]
            if rebuild_pubs:
                replace_publications(cur, pid, drafts)
        conn.commit()
        partner = _partner_row(cur, pid)
        partner["publications"] = _pubs(cur, pid)
        return partner


def ready_for_db(company: str, code: str) -> bool:
    return bool((company or "").strip() and (code or "").strip())


def import_from_r2(skip_keys: list[str] | None = None) -> dict:
    skip = {k.strip() for k in (skip_keys or []) if k and k.strip()}
    scanned = scan_r2_kits()
    imported = []
    skipped = []
    for row in scanned:
        key = row.get("r2_key") or ""
        if key in skip or not ready_for_db(row.get("company") or "", row.get("code") or ""):
            skipped.append(row)
            continue
        partner = upsert_partner(
            company=row["company"],
            code=row["code"],
            reg_url=row["reg_url"],
            posting_dates_raw=row["posting_dates"],
            first_post_date=row["first_post_date"],
            confirmed=False,
            rebuild_pubs=True,
        )
        imported.append({**row, "partner_id": partner["id"], "pub_count": len(partner["publications"])})
    return {"scanned": scanned, "imported": imported, "skipped": skipped}


def unconfirmed() -> list[dict]:
    with db.connect() as conn:
        cur = conn.cursor()
        ids = [r[0] for r in cur.execute(
            "SELECT id FROM partner WHERE NOT confirmed ORDER BY lower(company)"
        ).fetchall()]
        return [{**_partner_row(cur, i), "publications": _pubs(cur, i)} for i in ids]


def update_publication(pid: int, **fields) -> dict:
    allowed = {"date", "channel", "post_number", "status", "needs_check", "url", "notes"}
    sets = []
    vals = []
    for k, v in fields.items():
        if k not in allowed:
            continue
        sets.append(f"{k}=%s")
        vals.append(v)
    if not sets:
        raise ValueError("нечего менять")
    sets.append("updated_at=NOW()")
    vals.append(pid)
    with db.connect() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE publication SET {', '.join(sets)} WHERE id=%s RETURNING partner_id",
            vals,
        )
        row = cur.fetchone()
        if not row:
            raise ValueError("нет такого выхода")
        conn.commit()
        return {"ok": True, "partner_id": row[0]}


def delete_publication(pid: int) -> None:
    with db.connect() as conn:
        conn.execute("DELETE FROM publication WHERE id=%s", (pid,))
        conn.commit()


def delete_partner(pid: int) -> None:
    with db.connect() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM partner WHERE id=%s RETURNING id", (pid,))
        if not cur.fetchone():
            raise ValueError("нет такого партнёра")
        conn.commit()


def confirm_partner(pid: int) -> dict:
    with db.connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE partner SET confirmed=TRUE WHERE id=%s RETURNING id",
            (pid,),
        )
        if not cur.fetchone():
            raise ValueError("нет такого партнёра")
        cur.execute(
            "UPDATE publication SET needs_check=FALSE, updated_at=NOW() WHERE partner_id=%s",
            (pid,),
        )
        conn.commit()
        return {**_partner_row(cur, pid), "publications": _pubs(cur, pid)}
