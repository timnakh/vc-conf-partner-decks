"""Partner kit page sent to the media partner."""

from __future__ import annotations

import html as html_lib
import re
from urllib.parse import quote

import speakers

BANNER_HINT = "Add the banner here and link it to your link."
VOICE_HINT = (
    "Feel free to adapt the copy to your voice. Just keep your link and your code: "
    "that's how we see the registrations from your audience."
)
POSTER_NOTE = "Attach the square poster."
POST1_WHEN_EMPTY = "as soon as possible"


def page_title(company: str) -> str:
    return f"{company} × Virtual VC Conf 2027"


def as_confirmed(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in ("1", "true", "yes", "y", "on", "confirmed", "да")


def welcome_line(company: str, confirmed: bool) -> str:
    partner = (company or "").strip() or "partner"
    if confirmed:
        return f"Great to have {partner} on board as a media partner!"
    return (
        f"Here's how a {partner} × Virtual VC Conf partnership would look, "
        "with everything ready to use."
    )


def _ctx(
    *,
    company: str,
    track_url: str,
    promo: str,
    poster_url: str = "",
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
    **_extra,
) -> dict:
    partner = (company or "").strip() or "partner"
    code = (promo or "").strip().upper() or "{{code}}"
    link = (track_url or "").strip() or "{{reg_url}}"
    short = _short_link(link)
    dates = (posting_dates or "").strip()
    own = _post_dates(dates)
    if not (first_post_date or "").strip() and own.get(1):
        first_post_date = own[1]
    post1_list, post1_when = _post1_labels(first_post_date)
    ok = as_confirmed(confirmed if confirmed is not None else _extra.get("confirmed", True))
    return {
        "partner": partner,
        "link": link,
        "short": short,
        "code_url": _code_plain(short),
        "code": code,
        "dates": dates,
        "first_post_date": (first_post_date or "").strip(),
        "post1_list": post1_list,
        "post1_when": post1_when,
        "post2_list": f"{own[2]}" if own.get(2) else POST_DEFAULTS[2][0],
        "post2_when": own.get(2) or POST_DEFAULTS[2][1],
        "post3_list": f"{own[3]}" if own.get(3) else POST_DEFAULTS[3][0],
        "post3_when": own.get(3) or POST_DEFAULTS[3][1],
        "post4_list": f"{own[4]}" if own.get(4) else POST_DEFAULTS[4][0],
        "post4_when": own.get(4) or POST_DEFAULTS[4][1],
        "poster_url": poster_url or "",
        "poster_square_url": poster_square_url or "",
        "poster_banner_url": poster_banner_url or "",
        "first_name": (first_name or "").strip(),
        "confirmed": ok,
        "welcome": welcome_line(partner, ok),
        "is_speaker": as_confirmed(is_speaker),
        "speaker_name": (speaker_name or "").strip(),
        "speaker_role": (speaker_role or "").strip(),
        "speaker_topic": (speaker_topic or "").strip(),
    }


def kit_fields(source: dict) -> dict:
    """Normalize a partner row or poster meta dict for the page builders."""
    if "confirmed" in source and source["confirmed"] is not None:
        confirmed = source["confirmed"]
    else:
        confirmed = True
    posting = source.get("posting_dates")
    if posting is None:
        posting = source.get("posting_dates_raw") or ""
    promo = source.get("promo")
    if promo is None or promo == "":
        promo = source.get("code") or ""
    return {
        "company": source.get("company") or "",
        "track_url": source.get("track_url") or source.get("reg_url") or source.get("url") or "",
        "promo": promo,
        "poster_url": source.get("poster_url") or "",
        "poster_square_url": source.get("poster_square_url") or "",
        "poster_banner_url": source.get("poster_banner_url") or "",
        "first_name": source.get("first_name") or "",
        "posting_dates": posting or "",
        "first_post_date": source.get("first_post_date") or "",
        "confirmed": confirmed,
        "is_speaker": source.get("is_speaker") or False,
        "speaker_name": source.get("speaker_name") or "",
        "speaker_role": source.get("speaker_role") or "",
        "speaker_topic": source.get("speaker_topic") or "",
    }


def _partner_speaker_line(c: dict) -> str:
    if not c.get("is_speaker"):
        return ""
    return (
        f"{c.get('speaker_name') or ''}, {c.get('speaker_role') or ''} at {c['partner']}, "
        f"speaks on the main stage on Jan 27 about {c.get('speaker_topic') or ''}."
    )


def _li(c: dict, text: str) -> str:
    if not c.get("is_speaker"):
        return text
    topic = c.get("speaker_topic") or ""
    return f"On Jan 27, I'm speaking at Virtual VC Conf about {topic}.\n\n" + text


def _blocks(*parts: str) -> str:
    return "\n\n".join(part for part in parts if part)


POST_DEFAULTS = {
    2: ("December", "Dec 1–11"),
    3: ("early January", "Jan 5–14"),
    4: ("Jan 19–22", "Jan 19–22"),
}


def _post_dates(posting_dates: str) -> dict[int, str]:
    """Spread the partner's own dates over Posts 1–4 by season window."""
    try:
        from partners import _extract_date_hits
    except Exception:
        return {}
    text = re.split(r"Posting Mon|Below is ready|Use the post that matches", posting_dates or "", maxsplit=1, flags=re.I)[0]
    found: dict[int, list[str]] = {}
    for hit in _extract_date_hits(text):
        d = hit["date"]
        if d.month in (10, 11):
            n = 1
        elif d.month == 12:
            n = 2
        elif d.month == 1 and d.day <= 14 and not hit.get("conference"):
            n = 3
        elif d.month == 1:
            n = 4
        else:
            continue
        label = re.sub(r"\s*-\s*", "–", (hit.get("snippet") or "").strip())
        if label and label not in found.setdefault(n, []):
            found[n].append(label)
    return {n: ", ".join(v) for n, v in found.items()}


def _post1_labels(first_post_date: str) -> tuple[str, str]:
    date = (first_post_date or "").strip()
    if date:
        return f"first post ({date})", date
    return "first post", POST1_WHEN_EMPTY


def _short_link(url: str) -> str:
    text = (url or "").strip()
    for prefix in ("https://", "http://"):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :]
            break
    if text.startswith("www."):
        text = text[4:]
    return text or "vcconf.com"


