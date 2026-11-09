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


_MONTH = (
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|"
    r"aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
)
_DATE_RE = re.compile(
    rf"(?:(?P<qual>early|mid|late|by|starting)\s+)?(?P<mon>{_MONTH})\.?"
    rf"(?:\s+(?P<day>\d{{1,2}})(?:\s*[–\-]\s*(?P<day2>\d{{1,2}}))?)?",
    re.I,
)


def _parse_one_date(text: str) -> tuple[date | None, bool]:
    raw = (text or "").strip()
    if not raw:
        return None, True
    low = raw.lower().replace("–", "-").replace("—", "-")
    m = re.search(
        rf"\b({_MONTH})\.?\s*(\d{{1,2}})(?:\s*-\s*(\d{{1,2}}))?",
        low,
    )
    if m:
        month = MONTHS.get(m.group(1)) or MONTHS.get(m.group(1)[:3])
        day = int(m.group(2))
        d = date(season_year(month), month, day)
        if month == 1 and day >= 19:
            return d, True
        d, shifted = _weekday(d)
        return d, True if m.group(3) or shifted else False
    if "next week" in low:
        today = date.today()
        d = today + timedelta(days=(7 - today.weekday()) % 7 or 7)
        d, _ = _weekday(d)
        return d, True
    early = "early" in low
    m = re.search(rf"\b({_MONTH})\b", low)
    if m:
        key = m.group(1)
        month = MONTHS.get(key) or MONTHS[key[:3]]
        day = 1
        if early and month == 1:
            day = 5
        elif month == 1:
            day = 5
        d = date(season_year(month), month, day)
        d, shifted = _weekday(d)
        return d, True
    return None, True


_LI_X = re.compile(r"linkedin\s*(?:\+|and|&|/)\s*x\b|\+\s*x\b|\band\s+x\b|\btwitter\b|\bx\.com\b", re.I)


def detect_channels(text: str) -> list[str]:
    low = (text or "").lower()
    if re.search(r"sponsored(\s+slot)?", low):
        return ["other"]
    recurring = bool(re.search(r"every issue|until registration closes", low))
    no_nl = bool(
        re.search(r"no newsletter|not (in )?the newsletter|linkedin only|only linkedin", low)
    )
    has_nl = bool(re.search(r"newsletter", low))
    has_li = "linkedin" in low
    has_x = bool(_LI_X.search(low))
    li_x_plan = bool(re.search(r"linkedin\s*(?:\+|and|&|/)\s*x\b", low))
    if recurring:
        return ["newsletter"]
    if li_x_plan and not has_nl:
        return ["linkedin", "other"]
    if li_x_plan and no_nl:
        return ["linkedin", "other"]
    out: list[str] = []
    if has_nl and not no_nl and not (li_x_plan and not re.search(r"newsletter\s*\+\s*linkedin", low)):
        if not li_x_plan:
            out.append("newsletter")
        elif re.search(r"newsletter\s*\+", low):
            out.append("newsletter")
    if has_li:
        out.append("linkedin")
    if has_x:
        out.append("other")
    if no_nl:
        out = [c for c in out if c != "newsletter"]
        if not out:
            out = ["linkedin"]
    if not out:
        out = ["newsletter", "linkedin"]
    seen: list[str] = []
    for c in out:
        if c not in seen:
            seen.append(c)
    return seen


def _extract_date_hits(text: str) -> list[dict]:
    hits: list[dict] = []
    seen: set[tuple[int, int]] = set()
    for m in _DATE_RE.finditer(text or ""):
        mon_raw = (m.group("mon") or "").lower()
        month = MONTHS.get(mon_raw) or MONTHS.get(mon_raw[:3])
        if not month:
            continue
        qual = (m.group("qual") or "").lower()
        day = int(m.group("day")) if m.group("day") else None
        day2 = int(m.group("day2")) if m.group("day2") else None
        conference = month == 1 and day is not None and day >= 19
        if day is None:
            if month == 1:
                day = 5 if qual in ("", "early", "mid") else 15
            elif month == 12:
                day = 1
            else:
                day = 1 if qual in ("", "early") else (15 if qual == "mid" else 20)
        d = date(season_year(month), month, day)
        fuzzy = True
        if conference:
            fuzzy = True
        elif day2 or qual in ("early", "mid", "late", "by", "starting"):
            d, _ = _weekday(d)
            fuzzy = True
        else:
            d, shifted = _weekday(d)
            fuzzy = shifted
        key = (d.month, d.day)
        if key in seen:
            continue
        seen.add(key)
        hits.append(
            {
                "date": d,
                "fuzzy": fuzzy,
                "conference": conference,
                "snippet": m.group(0).strip(),
            }
        )
    return hits


