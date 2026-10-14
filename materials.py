"""Announcement pack: 4 posts + posting plan, same job as last conf’s Notion page."""

from __future__ import annotations

import html as html_lib
from urllib.parse import quote

POSTS = [
    {
        "n": 1,
        "label": "Announcement",
        "when": "Right after the agreement, by 20 November",
        "best": "any Tue–Thu",
        "newsletter": "suggested week: any week after confirmation, through the week of 17 November",
        "headline": "Three days with VCs. Day 1 is free to watch.",
        "body": (
            "Virtual VC Conf is three days: Day 1 livestream is free (keynotes and panels). "
            "Days 2–3 are 1:1s with matched investors.\n\n"
            "If your CEO wants a pitch ticket, use code {code} for 10% off.\n\n"
            "Register: {url}"
        ),
    },
    {
        "n": 2,
        "label": "Speakers & investors",
        "when": "2–11 December",
        "best": "8–10 December",
        "newsletter": "suggested week of 8 December (window 2–11 December)",
        "headline": "The VCs on stage — and in the 1:1 rooms.",
        "body": (
            "Speakers and investors already confirmed. 380+ VCs, angels, and family offices. "
            "Matching by sector, stage, and geography.\n\n"
            "If you still have an early-bird deadline, attach it to this send.\n\n"
            "Register: {url}"
        ),
    },
    {
        "n": 3,
        "label": "New year, new round",
        "when": "5–14 January",
        "best": "6–8 or 12–14 January",
        "newsletter": "suggested week of 5 January or 12 January (window 5–14 January)",
        "headline": "New year — new round.",
        "body": (
            "Q1 is when fundraising calendars lock. Book 1:1s with investors already matched "
            "to sector, stage, and geography, plus investor-only networking.\n\n"
            "Plan the round now.\n\n"
            "Register: {url}\n"
            "Code {code} — 10% off 1:1 pitch tickets."
        ),
    },
    {
        "n": 4,
        "label": "Last call",
        "when": "19–22 January",
        "best": "20–21 January",
        "newsletter": "suggested week of 19 January (window 19–22 January)",
        "headline": "Last call: one week out.",
        "body": (
            "Full program is live. Day 1 livestream is still free. 1:1 rooms close soon.\n\n"
            "If you've been meaning to send this, this is the post.\n\n"
            "Register: {url}\n"
            "Code {code}."
        ),
    },
]

PLANS = [
    {
        "title": "Default — 4 posts (agreed by November)",
        "posts": [1, 2, 3, 4],
        "note": "Announcement before 20 Nov, then December speakers, January new-round, last call.",
    },
    {
        "title": "3 posts (skip December)",
        "posts": [1, 3, 4],
        "note": "Announcement (Oct–Nov), January 5–14, last call 19–22.",
    },
    {
        "title": "Joined in December",
        "posts": [2, 3, 4],
        "note": "First post 2–11 December, then 6–14 January and 20–22 January.",
    },
    {
        "title": "Joined in January",
        "posts": [3, 4],
        "note": "Two posts: send now, then last call 19–22 January.",
    },
]

CHANNEL_NOTE = (
    "Newsletters: give suggested weeks, not exact calendar dates — they run their own send schedule. "
    "LinkedIn: Tue–Thu, morning ET."
)


def page_title(company: str) -> str:
    return f"For {company} - VC Pitch Conf announcements"


def intro(company: str) -> str:
    return f"Great to have {company} joining as a media partner!"


def _fill(text: str, *, url: str, code: str) -> str:
    code = (code or "").strip().upper() or "the code on the site"
    url = (url or "").strip() or "https://vcconf.com/"
    return text.replace("{url}", url).replace("{code}", code)


def filled_posts(*, track_url: str, promo: str) -> list[dict]:
    out = []
    for p in POSTS:
        item = dict(p)
        item["body"] = _fill(p["body"], url=track_url, code=promo)
        out.append(item)
    return out


def markdown(*, company: str, track_url: str, promo: str, poster_url: str = "") -> str:
    lines = [
        f"# {page_title(company)}",
        "",
        intro(company),
        "",
        "## Recommended posting plan",
        "",
        CHANNEL_NOTE,
        "",
        "| # | When | Best days | Newsletter | Angle |",
        "| --- | --- | --- | --- | --- |",
    ]
    for p in POSTS:
        lines.append(
            f"| {p['n']} | {p['when']} | {p['best']} | {p['newsletter']} | {p['label']} |"
        )
    lines += ["", "### Which plan", ""]
    for plan in PLANS:
        nums = ", ".join(f"Post {n}" for n in plan["posts"])
        lines += [f"- **{plan['title']}:** {nums}. {plan['note']}", ""]
    for p in filled_posts(track_url=track_url, promo=promo):
        lines += [
            f"## Post {p['n']} — {p['label']}",
            "",
            f"*When:* {p['when']}  ",
            f"*Best days:* {p['best']}  ",
            f"*Newsletters:* {p['newsletter']}",
            "",
            f"**{p['headline']}**",
            "",
            p["body"],
            "",
        ]
        if poster_url and p["n"] == 1:
            lines += [f"![Poster]({poster_url})", ""]
    return "\n".join(lines)


