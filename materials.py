"""Partner kit page: copy, plan, perks — sent to the media partner."""

from __future__ import annotations

import html as html_lib
from urllib.parse import quote


def page_title(company: str) -> str:
    return f"VC Conf 2027 × {company} — Partner Kit"


def _ctx(
    *,
    company: str,
    track_url: str,
    promo: str,
    poster_url: str = "",
    first_name: str = "",
    speaker_1: str = "{{speaker_1}}",
    speaker_2: str = "{{speaker_2}}",
    speaker_3: str = "{{speaker_3}}",
    date_1: str = "{{date_1}}",
    date_2: str = "{{date_2}}",
    date_3: str = "{{date_3}}",
    date_4: str = "{{date_4}}",
    visuals_folder_link: str = "",
) -> dict:
    partner = (company or "").strip() or "partner"
    code = (promo or "").strip().upper() or "{{promo_code}}"
    link = (track_url or "").strip() or "{{ref_link}}"
    first = (first_name or "").strip()
    hi = f"Hi {first}, welcome on board!" if first else "Hi, welcome on board!"
    return {
        "partner": partner,
        "first": first,
        "hi": hi,
        "link": link,
        "code": code,
        "poster_url": poster_url or "",
        "speaker_1": speaker_1,
        "speaker_2": speaker_2,
        "speaker_3": speaker_3,
        "date_1": date_1,
        "date_2": date_2,
        "date_3": date_3,
        "date_4": date_4,
        "visuals_folder_link": visuals_folder_link,
    }


def copies(c: dict) -> list[dict]:
    p, code, link = c["partner"], c["code"], c["link"]
    s1, s2, s3 = c["speaker_1"], c["speaker_2"], c["speaker_3"]
    return [
        {
            "title": "Send 1 — Announcement (newsletter)",
            "body": (
                f"**Subject / headline:** Free invite: VC Conf, Jan 27–29 (virtual)\n\n"
                f"VC Conf is back for its 24th edition — three days of investor insights "
                f"and 1:1 pitching, fully online, Jan 27–29.\n\n"
                f"- **Day 1:** top-VC panels + 25+ breakout rooms led by 100+ investors\n"
                f"- **Day 2:** 8-minute 1:1 calls between founders and matched investors\n"
                f"- **Day 3:** family office & LP insights\n\n"
                f"The Day 1 livestream is free for {p} readers. Raising this year? "
                f"Day 2 puts you in front of investors matched to your stage and sector — "
                f"use code {code} for 10% off any pass.\n\n"
                f"Register: {link}"
            ),
        },
        {
            "title": "Send 1 — Announcement (LinkedIn)",
            "body": (
                f"Raising in 2027? VC Conf is back on Jan 27–29, fully virtual.\n\n"
                f"→ Day 1: top-VC panels + 25+ investor-led breakout rooms\n"
                f"→ Day 2: 8-minute 1:1 calls with investors matched to your stage\n"
                f"→ Day 3: family office & LP insights\n\n"
                f"The Day 1 livestream is free. Code {code} = 10% off any pass.\n"
                f"{link}"
            ),
        },
        {
            "title": "Send 2 — Speakers (December)",
            "body": (
                f"**Headline:** Who's speaking at VC Conf this January\n\n"
                f"The lineup for VC Conf (Jan 27–29, virtual) is coming together: "
                f"{s1}, {s2}, {s3} and 100+ investors leading breakout rooms on Day 1.\n\n"
                f"Last edition drew 8,800+ registrations, including 1,300+ investors. "
                f"The Day 1 livestream is free — and with a pass, founders get 1:1 calls "
                f"with matched investors on Day 2.\n\n"
                f"Code {code} for 10% off: {link}"
            ),
        },
        {
            "title": "Send 3 — Raising in Q1 (January)",
            "body": (
                f"**Headline:** Planning to raise in Q1? Start with 1:1s on Jan 28\n\n"
                f"On Day 2 of VC Conf, founders get 8-minute 1:1 calls with investors "
                f"matched to their stage and sector — no travel, no cold emails.\n\n"
                f"Plus top-VC panels on Day 1 (free livestream) and family office & LP "
                f"insights on Day 3. Jan 27–29, virtual.\n\n"
                f"Code {code} for 10% off: {link}"
            ),
        },
        {
            "title": "Send 4 — Last call (Jan 19–22)",
            "body": (
                f"VC Conf starts next Wednesday, Jan 27. Last chance to grab a pass for "
                f"Day 2 1:1 calls with matched investors — or join the Day 1 livestream "
                f"for free.\n\n"
                f"Code {code} for 10% off: {link}"
            ),
        },
    ]