def _number_dates(hits: list[dict]) -> list[dict]:
    rest = sorted([h for h in hits if not h["conference"]], key=lambda h: h["date"])
    conf = [h for h in hits if h["conference"]]
    out: list[dict] = []
    for i, h in enumerate(rest):
        n = (1, 2, 3)[i] if i < 3 else 3
        out.append({**h, "post_number": n})
    for h in conf:
        out.append({**h, "post_number": 4})
    return out


def parse_posting_dates(
    posting_dates_raw: str,
    first_post_date: str = "",
) -> list[dict]:
    text = (posting_dates_raw or "").strip()
    text = re.split(
        r"Posting Mon|Below is ready|Use the post that matches|→ Post 1",
        text,
        maxsplit=1,
        flags=re.I,
    )[0]
    channels = detect_channels(text)
    extra_note = ""
    recurring = bool(re.search(r"every issue|until registration closes", text, re.I))
    hits = _extract_date_hits(text)
    first = (first_post_date or "").strip()
    if first and not recurring:
        d0, _ = _parse_one_date(first)
        if d0:
            hits = [
                h
                for h in hits
                if not (
                    "by" in (h.get("snippet") or "").lower()
                    and h["date"].month == d0.month
                    and h["date"].year == d0.year
                    and h["date"] != d0
                )
            ]
            if not any(h["date"] == d0 for h in hits):
                hits.append(
                    {"date": d0, "fuzzy": True, "conference": False, "snippet": first}
                )
    if recurring:
        extra_note = "каждый выпуск"
        start = None
        first = (first_post_date or "").strip()
        if first:
            start, _ = _parse_one_date(first)
        if start is None and hits:
            start = sorted(hits, key=lambda h: h["date"])[0]["date"]
        if start is None:
            start, _ = _parse_one_date("Nov 20")
        hits = [
            {"date": start or date(2026, 11, 20), "fuzzy": True, "conference": False, "snippet": first or "start"},
            {
                "date": date(2027, 1, 19),
                "fuzzy": True,
                "conference": True,
                "snippet": "Jan 19–22",
            },
        ]
    numbered = _number_dates(hits)
    if first and not recurring:
        d, _ = _parse_one_date(first)
        if d:
            for item in numbered:
                if item["post_number"] == 1:
                    item["date"] = d
                    item["fuzzy"] = True
                    item["snippet"] = (item.get("snippet") or "") + f"; first_post_date {first}"
    rows: list[dict] = []
    for item in numbered:
        note = item.get("snippet") or ""
        if extra_note and extra_note not in note:
            note = (note + "; " + extra_note).strip("; ")
        for ch in channels:
            rows.append(
                {
                    "date": item["date"],
                    "channel": ch,
                    "post_number": item["post_number"],
                    "needs_check": True,
                    "notes": note,
                }
            )
    if not rows:
        d, _ = _parse_one_date(first or "Nov 20")
        for ch in channels:
            rows.append(
                {
                    "date": d or date(2026, 11, 20),
                    "channel": ch,
                    "post_number": 1,
                    "needs_check": True,
                    "notes": extra_note or posting_dates_raw or "",
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
    m = re.search(
        r"Planned posting dates:\s*(.+?)(?:Below is ready-to-use|Visuals:|Copy pack|$)",
        blob,
        re.I,
    )
    if m:
        dates = m.group(1).strip()
        dates = re.split(r"Use the post that matches", dates, maxsplit=1, flags=re.I)[0].strip()
        if len(dates) > 420:
            dates = dates[:420]
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


def kit_slug(key: str) -> str:
    name = (key or "").rsplit("/", 1)[-1]
    name = re.sub(r"-[0-9a-f]{6,}\.html$", ".html", name, flags=re.I)
    name = re.sub(r"\.html$", "", name, flags=re.I)
    name = re.sub(r"[_—\-\s]+materials.*", "", name, flags=re.I)
    return name.strip().lower() or (key or "").lower()


def scan_r2_kits() -> list[dict]:
    import store

    items = store.list_keys("vc-conf-2027/poster-mp/")
    htmls = [
        it
        for it in items
        if it["key"].lower().endswith(".html") and "materials" in it["key"].lower()
    ]
    latest: dict[str, dict] = {}
    for it in htmls:
        slug = kit_slug(it["key"])
        prev = latest.get(slug)
        if prev is None or it["last_modified"] > prev["last_modified"]:
            latest[slug] = it
    by_company: dict[str, dict] = {}
    for it in latest.values():
        slug = kit_slug(it["key"])
        if (it.get("size") or 0) > 400_000:
            continue
        raw = store.get_bytes(it["key"], max_bytes=80_000).decode("utf-8", errors="replace")
        if re.search(r"<title>\s*502\s*</title>|Bad Gateway", raw[:2000], re.I):
            continue
        parsed = parse_kit_html(raw, source_url=it["url"])
        parsed["r2_key"] = it["key"]
        parsed["last_modified"] = it["last_modified"].isoformat()
        parsed["posting_dates"] = (parsed.get("posting_dates") or "")[:400]
        key = (parsed["company"] or slug or it["key"]).strip().lower()
        by_company[key] = parsed
    return sorted(by_company.values(), key=lambda r: (r["company"] or r["r2_key"]).lower())


def _partner_row(cur, pid: int) -> dict | None:
    row = cur.execute(
        "SELECT id, company, code, reg_url, notion_page_url, posting_dates_raw, "
        "first_post_date, confirmed, created_at, notes FROM partner WHERE id=%s",
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
        "notes": row[9] or "",
        "status": "подтверждён" if row[7] else "черновик",
    }


def _changes(cur, pub_id: int) -> list[dict]:
    rows = cur.execute(
        "SELECT field, old_value, new_value, created_at FROM publication_change "
        "WHERE publication_id=%s ORDER BY created_at",
        (pub_id,),
    ).fetchall()
    return [
        {
            "field": r[0],
            "old_value": r[1],
            "new_value": r[2],
            "created_at": r[3].isoformat() if r[3] else "",
        }
        for r in rows
    ]


def _log_change(cur, partner_id: int, publication_id: int | None, field: str, old: str, new: str) -> None:
    if str(old) == str(new):
        return
    cur.execute(
        "INSERT INTO publication_change (publication_id, partner_id, field, old_value, new_value) "
        "VALUES (%s, %s, %s, %s, %s)",
        (publication_id, partner_id, field, str(old or ""), str(new or "")),
    )


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
                "changes": _changes(cur, r[0]),
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
                "first_post_date, confirmed, notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (company, code, reg_url, notion_page_url, posting_dates_raw, first_post_date, confirmed, ""),
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
    with db.connect() as conn:
        confirmed_names = {
            r[0].lower()
            for r in conn.execute("SELECT company FROM partner WHERE confirmed").fetchall()
            if r[0]
        }
    for row in scanned:
        key = row.get("r2_key") or ""
        company = (row.get("company") or "").strip()
        if key in skip or not ready_for_db(company, row.get("code") or ""):
            skipped.append(row)
            continue
        if company.lower() in confirmed_names:
            skipped.append({**row, "skip_reason": "confirmed"})
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


def mark_missed(today: date | None = None) -> int:
    today = today or date.today()
    cutoff = today - timedelta(days=2)
    with db.connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE publication SET status='missed', updated_at=NOW() "
            "WHERE date <= %s AND status NOT IN ('published', 'missed')",
            (cutoff,),
        )
        n = cur.rowcount
        conn.commit()
        return n


CHANNEL_LABELS = {
    "newsletter": "newsletter",
    "linkedin": "LinkedIn",
    "other": "other",
}
CH_SHORT = {"newsletter": "NL", "linkedin": "LI", "other": "X"}
RU_MON = {
    1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "май", 6: "июн",
    7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек",
}


def ru_day(d) -> str:
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    return f"{d.day} {RU_MON[d.month]}"


def partner_color(company: str, pid: int) -> str:
    s = f"{company}|{pid}"
    h = 0
    for ch in s:
        h = (h * 33 + ord(ch)) & 0xFFFFFFFF
    return f"hsl({h % 360} 48% 36%)"


def channels_short(channels: list[str]) -> str:
    order = ["NL", "LI", "X"]
    shorts = []
    for c in channels:
        s = CH_SHORT.get(c, "X")
        if s not in shorts:
            shorts.append(s)
    shorts.sort(key=lambda x: order.index(x) if x in order else 9)
    return "+".join(shorts)


def posts_short(numbers: list[int]) -> str:
    nums = sorted({int(n) for n in numbers})
    return "+".join(f"P{n}" for n in nums)


def group_digest_rows(rows: list[dict]) -> list[dict]:
    buckets: dict[tuple, list[dict]] = {}
    order: list[tuple] = []
    for ev in rows:
        key = (ev.get("partner_id"), ev.get("date"), ev.get("company"))
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(ev)
    out = []
    for key in order:
        items = buckets[key]
        chs = channels_short([i.get("channel") or "" for i in items])
        posts = " · ".join(f"Post {n}" for n in sorted({int(i["post_number"]) for i in items}))
        company = items[0]["company"]
        line = f"{company} — {chs} · {posts} · {ru_day(items[0]['date'])}"
        out.append(
            {
                "line": line,
                "ids": [i["id"] for i in items],
                "company": company,
                "date": items[0]["date"],
            }
        )
    return out


def reminder_text(pub: dict, partner: dict) -> str:
    n = int(pub.get("post_number") or 1)
    label = POST_LABELS.get(n, str(n))
    channel = CHANNEL_LABELS.get(pub.get("channel") or "", pub.get("channel") or "post")
    kit = (partner.get("notion_page_url") or "").strip()
    kit_line = f"Your kit: {kit}\n" if kit else ""
    return (
        f"Hi — a reminder that {pub.get('date')} is your {channel} slot "
        f"(Post {n}: {label}) for Virtual VC Conf 2027.\n\n"
        f"Promo code: {partner.get('code') or '—'}\n"
        f"Registration link: {partner.get('reg_url') or '—'}\n"
        f"{kit_line}"
        "Please post and send me the live URL when it's up. Thank you!"
    )


def calendar_bundle() -> dict:
    mark_missed()
    with db.connect() as conn:
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT pu.id, pu.date, pu.channel, pu.post_number, pu.status, pu.needs_check, "
            "pu.url, pu.notes, pu.reminded_at, pu.published_at, "
            "p.id, p.company, p.code, p.reg_url, p.notion_page_url, p.confirmed "
            "FROM publication pu JOIN partner p ON p.id = pu.partner_id "
            "ORDER BY pu.date, lower(p.company), pu.post_number"
        ).fetchall()
        drafts_n = cur.execute("SELECT COUNT(*) FROM partner WHERE NOT confirmed").fetchone()[0]
    events = []
    by_partner: dict[int, dict] = {}
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    buckets = {
        "today": [],
        "remind": [],
        "overdue": [],
        "no_url": [],
        "week": [],
        "drafts_n": int(drafts_n or 0),
    }
    seen_week: set[int] = set()
    for r in rows:
        confirmed = bool(r[15])
        color = partner_color(r[11], r[10])
        ev = {
            "id": r[0],
            "date": r[1].isoformat(),
            "channel": r[2],
            "ch_short": CH_SHORT.get(r[2], "X"),
            "post_number": r[3],
            "post_label": POST_LABELS.get(r[3], str(r[3])),
            "status": r[4],
            "needs_check": r[5],
            "url": r[6] or "",
            "notes": r[7] or "",
            "reminded_at": r[8].isoformat() if r[8] else "",
            "published_at": r[9].isoformat() if r[9] else "",
            "partner_id": r[10],
            "company": r[11],
            "code": r[12] or "",
            "reg_url": r[13] or "",
            "notion_page_url": r[14] or "",
            "confirmed": confirmed,
            "color": color,
            "title": f"{r[11]} · {CH_SHORT.get(r[2], 'X')} · P{r[3]}",
        }
        events.append(ev)
        pack = by_partner.setdefault(
            r[10],
            {"id": r[10], "company": r[11], "confirmed": confirmed, "color": color,
             "pubs": [], "done": 0, "total": 0},
        )
        pack["pubs"].append(
            {"id": ev["id"], "date": ev["date"], "channel": ev["channel"],
             "post_number": ev["post_number"], "status": ev["status"]}
        )
        if ev["status"] == "published":
            pack["done"] = pack.get("done", 0) + 1
        pack["total"] = pack.get("total", 0) + 1
        if not confirmed:
            continue
        d = r[1]
        st = r[4]
        if d == today:
            buckets["today"].append(ev)
        if today < d <= today + timedelta(days=3) and st not in ("published", "missed"):
            buckets["remind"].append(ev)
        if d < today and st != "published":
            buckets["overdue"].append(ev)
        if st == "published" and not (r[6] or "").strip():
            buckets["no_url"].append(ev)
        if monday <= d <= sunday and d != today and ev["id"] not in seen_week:
            in_other = (
                ev in buckets["today"]
                or ev in buckets["remind"]
                or ev in buckets["overdue"]
                or ev in buckets["no_url"]
            )
            if not in_other:
                buckets["week"].append(ev)
                seen_week.add(ev["id"])
    conf_ev = [e for e in events if e["confirmed"]]
    return {
        "today": today.isoformat(),
        "events": events,
        "today_panel": buckets,
        "progress": {
            "done": sum(1 for e in conf_ev if e["status"] == "published"),
            "total": len(conf_ev),
            "left": sum(1 for e in conf_ev if e["status"] != "published"),
        },
        "timeline": sorted(
            by_partner.values(),
            key=lambda x: (-(x.get("total", 0) - x.get("done", 0)), x["company"].lower()),
        ),
    }