def _code_plain(short: str) -> str:
    # Notion autolinks vcconf.com?120 inside a code block and copies
    # <https://vcconf.com?120>. A ZWSP after the first dot stops that;
    # LinkedIn/browsers ignore it when the partner pastes.
    if "." not in short:
        return short
    host, rest = short.split(".", 1)
    return host + ".\u200b" + rest


def copies(c: dict) -> list[dict]:
    p, code, link = c["partner"], c["code"], c["link"]
    li = c["code_url"]
    who = _partner_speaker_line(c)
    p1 = speakers.for_post(1, "names")
    p1f = speakers.for_post(1, "funds")
    p2 = speakers.for_post(2, "names")
    p2f = speakers.for_post(2, "funds")
    p3 = speakers.for_post(3, "stage")
    p3f = speakers.for_post(3, "funds")
    p4 = speakers.for_post(4, "stage")
    p4f = speakers.for_post(4, "funds")
    return [
        {
            "title": "Post 1: Announcement",
            "when": c["post1_when"],
            "kicker": "ON JAN 27–29, ONLINE",
            "headline": "Pitch your startup 1:1 to matched investors at Virtual VC Conf",
            "newsletter": _blocks(
                f"{p} is partnering with Virtual VC Conf: three days online with VCs, angels, family offices and LPs. Speakers include {p1}.",
                who,
                f"**For founders raising now:** get a pass with 8-minute 1:1 pitch calls on Day 2, with investors matched to your sector, stage and geography. Pass prices go up as the event gets closer, so today's price is the lowest. Code {code} gives 10% off any pass.",
                "**Just want to listen in?** The Day 1 panels with top VCs are free to watch.",
                "**Investors:** get a free 3-day pass for committing to 15 founder pitches on Day 2.",
                f"Register at {link}",
            ),
            "linkedin": _li(
                c,
                "Raising in 2027? Here's a fast way to get in front of investors.\n\n"
                f"Virtual VC Conf, Jan 27–29, 100% online. Speakers include {p1f}.\n\n"
                "→ Day 1: VC panels + 25+ breakout rooms led by 100+ VCs & angels (free to watch)\n"
                "→ Day 2: 8-min 1:1 pitch calls with investors matched to your sector and stage\n"
                "→ Day 3: family office & LP insights + 10+ rooms led by 30+ FOs & LPs\n\n"
                f"Pass prices go up as the event gets closer. Code {code} gives 10% off any pass.\n\n"
                "Investors: free 3-day pass for committing to 15 founder pitches.\n\n"
                f"Register: {li}",
            ),
            "note": POSTER_NOTE,
            "banner_hint": BANNER_HINT,
        },
        {
            "title": "Post 2: Speakers",
            "when": c["post2_when"],
            "kicker": "ON JAN 27–29, ONLINE",
            "headline": "Meet the speakers at Virtual VC Conf",
            "newsletter": _blocks(
                f"The January lineup includes {p2}.",
                who,
                f"**For founders raising now:** get a pass with 1:1 pitch calls to pitch investors matched to your sector, stage and geography on Day 2. Prices go up as the event gets closer. Code {code} gives 10% off any pass.",
                "**Just want to listen in?** Watch the Day 1 panels for free.",
                "**Investors:** free 3-day pass for committing to 15 founder pitches on Day 2.",
                f"Register at {link}",
            ),
            "linkedin": _li(
                c,
                f"{p2f}.\n\n"
                "That's part of the lineup at Virtual VC Conf, Jan 27–29, online. On Day 2, founders pitch matched investors in 8-minute 1:1 calls. Day 1 panels are free to watch.\n\n"
                f"Prices go up as the event gets closer. Code {code} gives 10% off any pass.\n\n"
                f"Register: {li}",
            ),
            "note": POSTER_NOTE,
            "banner_hint": BANNER_HINT,
        },
        {
            "title": "Post 3: New year, new round",
            "when": c["post3_when"],
            "kicker": "ON JAN 28",
            "headline": "Raising this year? Pitch matched investors in 8-minute 1:1s",
            "newsletter": _blocks(
                "At Virtual VC Conf, founders get 1:1 calls with investors matched by sector, stage and geography. Investors can flag your deck in advance, and those meetings come first.",
                f"The day before, on Jan 27, the main stage features {p3}.",
                who,
                f"**For founders:** get a pass with 1:1 pitch calls to get on investors' calendars on Day 2. Prices go up as the event gets closer. Code {code} gives 10% off any pass.",
                "**Just want to listen in?** Day 1 panels are free to watch.",
                "**Investors:** free 3-day pass for committing to 15 founder pitches on Day 2.",
                f"Register at {link}",
            ),
            "linkedin": _li(
                c,
                "Raising this year? Here's a fast way to get in front of investors.\n\n"
                "On Jan 28, founders at Virtual VC Conf get 8-minute 1:1 calls with investors matched by sector, stage and geography. "
                f"The day before, 100+ VCs & angels lead 25+ breakout rooms, with speakers from {p3f}.\n\n"
                f"Prices go up as the event gets closer. Code {code} gives 10% off any pass. Day 1 is free to watch.\n\n"
                f"Register: {li}",
            ),
            "note": POSTER_NOTE,
            "banner_hint": BANNER_HINT,
        },
        {
            "title": "Post 4: Last call",
            "when": c["post4_when"],
            "kicker": "NEXT WEEK, JAN 27–29",
            "headline": "Last call for Virtual VC Conf",
            "newsletter": _blocks(
                f"The full program is live: 8 AM PT / 11 AM ET, 100% online, with {p4} on Day 1.",
                who,
                f"**For founders:** this is the last week to get a pass with 1:1 pitch calls with matched investors on Day 2. Prices go up until the event starts. Code {code} still gives 10% off any pass.",
                "**Just want to listen in?** Day 1 panels are free to watch.",
                "**Investors:** free 3-day pass for committing to 15 founder pitches on Day 2.",
                f"Register at {link}",
            ),
            "linkedin": _li(
                c,
                "Last call: Virtual VC Conf starts next week.\n\n"
                "Jan 27–29, 8 AM PT / 11 AM ET, 100% online:\n"
                f"→ Day 1: VC panels with {p4f} + breakout rooms led by 100+ VCs & angels (free to watch)\n"
                "→ Day 2: 1:1 pitch calls with matched investors\n"
                "→ Day 3: family offices & LPs\n\n"
                f"Last week to get a pitch pass. Code {code} gives 10% off any pass.\n\n"
                f"Register: {li}",
            ),
            "note": POSTER_NOTE,
            "banner_hint": BANNER_HINT,
        },
    ]