def markdown(
    *,
    company: str,
    track_url: str,
    promo: str,
    poster_url: str = "",
    first_name: str = "",
    **extra,
) -> str:
    c = _ctx(
        company=company,
        track_url=track_url,
        promo=promo,
        poster_url=poster_url,
        first_name=first_name,
        **{k: v for k, v in extra.items() if k in {
            "speaker_1", "speaker_2", "speaker_3",
            "date_1", "date_2", "date_3", "date_4",
            "visuals_folder_link",
        }},
    )
    p, link, code = c["partner"], c["link"], c["code"]
    lines = [
        f"# {page_title(p)}",
        "",
        f"> 👋 {c['hi']} Everything you need to promote VC Conf is on this page: "
        f"your link and code, the suggested schedule, ready-made copy and visuals.",
        "",
        "## Your link and code",
        "",
        f"- **Tracking link:** `{link}`",
        f"- **Promo code (10% off any pass):** `{code}`",
        "- **Free for your audience:** Day 1 livestream (Jan 27, from 11:00 AM ET) — registration via your link",
        "",
        "> ⚠️ Please always use your tracking link — that's how we count registrations and sales for your perks.",
        "",
        "---",
        "",
        "## Promotion plan",
        "",
        "| # | Suggested window | Format | Angle |",
        "| --- | --- | --- | --- |",
        "| 1 | Right away, by Nov 20 | Dedicated email or top of issue / post | Announcement + free Day 1 livestream |",
        "| 2 | Dec 2–11 | Dedicated email or top of issue / post | Speakers and investors |",
        "| 3 | Jan 5–14 | Dedicated email or top of issue / post | Raising in Q1: 1:1 calls with matched investors |",
        "| 4 | Jan 19–22 | Short mention or post | Last call — starts next week |",
        "",
        "- Please avoid Nov 23 – Dec 1 (Thanksgiving, Black Friday) and Dec 18 – Jan 4 (holidays) — inboxes are overloaded.",
        "- For newsletters, we ask that each send is a dedicated email or placed at the top of your issue.",
        "- Once a send or post is out, just reply with a link or screenshot.",
        "",
        "**Your confirmed dates:**",
        "",
        f"- [ ] Send 1: {c['date_1']}",
        f"- [ ] Send 2: {c['date_2']}",
        f"- [ ] Send 3: {c['date_3']}",
        f"- [ ] Send 4: {c['date_4']}",
        "",
        "---",
        "",
        "## Your perks",
        "",
        "### For promoting VC Conf",
        "",
        "| Your audience | What you get |",
        "| --- | --- |",
        "| 3K+ | Your offer in our Free Partner Perks section + a feature in our email to 5K+ attendees |",
        "| 10K+ | Our Super Networking List — 2,500+ GPs, angels, LPs and family offices (for networking, not for mailing) |",
        "| 30K+ | Your offer in our 60K+ email — or, if you bring 100+ registrations, 10x that number in new subscribers to your newsletter |",
        "| 100K+ | Co-host status and full-audience access (goal: 1,000+ registrations or 60+ sales) |",
        "",
        "### For ticket sales through your link",
        "",
        "| Sales | Perk |",
        "| --- | --- |",
        "| 3+ | Free pass to Days 1 & 3 on Zoom, incl. networking |",
        "| 5+ | Super Networking List — 2,500+ GPs, angels, LPs and family offices |",
        "| 10+ | A 10-minute slot in a Day 1 breakout room or a 3.5-minute keynote on the main stage |",
        "| 25+ | A dedicated email about you to our conference audience after the event |",
        "",
        "> 📊 Want to know where you stand? Ask us anytime for your current registrations and sales.",
        "",
        "---",
        "",
        "## Your offer for our attendees",
        "",
        "Founders browse our Free Partner Perks page right before their investor calls. "
        "Add something free or discounted for them — a trial, a discount, a consultation — "
        "and we'll promote it to our whole audience.",
        "",
        "**Please send us:**",
        "",
        "- [ ] Logo (PNG or SVG, transparent background)",
        f"- [ ] 1–2 sentences about {p}",
        "- [ ] Link for founders (CTA)",
        "- [ ] Your offer for attendees (optional)",
        "",
        "---",
        "",
        "## About the event",
        "",
        "**VC Conf — Jan 27–29, 2027, fully virtual.** Our 24th event. The September edition drew 8,800+ registrations, including 3,300+ startups and 1,300+ investors.",
        "",
        "- **Day 1 — VC & Startup Insights:** top-VC panels and keynotes, plus 25+ breakout rooms led by 100+ investors",
        "- **Day 2 — 1:1 Pitches:** 8-minute calls between founders and investors matched to their stage and sector",
        "- **Day 3 — Family Office & LP Insights:** panels and rooms with LPs and family offices",
        "",
        "700+ speakers from 650+ firms across our events, including a16z, 500 Global, Techstars, USV and Hustle Fund. 230+ media partners, including Carta, Crunchbase, PitchBook and Startup Grind.",
        "",
        "---",
        "",
        "## Ready-made copy",
        "",
        "Use as is or adapt to your voice — just keep your link.",
        "",
    ]
    for item in copies(c):
        lines += [
            f"<details>",
            f"<summary><strong>{item['title']}</strong></summary>",
            "",
            item["body"],
            "",
            "</details>",
            "",
        ]
    lines += [
        "---",
        "",
        "## Visuals",
        "",
    ]
    if c["poster_url"]:
        lines += [f"![Poster]({c['poster_url']})", ""]
    lines += [
        "Newsletter banner 1200×628 and LinkedIn square 1080×1080 — we'll add those when the new templates are ready.",
        "",
    ]
    if c["visuals_folder_link"]:
        lines += [f"Download all: {c['visuals_folder_link']}", ""]
    return "\n".join(lines)