def update_publication(pid: int, **fields) -> dict:
    allowed = {"date", "channel", "post_number", "status", "needs_check", "url", "notes"}
    with db.connect() as conn:
        cur = conn.cursor()
        old = cur.execute(
            "SELECT partner_id, date, channel, post_number, status, needs_check, url, notes "
            "FROM publication WHERE id=%s",
            (pid,),
        ).fetchone()
        if not old:
            raise ValueError("нет такого выхода")
        current = {
            "date": old[1],
            "channel": old[2],
            "post_number": old[3],
            "status": old[4],
            "needs_check": old[5],
            "url": old[6],
            "notes": old[7],
        }
        extra: dict = {}
        if "date" in fields and fields["date"] and fields["date"] != current["date"]:
            extra.setdefault("status", "rescheduled")
            old_d = current["date"].isoformat() if hasattr(current["date"], "isoformat") else str(current["date"])
            note = f"перенос с {old_d}"
            notes = fields["notes"] if "notes" in fields else (current["notes"] or "")
            if note not in (notes or ""):
                extra["notes"] = (note + (". " + notes if notes else "")).strip()
        url_in = fields.get("url", None)
        if url_in is not None and str(url_in).strip() and fields.get("status") != "missed":
            extra["status"] = "published"
        fields = {**fields, **extra}
        sets = []
        vals = []
        for k, v in fields.items():
            if k not in allowed:
                continue
            sets.append(f"{k}=%s")
            vals.append(v)
            before = current[k]
            after = v
            if k == "date":
                before = before.isoformat() if hasattr(before, "isoformat") else str(before)
                after = after.isoformat() if hasattr(after, "isoformat") else str(after)
            _log_change(cur, old[0], pid, k, before, after)
        status = fields.get("status")
        if status == "reminded":
            sets.append("reminded_at=NOW()")
        if status == "published":
            sets.append("published_at=NOW()")
        if not sets:
            raise ValueError("нечего менять")
        sets.append("updated_at=NOW()")
        vals.append(pid)
        cur.execute(
            f"UPDATE publication SET {', '.join(sets)} WHERE id=%s RETURNING partner_id",
            vals,
        )
        row = cur.fetchone()
        conn.commit()
        return {"ok": True, "partner_id": row[0]}