def markdown(
    *,
    company: str,
    track_url: str,
    promo: str,
    poster_url: str = "",
    poster_square_url: str = "",
    poster_banner_url: str = "",
    first_name: str = "",
    posting_dates: str = "",
    **extra,
) -> str:
    c = _ctx(
        company=company,
        track_url=track_url,
        promo=promo,
        poster_url=poster_url,
        poster_square_url=poster_square_url,
        poster_banner_url=poster_banner_url,
        first_name=first_name,
        posting_dates=posting_dates,
        **extra,
    )
    p, link = c["partner"], c["link"]
    lines = [
        f"# {page_title(p)}",
        "",
        c["welcome"],
        "",
        f"**Your link:** {link}",
        "",
        f"**Your code:** {c['code']} (10% off any pass)",
    ]
    if c["dates"]:
        lines += ["", f"**Planned posting dates:** {c['dates']}"]
    lines += [
        "",
        "Below is ready-to-use copy for each date, with a newsletter and a LinkedIn version. Use the post that matches your date:",
        "",
        f"- {c['post1_list']} → Post 1",
        f"- {c['post2_list']} → Post 2",
        f"- {c['post3_list']} → Post 3",
        f"- {c['post4_list']} → Post 4",
        "- only two posts → Post 1 and Post 4",
        "",
        VOICE_HINT,
        "",
        "Visuals: the banner for newsletters (link the whole image to your link), the square poster for LinkedIn, the vertical poster for anything else.",
        "",
    ]
    if c["poster_banner_url"]:
        lines += [f"![Banner for newsletters]({c['poster_banner_url']})", ""]
    if c["poster_square_url"]:
        lines += [f"![Poster for LinkedIn]({c['poster_square_url']})", ""]
    if c["poster_url"]:
        lines += [f"![Poster]({c['poster_url']})", ""]
    lines += [
        "Click an image → ⋯ → Download",
        "",
        "---",
        "",
    ]
    for item in copies(c):
        lines += [
            f"## {item['title']}",
            "",
            f"*When:* {item['when']}",
            "",
            "**Newsletter**",
            "",
            f"**{item['kicker']}**",
            "",
            f"**{item['headline']}**",
            "",
            item["newsletter"],
            "",
            item.get("banner_hint") or BANNER_HINT,
            "",
            "**LinkedIn**",
            "",
            "```",
            item["linkedin"],
            "```",
            "",
        ]
        if item.get("note"):
            lines += [item["note"], ""]
        lines += ["---", ""]
    if lines[-2] == "---":
        lines = lines[:-2]
    return "\n".join(lines).rstrip() + "\n"