def html_page(*, company: str, track_url: str, promo: str, poster_url: str) -> str:
    esc = html_lib.escape
    posts_html = []
    for p in filled_posts(track_url=track_url, promo=promo):
        img = ""
        if poster_url and p["n"] == 1:
            img = (
                f'<p><img src="{esc(poster_url)}" alt="Poster" '
                f'style="max-width:100%;border-radius:12px" /></p>'
            )
        body = "".join(f"<p>{esc(part)}</p>" for part in p["body"].split("\n\n"))
        posts_html.append(
            f"""<article class="post">
  <div class="kicker">Post {p['n']} · {esc(p['label'])}</div>
  <p class="meta">{esc(p['when'])} · best {esc(p['best'])}<br />
  Newsletters: {esc(p['newsletter'])}</p>
  <h3>{esc(p['headline'])}</h3>
  {body}
  {img}
</article>"""
        )
    plan_rows = "".join(
        f"<tr><td>{p['n']}</td><td>{esc(p['when'])}</td>"
        f"<td>{esc(p['best'])}</td><td>{esc(p['label'])}</td></tr>"
        for p in POSTS
    )
    variants = "".join(
        f"<div class='variant'><strong>{esc(pl['title'])}</strong>"
        f"<p>Posts {', '.join(str(n) for n in pl['posts'])}. {esc(pl['note'])}</p></div>"
        for pl in PLANS
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(page_title(company))}</title>
  <style>
    body {{ margin:0; font: 16px/1.5 Inter, ui-sans-serif, system-ui, sans-serif;
      background:#111; color:#f4f4f5; }}
    main {{ max-width: 760px; margin: 0 auto; padding: 48px 20px 80px; }}
    h1 {{ font-size: 28px; letter-spacing:-.03em; margin: 0 0 12px; }}
    h2 {{ font-size: 20px; margin: 36px 0 12px; }}
    h3 {{ font-size: 18px; margin: 0 0 8px; }}
    .muted {{ color:#a1a1aa; }}
    .note {{ background:#1c1c1e; border-radius:14px; padding:14px 16px; color:#d4d4d8; }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; margin: 16px 0 20px; }}
    th, td {{ text-align:left; padding:10px 8px; border-bottom:1px solid #27272a; vertical-align:top; }}
    th {{ color:#a1a1aa; font-weight:600; }}
    .variant {{ background:#1c1c1e; border-radius:14px; padding:14px 16px; margin: 10px 0; }}
    .variant p {{ margin: 6px 0 0; color:#a1a1aa; }}
    .post {{ background:#18181b; border:1px solid #27272a; border-radius:18px;
      padding:20px; margin: 16px 0; }}
    .kicker {{ font-size:12px; font-weight:700; letter-spacing:.08em; text-transform:uppercase;
      color:#f9a72a; margin-bottom:8px; }}
    .meta {{ font-size:13px; color:#a1a1aa; }}
  </style>
</head>
<body>
<main>
  <h1>{esc(page_title(company))}</h1>
  <p class="muted">{esc(intro(company))}</p>
  <h2>Recommended posting plan</h2>
  <p class="note">{esc(CHANNEL_NOTE)}</p>
  <table>
    <thead><tr><th>#</th><th>When</th><th>Best days</th><th>Angle</th></tr></thead>
    <tbody>{plan_rows}</tbody>
  </table>
  {variants}
  <h2>Posts</h2>
  {''.join(posts_html)}
</main>
</body>
</html>
"""


def notion_children(*, company: str, track_url: str, promo: str, poster_url: str) -> list[dict]:
    def rt(content: str, link: str | None = None) -> dict:
        node = {"type": "text", "text": {"content": content[:2000]}}
        if link:
            node["text"]["link"] = {"url": link}
        return node

    def para(text: str, link: str | None = None) -> dict:
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [rt(text, link)]},
        }

    def h2(text: str) -> dict:
        return {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [rt(text)]},
        }

    def h3(text: str) -> dict:
        return {
            "object": "block",
            "type": "heading_3",
            "heading_3": {"rich_text": [rt(text)]},
        }

    def bullet(text: str) -> dict:
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [rt(text)]},
        }

    kids = [
        para(intro(company)),
        h2("Recommended posting plan"),
        para(CHANNEL_NOTE),
    ]
    for p in POSTS:
        kids.append(
            bullet(
                f"Post {p['n']} · {p['label']} — {p['when']} "
                f"(best {p['best']}; newsletters: {p['newsletter']})"
            )
        )
    kids.append(h3("Which plan"))
    for pl in PLANS:
        nums = ", ".join(str(n) for n in pl["posts"])
        kids.append(bullet(f"{pl['title']}: posts {nums}. {pl['note']}"))
    for p in filled_posts(track_url=track_url, promo=promo):
        kids.append(h2(f"Post {p['n']} — {p['label']}"))
        kids.append(para(f"When: {p['when']}. Best days: {p['best']}."))
        kids.append(para(f"Newsletters: {p['newsletter']}"))
        kids.append(h3(p["headline"]))
        for part in p["body"].split("\n\n"):
            kids.append(para(part))
        if poster_url and p["n"] == 1:
            kids.append(
                {
                    "object": "block",
                    "type": "image",
                    "image": {"type": "external", "external": {"url": poster_url}},
                }
            )
    return kids


def md_filename(company: str) -> str:
    slug = quote(company.strip() or "partner", safe="")
    return f"For-{slug}-VC-Pitch-Conf-announcements.md"