def html_page(
    *,
    company: str,
    track_url: str,
    promo: str,
    poster_url: str = "",
    first_name: str = "",
    **extra,
) -> str:
    c = _ctx(
        company=company,
        track_url=track_url,
        promo=promo,
        poster_url=poster_url,
        first_name=first_name,
        **{k: v for k, v in extra.items() if k in {
            "speaker_1", "speaker_2", "speaker_3",
            "date_1", "date_2", "date_3", "date_4",
            "visuals_folder_link",
        }},
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
                out.append(f"<p>{rich(para)}</p>")
        if in_list:
            out.append("</ul>")
        return "".join(out)

    details = []
    for item in copies(c):
        details.append(
            f"<details><summary>{esc(item['title'])}</summary>"
            f"<div class='copy'>{md_inline(item['body'])}</div></details>"
        )
    poster = (
        f'<p><img src="{esc(c["poster_url"])}" alt="Poster" /></p>'
        if c["poster_url"]
        else ""
    )
    folder = (
        f'<p><a href="{esc(c["visuals_folder_link"])}">Download all visuals</a></p>'
        if c["visuals_folder_link"]
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(page_title(c["partner"]))}</title>
  <style>
    body {{ margin:0; background:#0b1220; color:#f4f4f5;
      font: 16px/1.5 Inter, ui-sans-serif, system-ui, sans-serif; }}
    main {{ max-width: 760px; margin: 0 auto; padding: 48px 20px 80px; }}
    h1 {{ font-size: 28px; letter-spacing:-.03em; margin: 0 0 16px; }}
    h2 {{ font-size: 20px; margin: 36px 0 12px; }}
    h3 {{ font-size: 16px; margin: 20px 0 8px; }}
    .callout {{ border-radius: 14px; padding: 14px 16px; margin: 16px 0; }}
    .hi {{ background:#1e293b; }}
    .warn {{ background:#422006; }}
    .stat {{ background:#1e293b; }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; margin: 12px 0 18px; }}
    th, td {{ text-align:left; padding:10px 8px; border-bottom:1px solid #1f2937; vertical-align:top; }}
    th {{ color:#94a3b8; font-weight:600; }}
    code {{ background:#1e293b; padding:2px 6px; border-radius:6px; font-size:13px; }}
    details {{ background:#111827; border:1px solid #1f2937; border-radius:14px;
      padding:12px 16px; margin: 10px 0; }}
    summary {{ cursor:pointer; font-weight:700; }}
    .copy {{ margin-top:12px; color:#e4e4e7; }}
    img {{ max-width:100%; border-radius:12px; }}
    hr {{ border:0; border-top:1px solid #1f2937; margin: 28px 0; }}
    a {{ color:#38bdf8; }}
  </style>
</head>
<body>
<main>
  <h1>{esc(page_title(c["partner"]))}</h1>
  <div class="callout hi">👋 {esc(c["hi"])} Everything you need to promote VC Conf is on this page: your link and code, the suggested schedule, ready-made copy and visuals.</div>
  <h2>Your link and code</h2>
  <ul>
    <li><strong>Tracking link:</strong> <code>{link}</code></li>
    <li><strong>Promo code (10% off any pass):</strong> <code>{code}</code></li>
    <li><strong>Free for your audience:</strong> Day 1 livestream (Jan 27, from 11:00 AM ET) — registration via your link</li>
  </ul>
  <div class="callout warn">⚠️ Please always use your tracking link — that's how we count registrations and sales for your perks.</div>
  <hr />
  <h2>Promotion plan</h2>
  <table>
    <thead><tr><th>#</th><th>Suggested window</th><th>Format</th><th>Angle</th></tr></thead>
    <tbody>
      <tr><td>1</td><td>Right away, by Nov 20</td><td>Dedicated email or top of issue / post</td><td>Announcement + free Day 1 livestream</td></tr>
      <tr><td>2</td><td>Dec 2–11</td><td>Dedicated email or top of issue / post</td><td>Speakers and investors</td></tr>
      <tr><td>3</td><td>Jan 5–14</td><td>Dedicated email or top of issue / post</td><td>Raising in Q1: 1:1 calls with matched investors</td></tr>
      <tr><td>4</td><td>Jan 19–22</td><td>Short mention or post</td><td>Last call — starts next week</td></tr>
    </tbody>
  </table>
  <ul>
    <li>Please avoid Nov 23 – Dec 1 (Thanksgiving, Black Friday) and Dec 18 – Jan 4 (holidays) — inboxes are overloaded.</li>
    <li>For newsletters, we ask that each send is a dedicated email or placed at the top of your issue.</li>
    <li>Once a send or post is out, just reply with a link or screenshot.</li>
  </ul>
  <p><strong>Your confirmed dates:</strong></p>
  <ul>
    <li>[ ] Send 1: {esc(c["date_1"])}</li>
    <li>[ ] Send 2: {esc(c["date_2"])}</li>
    <li>[ ] Send 3: {esc(c["date_3"])}</li>
    <li>[ ] Send 4: {esc(c["date_4"])}</li>
  </ul>
  <hr />
  <h2>Your perks</h2>
  <h3>For promoting VC Conf</h3>
  <table>
    <thead><tr><th>Your audience</th><th>What you get</th></tr></thead>
    <tbody>
      <tr><td>3K+</td><td>Your offer in our Free Partner Perks section + a feature in our email to 5K+ attendees</td></tr>
      <tr><td>10K+</td><td>Our Super Networking List — 2,500+ GPs, angels, LPs and family offices (for networking, not for mailing)</td></tr>
      <tr><td>30K+</td><td>Your offer in our 60K+ email — or, if you bring 100+ registrations, 10x that number in new subscribers to your newsletter</td></tr>
      <tr><td>100K+</td><td>Co-host status and full-audience access (goal: 1,000+ registrations or 60+ sales)</td></tr>
    </tbody>
  </table>
  <h3>For ticket sales through your link</h3>
  <table>
    <thead><tr><th>Sales</th><th>Perk</th></tr></thead>
    <tbody>
      <tr><td>3+</td><td>Free pass to Days 1 &amp; 3 on Zoom, incl. networking</td></tr>
      <tr><td>5+</td><td>Super Networking List — 2,500+ GPs, angels, LPs and family offices</td></tr>
      <tr><td>10+</td><td>A 10-minute slot in a Day 1 breakout room or a 3.5-minute keynote on the main stage</td></tr>
      <tr><td>25+</td><td>A dedicated email about you to our conference audience after the event</td></tr>
    </tbody>
  </table>
  <div class="callout stat">📊 Want to know where you stand? Ask us anytime for your current registrations and sales.</div>
  <hr />
  <h2>Your offer for our attendees</h2>
  <p>Founders browse our Free Partner Perks page right before their investor calls. Add something free or discounted for them — a trial, a discount, a consultation — and we'll promote it to our whole audience.</p>
  <p><strong>Please send us:</strong></p>
  <ul>
    <li>[ ] Logo (PNG or SVG, transparent background)</li>
    <li>[ ] 1–2 sentences about {p}</li>
    <li>[ ] Link for founders (CTA)</li>
    <li>[ ] Your offer for attendees (optional)</li>
  </ul>
  <hr />
  <h2>About the event</h2>
  <p><strong>VC Conf — Jan 27–29, 2027, fully virtual.</strong> Our 24th event. The September edition drew 8,800+ registrations, including 3,300+ startups and 1,300+ investors.</p>
  <ul>
    <li><strong>Day 1 — VC &amp; Startup Insights:</strong> top-VC panels and keynotes, plus 25+ breakout rooms led by 100+ investors</li>
    <li><strong>Day 2 — 1:1 Pitches:</strong> 8-minute calls between founders and investors matched to their stage and sector</li>
    <li><strong>Day 3 — Family Office &amp; LP Insights:</strong> panels and rooms with LPs and family offices</li>
  </ul>
  <p>700+ speakers from 650+ firms across our events, including a16z, 500 Global, Techstars, USV and Hustle Fund. 230+ media partners, including Carta, Crunchbase, PitchBook and Startup Grind.</p>
  <hr />
  <h2>Ready-made copy</h2>
  <p>Use as is or adapt to your voice — just keep your link.</p>
  {''.join(details)}
  <hr />
  <h2>Visuals</h2>
  {poster}
  <p>Newsletter banner 1200×628 and LinkedIn square 1080×1080 — we'll add those when the new templates are ready.</p>
  {folder}
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
    first_name: str = "",
    **extra,
) -> list[dict]:
    c = _ctx(
        company=company,
        track_url=track_url,
        promo=promo,
        poster_url=poster_url,
        first_name=first_name,
        **{k: v for k, v in extra.items() if k in {
            "speaker_1", "speaker_2", "speaker_3",
            "date_1", "date_2", "date_3", "date_4",
            "visuals_folder_link",
        }},
    )

    def rt(content: str, *, bold: bool = False, code: bool = False, link: str | None = None) -> dict:
        node = {"type": "text", "text": {"content": (content or "")[:2000]}}
        if link:
            node["text"]["link"] = {"url": link}
        ann = {}
        if bold:
            ann["bold"] = True
        if code:
            ann["code"] = True
        if ann:
            node["annotations"] = ann
        return node

    def para(*bits: dict) -> dict:
        return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": list(bits)}}

    def h2(text: str) -> dict:
        return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": [rt(text)]}}

    def h3(text: str) -> dict:
        return {"object": "block", "type": "heading_3", "heading_3": {"rich_text": [rt(text)]}}

    def bullet(*bits: dict) -> dict:
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": list(bits)},
        }

    def todo(text: str) -> dict:
        return {
            "object": "block",
            "type": "to_do",
            "to_do": {"rich_text": [rt(text)], "checked": False},
        }

    def callout(emoji: str, text: str) -> dict:
        return {
            "object": "block",
            "type": "callout",
            "callout": {
                "icon": {"type": "emoji", "emoji": emoji},
                "rich_text": [rt(text)],
            },
        }

    def divider() -> dict:
        return {"object": "block", "type": "divider", "divider": {}}

    def table(headers: list[str], rows: list[list[str]]) -> dict:
        def cells(vals: list[str], header: bool = False) -> dict:
            return {
                "type": "table_row",
                "table_row": {
                    "cells": [[rt(v, bold=header)] for v in vals]
                },
            }

        kids = [cells(headers, True)]
        kids.extend(cells(row) for row in rows)
        return {
            "object": "block",
            "type": "table",
            "table": {
                "table_width": len(headers),
                "has_column_header": True,
                "children": kids,
            },
        }

    def toggle(title: str, body: str) -> dict:
        children = []
        for chunk in body.split("\n\n"):
            children.append(para(rt(chunk)))
        return {
            "object": "block",
            "type": "toggle",
            "toggle": {"rich_text": [rt(title, bold=True)], "children": children},
        }

    p, link, code = c["partner"], c["link"], c["code"]
    kids = [
        callout(
            "👋",
            f"{c['hi']} Everything you need to promote VC Conf is on this page: "
            "your link and code, the suggested schedule, ready-made copy and visuals.",
        ),
        h2("Your link and code"),
        bullet(rt("Tracking link: ", bold=True), rt(link, code=True)),
        bullet(rt("Promo code (10% off any pass): ", bold=True), rt(code, code=True)),
        bullet(
            rt("Free for your audience: ", bold=True),
            rt("Day 1 livestream (Jan 27, from 11:00 AM ET) — registration via your link"),
        ),
        callout(
            "⚠️",
            "Please always use your tracking link — that's how we count registrations and sales for your perks.",
        ),
        divider(),
        h2("Promotion plan"),
        table(
            ["#", "Suggested window", "Format", "Angle"],
            [
                ["1", "Right away, by Nov 20", "Dedicated email or top of issue / post", "Announcement + free Day 1 livestream"],
                ["2", "Dec 2–11", "Dedicated email or top of issue / post", "Speakers and investors"],
                ["3", "Jan 5–14", "Dedicated email or top of issue / post", "Raising in Q1: 1:1 calls with matched investors"],
                ["4", "Jan 19–22", "Short mention or post", "Last call — starts next week"],
            ],
        ),
        bullet(rt("Please avoid Nov 23 – Dec 1 (Thanksgiving, Black Friday) and Dec 18 – Jan 4 (holidays) — inboxes are overloaded.")),
        bullet(rt("For newsletters, we ask that each send is a dedicated email or placed at the top of your issue.")),
        bullet(rt("Once a send or post is out, just reply with a link or screenshot.")),
        para(rt("Your confirmed dates:", bold=True)),
        todo(f"Send 1: {c['date_1']}"),
        todo(f"Send 2: {c['date_2']}"),
        todo(f"Send 3: {c['date_3']}"),
        todo(f"Send 4: {c['date_4']}"),
        divider(),
        h2("Your perks"),
        h3("For promoting VC Conf"),
        table(
            ["Your audience", "What you get"],
            [
                ["3K+", "Your offer in our Free Partner Perks section + a feature in our email to 5K+ attendees"],
                ["10K+", "Our Super Networking List — 2,500+ GPs, angels, LPs and family offices (for networking, not for mailing)"],
                ["30K+", "Your offer in our 60K+ email — or, if you bring 100+ registrations, 10x that number in new subscribers to your newsletter"],
                ["100K+", "Co-host status and full-audience access (goal: 1,000+ registrations or 60+ sales)"],
            ],
        ),
        h3("For ticket sales through your link"),
        table(
            ["Sales", "Perk"],
            [
                ["3+", "Free pass to Days 1 & 3 on Zoom, incl. networking"],
                ["5+", "Super Networking List — 2,500+ GPs, angels, LPs and family offices"],
                ["10+", "A 10-minute slot in a Day 1 breakout room or a 3.5-minute keynote on the main stage"],
                ["25+", "A dedicated email about you to our conference audience after the event"],
            ],
        ),
        callout("📊", "Want to know where you stand? Ask us anytime for your current registrations and sales."),
        divider(),
        h2("Your offer for our attendees"),
        para(rt(
            "Founders browse our Free Partner Perks page right before their investor calls. "
            "Add something free or discounted for them — a trial, a discount, a consultation — "
            "and we'll promote it to our whole audience."
        )),
        para(rt("Please send us:", bold=True)),
        todo("Logo (PNG or SVG, transparent background)"),
        todo(f"1–2 sentences about {p}"),
        todo("Link for founders (CTA)"),
        todo("Your offer for attendees (optional)"),
        divider(),
        h2("About the event"),
        para(rt(
            "VC Conf — Jan 27–29, 2027, fully virtual. Our 24th event. The September edition "
            "drew 8,800+ registrations, including 3,300+ startups and 1,300+ investors.",
            bold=True,
        )),
        bullet(rt("Day 1 — VC & Startup Insights: ", bold=True), rt("top-VC panels and keynotes, plus 25+ breakout rooms led by 100+ investors")),
        bullet(rt("Day 2 — 1:1 Pitches: ", bold=True), rt("8-minute calls between founders and investors matched to their stage and sector")),
        bullet(rt("Day 3 — Family Office & LP Insights: ", bold=True), rt("panels and rooms with LPs and family offices")),
        para(rt(
            "700+ speakers from 650+ firms across our events, including a16z, 500 Global, Techstars, "
            "USV and Hustle Fund. 230+ media partners, including Carta, Crunchbase, PitchBook and Startup Grind."
        )),
        divider(),
        h2("Ready-made copy"),
        para(rt("Use as is or adapt to your voice — just keep your link.")),
    ]
    for item in copies(c):
        kids.append(toggle(item["title"], item["body"]))
    kids += [divider(), h2("Visuals")]
    if c["poster_url"]:
        kids.append(
            {
                "object": "block",
                "type": "image",
                "image": {"type": "external", "external": {"url": c["poster_url"]}},
            }
        )
    kids.append(para(rt(
        "Newsletter banner 1200×628 and LinkedIn square 1080×1080 — we'll add those when the new templates are ready."
    )))
    if c["visuals_folder_link"]:
        kids.append(para(rt("Download all: ", bold=True), rt(c["visuals_folder_link"], link=c["visuals_folder_link"])))
    return kids


def md_filename(company: str) -> str:
    slug = quote(company.strip() or "partner", safe="")
    return f"VC-Conf-2027-{slug}-Partner-Kit.md"