def get_publication(pid: int) -> dict:
    with db.connect() as conn:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT pu.id, pu.date, pu.channel, pu.post_number, pu.status, pu.needs_check, "
            "pu.url, pu.notes, p.id, p.company, p.code, p.reg_url, p.notion_page_url, p.confirmed "
            "FROM publication pu JOIN partner p ON p.id = pu.partner_id WHERE pu.id=%s",
            (pid,),
        ).fetchone()
        if not row:
            raise ValueError("нет такого выхода")
        pub = {
            "id": row[0],
            "date": row[1].isoformat(),
            "channel": row[2],
            "post_number": row[3],
            "post_label": POST_LABELS.get(row[3], str(row[3])),
            "status": row[4],
            "needs_check": row[5],
            "url": row[6] or "",
            "notes": row[7] or "",
        }
        partner = {
            "id": row[8],
            "company": row[9],
            "code": row[10] or "",
            "reg_url": row[11] or "",
            "notion_page_url": row[12] or "",
            "confirmed": bool(row[13]),
        }
        return {"publication": pub, "partner": partner, "text": reminder_text(pub, partner)}


def delete_publication(pid: int) -> None:
    with db.connect() as conn:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT partner_id, date, channel, post_number FROM publication WHERE id=%s",
            (pid,),
        ).fetchone()
        if not row:
            raise ValueError("нет такого выхода")
        _log_change(
            cur,
            row[0],
            pid,
            "deleted",
            f"{row[1].isoformat()} {row[2]} post {row[3]}",
            "",
        )
        cur.execute("DELETE FROM publication WHERE id=%s", (pid,))
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