def html_page(
    *,
    company: str,
    track_url: str,
    promo: str,
    poster_url: str = "",
    poster_square_url: str = "",
    poster_banner_url: str = "",
    first_name: str = "",
    posting_dates: str = "",
    **extra,
) -> str:
    c = _ctx(
        company=company,
        track_url=track_url,
        promo=promo,
        poster_url=poster_url,
        poster_square_url=poster_square_url,
        poster_banner_url=poster_banner_url,
        first_name=first_name,
        posting_dates=posting_dates,
        **extra,
    )
    esc = html_lib.escape
    p, link, code = esc(c["partner"]), esc(c["link"]), esc(c["code"])

    def rich(text: str) -> str:
        parts = text.split("**")
        return "".join(
            esc(part) if i % 2 == 0 else f"<strong>{esc(part)}</strong>"
            for i, part in enumerate(parts)
        )

    def md_inline(text: str) -> str:
        out = []
        in_list = False
        for para in text.split("\n"):
            if para.startswith("- ") or para.startswith("→ "):
                if not in_list:
                    out.append("<ul>")
                    in_list = True
                out.append(f"<li>{rich(para[2:])}</li>")
                continue
            if in_list:
                out.append("</ul>")
                in_list = False
            if para.strip():
                if para.startswith("Register at "):
                    out.append(f"<p><strong>{esc(para)}</strong></p>")
                else:
                    out.append(f"<p>{rich(para)}</p>")
        if in_list:
            out.append("</ul>")
        return "".join(out)

    posts = []
    for item in copies(c):
        note = f"<p>{esc(item['note'])}</p>" if item.get("note") else ""
        hint = item.get("banner_hint") or BANNER_HINT
        kicker = esc(item.get("kicker") or "")
        posts.append(
            f"<h2>{esc(item['title'])}</h2>"
            f"<p><em>When:</em> {esc(item['when'])}</p>"
            f"<h3>Newsletter</h3>"
            f"<p><strong>{kicker}</strong></p>"
            f"<p><strong>{esc(item['headline'])}</strong></p>"
            f"{md_inline(item['newsletter'])}"
            f"<p>{esc(hint)}</p>"
            f"<h3>LinkedIn</h3>"
            f"<pre>{esc(item['linkedin'])}</pre>"
            f"{note}"
        )
    imgs = ""
    if c["poster_banner_url"]:
        imgs += f'<p><img src="{esc(c["poster_banner_url"])}" alt="Banner for newsletters" /></p>'
    if c["poster_square_url"]:
        imgs += f'<p><img src="{esc(c["poster_square_url"])}" alt="Poster for LinkedIn" /></p>'
    if c["poster_url"]:
        imgs += f'<p><img src="{esc(c["poster_url"])}" alt="Poster" /></p>'
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(page_title(c["partner"]))}</title>
  <style>
    body {{ margin:0; background:#f8fafc; color:#0b1220;
      font: 16px/1.5 Inter, ui-sans-serif, system-ui, sans-serif; }}
    main {{ max-width: 760px; margin: 0 auto; padding: 48px 20px 80px; }}
    h1 {{ font-size: 28px; letter-spacing:-.03em; margin: 0 0 16px; }}
    h2 {{ font-size: 20px; margin: 32px 0 10px; }}
    h3 {{ font-size: 16px; margin: 18px 0 8px; }}
    pre {{ white-space: pre-wrap; background:#f1f5f9; border-radius:12px;
      padding:14px 16px; font: 14px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; }}
    img {{ max-width:100%; border-radius:12px; }}
    hr {{ border:0; border-top:1px solid #e2e8f0; margin: 28px 0; }}
    a {{ color:#1f60e0; }}
    code {{ background:#eef2ff; padding:2px 6px; border-radius:6px; }}
  </style>
</head>
<body>
<main>
  <h1>{esc(page_title(c["partner"]))}</h1>
  <p>{esc(c["welcome"])}</p>
  <p><strong>Your link:</strong> <a href="{link}">{link}</a></p>
  <p><strong>Your code:</strong> <code>{code}</code> (10% off any pass)</p>
  {f'<p><strong>Planned posting dates:</strong> {esc(c["dates"])}</p>' if c["dates"] else ""}
  <p>Below is ready-to-use copy for each date, with a newsletter and a LinkedIn version. Use the post that matches your date:</p>
  <ul>
    <li>{esc(c["post1_list"])} → Post 1</li>
    <li>{esc(c["post2_list"])} → Post 2</li>
    <li>{esc(c["post3_list"])} → Post 3</li>
    <li>{esc(c["post4_list"])} → Post 4</li>
    <li>only two posts → Post 1 and Post 4</li>
  </ul>
  <p>{esc(VOICE_HINT)}</p>
  <p>Visuals: the banner for newsletters (link the whole image to your link), the square poster for LinkedIn, the vertical poster for anything else.</p>
  {imgs}
  <p>Click an image → ⋯ → Download</p>
  <hr />
  {''.join(posts)}
</main>
</body>
</html>
"""


def notion_children(
    *,
    company: str,
    track_url: str,
    promo: str,
    poster_url: str = "",
    poster_square_url: str = "",
    poster_banner_url: str = "",
    first_name: str = "",
    posting_dates: str = "",
    **extra,
) -> list[dict]:
    c = _ctx(
        company=company,
        track_url=track_url,
        promo=promo,
        poster_url=poster_url,
        poster_square_url=poster_square_url,
        poster_banner_url=poster_banner_url,
        first_name=first_name,
        posting_dates=posting_dates,
        **extra,
    )

    def rt(content: str, *, bold: bool = False, italic: bool = False) -> dict:
        node = {"type": "text", "text": {"content": (content or "")[:2000]}}
        ann = {}
        if bold:
            ann["bold"] = True
        if italic:
            ann["italic"] = True
        if ann:
            node["annotations"] = ann
        return node

    def para(*bits: dict) -> dict:
        return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": list(bits)}}

    def h2(text: str) -> dict:
        return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [rt(text)]}}

    def h3(text: str) -> dict:
        return {"object": "block", "type": "heading_3", "heading_3": {"rich_text": [rt(text)]}}

    def plain(content: str) -> dict:
        return {"type": "text", "text": {"content": (content or "")[:2000], "link": None}}

    def code(text: str) -> dict:
        # Notion autolinks host?query inside code and copies <https://…>.
        # Split + ZWSP after '.' and '?' so the copied text is plain.
        marker = "Register: "
        idx = text.rfind(marker)
        nodes: list[dict] = []
        if idx == -1:
            nodes.append(plain(text))
        else:
            before = text[: idx + len(marker)]
            url = (text[idx + len(marker) :] or "").replace("\u200b", "")
            if before:
                nodes.append(plain(before))
            buf = ""
            for ch in url:
                if ch in ".?":
                    if buf:
                        nodes.append(plain(buf))
                        buf = ""
                    nodes.append(plain(ch + "\u200b"))
                else:
                    buf += ch
            if buf:
                nodes.append(plain(buf))
        return {
            "object": "block",
            "type": "code",
            "code": {"rich_text": nodes, "language": "plain text"},
        }

    def bullet(text: str) -> dict:
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [rt(text)]},
        }

    def bullet_bits(*bits: dict) -> dict:
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": list(bits)},
        }

    def md_bits(text: str) -> list[dict]:
        parts = (text or "").split("**")
        out: list[dict] = []
        for i, part in enumerate(parts):
            if part:
                out.append(rt(part, bold=i % 2 == 1))
        return out or [rt("")]

    def divider() -> dict:
        return {"object": "block", "type": "divider", "divider": {}}

    def image(url: str) -> dict:
        return {
            "object": "block",
            "type": "image",
            "image": {"type": "external", "external": {"url": url}},
        }

    p = c["partner"]
    kids = [
        para(rt(c["welcome"])),
        para(rt("Your link: ", bold=True), rt(c["link"])),
        para(rt("Your code: ", bold=True), rt(c["code"] + " (10% off any pass)")),
    ]
    if c["dates"]:
        kids.append(para(rt("Planned posting dates: ", bold=True), rt(c["dates"])))
    kids += [
        para(rt("Below is ready-to-use copy for each date, with a newsletter and a LinkedIn version. Use the post that matches your date:")),
        bullet(f"{c['post1_list']} → Post 1"),
        bullet(f"{c['post2_list']} → Post 2"),
        bullet(f"{c['post3_list']} → Post 3"),
        bullet(f"{c['post4_list']} → Post 4"),
        bullet("only two posts → Post 1 and Post 4"),
        para(rt(VOICE_HINT)),
        para(rt("Visuals: the banner for newsletters (link the whole image to your link), the square poster for LinkedIn, the vertical poster for anything else.")),
    ]
    if c["poster_banner_url"]:
        kids.append(image(c["poster_banner_url"]))
    if c["poster_square_url"]:
        kids.append(image(c["poster_square_url"]))
    if c["poster_url"]:
        kids.append(image(c["poster_url"]))
    kids.append(para(rt("Click an image → ⋯ → Download")))
    kids.append(divider())
    for item in copies(c):
        kids.append(h2(item["title"]))
        kids.append(para(rt("When: ", italic=True), rt(item["when"])))
        kids.append(h3("Newsletter"))
        kids.append(para(rt(item["kicker"], bold=True)))
        kids.append(para(rt(item["headline"], bold=True)))
        for chunk in item["newsletter"].split("\n\n"):
            lines = [ln for ln in chunk.split("\n") if ln.strip()]
            if lines and all(ln.startswith("- ") for ln in lines):
                for ln in lines:
                    kids.append(bullet_bits(*md_bits(ln[2:])))
            elif chunk.startswith("Register at "):
                kids.append(para(rt(chunk, bold=True)))
            else:
                kids.append(para(*md_bits(chunk.replace("\n", " "))))
        kids.append(para(rt(item.get("banner_hint") or BANNER_HINT)))
        kids.append(h3("LinkedIn"))
        kids.append(code(item["linkedin"]))
        if item.get("note"):
            kids.append(para(rt(item["note"])))
        kids.append(divider())
    if kids and kids[-1]["type"] == "divider":
        kids.pop()
    return kids


def md_filename(company: str) -> str:
    slug = quote(company.strip() or "partner", safe="")
    return f"VC-Conf-2027-{slug}-Partner-Kit.md"