def _full(cur, pid: int) -> dict:
    partner = _partner_row(cur, pid)
    if not partner:
        raise ValueError("нет такого партнёра")
    partner["publications"] = _pubs(cur, pid)
    return partner


def find_partner(company: str = "", code: str = "") -> dict | None:
    company = (company or "").strip()
    code = (code or "").strip().upper()
    with db.connect() as conn:
        cur = conn.cursor()
        row = None
        if company:
            row = cur.execute(
                "SELECT id FROM partner WHERE lower(company)=lower(%s)",
                (company,),
            ).fetchone()
        if not row and code:
            row = cur.execute(
                "SELECT id FROM partner WHERE code<>'' AND lower(code)=lower(%s)",
                (code,),
            ).fetchone()
        if not row:
            return None
        return _full(cur, row[0])


def get_partner(pid: int) -> dict:
    with db.connect() as conn:
        return _full(conn.cursor(), pid)


def list_partners(q: str = "") -> list[dict]:
    q = (q or "").strip()
    with db.connect() as conn:
        cur = conn.cursor()
        if q:
            like = f"%{q}%"
            ids = [
                r[0]
                for r in cur.execute(
                    "SELECT id FROM partner WHERE company ILIKE %s OR code ILIKE %s "
                    "OR reg_url ILIKE %s ORDER BY confirmed DESC, lower(company)",
                    (like, like, like),
                ).fetchall()
            ]
        else:
            ids = [
                r[0]
                for r in cur.execute(
                    "SELECT id FROM partner ORDER BY confirmed DESC, lower(company)"
                ).fetchall()
            ]
        ticks: dict[int, list[str]] = {}
        for pid, st in cur.execute(
            "SELECT partner_id, status FROM publication ORDER BY date, post_number, channel"
        ).fetchall():
            ticks.setdefault(pid, []).append(st)
        out = []
        for i in ids:
            row = _partner_row(cur, i)
            seq = ticks.get(i) or []
            done = sum(1 for s in seq if s == "published")
            missed = sum(1 for s in seq if s == "missed")
            row["pub_count"] = len(seq)
            row["done"] = done
            row["missed"] = missed
            row["left"] = max(0, len(seq) - done)
            row["ticks"] = seq
            out.append(row)
        return out


def save_partner(pid: int, **fields) -> dict:
    allowed = {
        "company",
        "code",
        "reg_url",
        "notion_page_url",
        "posting_dates_raw",
        "first_post_date",
        "notes",
        "confirmed",
    }
    sets = []
    vals = []
    for k, v in fields.items():
        if k not in allowed or v is None:
            continue
        if k == "code":
            v = str(v).strip().upper()
        elif k == "confirmed":
            v = bool(v)
        else:
            v = str(v).strip() if isinstance(v, str) else v
        sets.append(f"{k}=%s")
        vals.append(v)
    if not sets:
        return get_partner(pid)
    vals.append(pid)
    with db.connect() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE partner SET {', '.join(sets)} WHERE id=%s RETURNING id", vals)
        if not cur.fetchone():
            raise ValueError("нет такого партнёра")
        conn.commit()
        return _full(cur, pid)


def add_publication(
    partner_id: int,
    *,
    date_value: date,
    channel: str,
    post_number: int,
    notes: str = "",
    url: str = "",
) -> dict:
    channel = (channel or "newsletter").strip().lower()
    if channel not in ("newsletter", "linkedin", "other"):
        raise ValueError("канал: newsletter, linkedin или other")
    post_number = int(post_number)
    if post_number < 1 or post_number > 4:
        raise ValueError("номер поста 1–4")
    with db.connect() as conn:
        cur = conn.cursor()
        if not _partner_row(cur, partner_id):
            raise ValueError("нет такого партнёра")
        row = cur.execute(
            "INSERT INTO publication (partner_id, date, channel, post_number, status, needs_check, notes, url) "
            "VALUES (%s, %s, %s, %s, 'planned', TRUE, %s, %s) RETURNING id",
            (partner_id, date_value, channel, post_number, notes or "", url or ""),
        ).fetchone()
        _log_change(
            cur,
            partner_id,
            row[0],
            "created",
            "",
            f"{date_value.isoformat()} {channel} post {post_number}",
        )
        conn.commit()
        return _full(cur, partner_id)


def pub_key(row: dict) -> tuple:
    return (int(row["post_number"]), row["channel"])


def diff_publications(existing: list[dict], wanted: list[dict]) -> dict:
    have = {pub_key(r): r for r in existing}
    want = {pub_key(r): r for r in wanted}
    added, removed, changed = [], [], []
    for k, w in want.items():
        if k not in have:
            added.append(
                {
                    "date": w["date"].isoformat() if hasattr(w["date"], "isoformat") else str(w["date"]),
                    "channel": w["channel"],
                    "post_number": w["post_number"],
                    "notes": w.get("notes") or "",
                }
            )
        else:
            old = have[k]
            old_d = old["date"] if isinstance(old["date"], str) else old["date"].isoformat()
            new_d = w["date"].isoformat() if hasattr(w["date"], "isoformat") else str(w["date"])
            if old_d != new_d:
                changed.append(
                    {
                        "id": old.get("id"),
                        "channel": w["channel"],
                        "post_number": w["post_number"],
                        "old_date": old_d,
                        "new_date": new_d,
                        "status": old.get("status") or "planned",
                    }
                )
    for k, old in have.items():
        if k not in want:
            removed.append(
                {
                    "id": old.get("id"),
                    "date": old["date"] if isinstance(old["date"], str) else old["date"].isoformat(),
                    "channel": old["channel"],
                    "post_number": old["post_number"],
                    "status": old.get("status") or "planned",
                    "url": old.get("url") or "",
                }
            )
    return {"added": added, "removed": removed, "changed": changed}


def preview_rebuild(pid: int, posting_dates_raw: str, first_post_date: str = "") -> dict:
    partner = get_partner(pid)
    wanted = parse_posting_dates(posting_dates_raw, first_post_date)
    diff = diff_publications(partner["publications"], wanted)
    diff["partner_id"] = pid
    diff["posting_dates_raw"] = posting_dates_raw
    diff["first_post_date"] = first_post_date
    return diff


def apply_rebuild(pid: int, posting_dates_raw: str, first_post_date: str = "") -> dict:
    wanted = parse_posting_dates(posting_dates_raw, first_post_date)
    with db.connect() as conn:
        cur = conn.cursor()
        partner = _full(cur, pid)
        diff = diff_publications(partner["publications"], wanted)
        have = {pub_key(r): r for r in partner["publications"]}
        want = {pub_key(r): r for r in wanted}
        for item in diff["changed"]:
            old = have[(item["post_number"], item["channel"])]
            new_d = date.fromisoformat(item["new_date"])
            _log_change(cur, pid, old["id"], "date", item["old_date"], item["new_date"])
            cur.execute(
                "UPDATE publication SET date=%s, needs_check=TRUE, updated_at=NOW() WHERE id=%s",
                (new_d, old["id"]),
            )
        for item in diff["added"]:
            w = want[(item["post_number"], item["channel"])]
            row = cur.execute(
                "INSERT INTO publication (partner_id, date, channel, post_number, status, needs_check, notes) "
                "VALUES (%s, %s, %s, %s, 'planned', TRUE, %s) RETURNING id",
                (pid, w["date"], w["channel"], w["post_number"], w.get("notes") or ""),
            ).fetchone()
            _log_change(
                cur,
                pid,
                row[0],
                "created",
                "",
                f"{w['date'].isoformat()} {w['channel']} post {w['post_number']}",
            )
        for item in diff["removed"]:
            old = have[(item["post_number"], item["channel"])]
            _log_change(
                cur,
                pid,
                old["id"],
                "deleted",
                f"{item['date']} {item['channel']} post {item['post_number']}",
                "",
            )
            cur.execute("DELETE FROM publication WHERE id=%s", (old["id"],))
        cur.execute(
            "UPDATE partner SET posting_dates_raw=%s, first_post_date=%s WHERE id=%s",
            (posting_dates_raw or "", first_post_date or "", pid),
        )
        conn.commit()
        return _full(cur, pid)


def create_or_conflict(
    *,
    company: str,
    code: str = "",
    reg_url: str = "",
    notion_page_url: str = "",
    posting_dates_raw: str = "",
    first_post_date: str = "",
    notes: str = "",
    confirmed: bool = False,
    update_existing: bool = False,
    rebuild_pubs: bool | None = None,
) -> dict:
    existing = find_partner(company, code)
    if existing and not update_existing:
        return {"conflict": True, "existing": existing, "partner": existing}
    if existing:
        partner = upsert_partner(
            company=company or existing["company"],
            code=code or existing["code"],
            reg_url=reg_url,
            notion_page_url=notion_page_url,
            posting_dates_raw=posting_dates_raw,
            first_post_date=first_post_date,
            confirmed=confirmed,
            rebuild_pubs=False if rebuild_pubs is None else rebuild_pubs,
        )
        if notes:
            partner = save_partner(partner["id"], notes=notes)
        return {"conflict": False, "existing": existing, "partner": partner}
    partner = upsert_partner(
        company=company,
        code=code,
        reg_url=reg_url,
        notion_page_url=notion_page_url,
        posting_dates_raw=posting_dates_raw,
        first_post_date=first_post_date,
        confirmed=confirmed,
        rebuild_pubs=True if rebuild_pubs is None else rebuild_pubs,
    )
    if notes:
        partner = save_partner(partner["id"], notes=notes)
    return {"conflict": False, "existing": None, "partner": partner}
