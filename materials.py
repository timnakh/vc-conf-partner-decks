"""Partner kit page sent to the media partner."""

from __future__ import annotations

import html as html_lib
from urllib.parse import quote

DEFAULT_DATES = (
    "3–4 posts (newsletter + LinkedIn): by Nov 20, early Dec, early Jan, "
    "Jan 19–22. Posting Mon–Fri 9–11 am EST"
)


def page_title(company: str) -> str:
    return f"{company} × Virtual VC Conf 2027"


def _ctx(
    *,
    company: str,
    track_url: str,
    promo: str,
    poster_url: str = "",
    poster_square_url: str = "",
    first_name: str = "",
    posting_dates: str = "",
    **_extra,
) -> dict:
    partner = (company or "").strip() or "partner"
    code = (promo or "").strip().upper() or "{{code}}"
    link = (track_url or "").strip() or "{{reg_url}}"
    dates = (posting_dates or "").strip() or DEFAULT_DATES
    return {
        "partner": partner,
        "link": link,
        "code_url": _code_url(link),
        "code": code,
        "dates": dates,
        "poster_url": poster_url or "",
        "poster_square_url": poster_square_url or "",
        "first_name": (first_name or "").strip(),
    }


def _code_url(url: str) -> str:
    # Notion autolinks https://… inside a code block and copies it as <https://…>.
    # A zero-width space after :// keeps the visible URL intact and copy-safe.
    if url.startswith("https://"):
        return "https://\u200b" + url[len("https://") :]
    if url.startswith("http://"):
        return "http://\u200b" + url[len("http://") :]
    return url


def copies(c: dict) -> list[dict]:
    p, code, link = c["partner"], c["code"], c["link"]
    li = c["code_url"]
    return [
        {
            "title": "Post 1: Announcement",
            "when": "by Nov 20",
            "headline": (
                "Free Virtual VC Conf, Jan 27–29: meet 1,000+ VCs, angels, "
                "family offices & LPs"
            ),
            "newsletter": (
                f"{p} is a media partner of Virtual VC Conf 2027, three days, 100% online:\n\n"
                "- **Day 1, Jan 27:** VC panels + networking in 25+ breakout rooms led by 100+ VCs & angels. Free livestream.\n"
                "- **Day 2, Jan 28:** 8-minute 1:1 pitch calls with matched investors + investor-only networking.\n"
                "- **Day 3, Jan 29:** family office & LP insights + 10+ rooms led by 30+ FOs & LPs.\n\n"
                f"Investors get a free 3-day pass. Founders get 10% off pitch tickets with code {code}.\n\n"
                f"Register free: {link}"
            ),
            "linkedin": (
                "We're a media partner of Virtual VC Conf 2027, and it's free to join 🎉\n\n"
                "Jan 27–29, 100% online. Meet 1,000+ VCs, angels, family offices & LPs:\n\n"
                "→ Day 1: VC panels + 25+ breakout rooms led by 100+ VCs & angels. Free livestream\n"
                "→ Day 2: 8-min 1:1 pitch calls with matched investors\n"
                "→ Day 3: family office & LP insights + 10+ rooms led by FOs & LPs\n\n"
                f"Investors get a free 3-day pass. Founders: code {code} for 10% off pitch tickets.\n\n"
                f"Register free: {li}"
            ),
            "note": "Attach the square poster.",
        },
        {
            "title": "Post 2: Speakers",
            "when": "Dec 1–11",
            "headline": "Who's speaking at the free Virtual VC Conf, Jan 27–29",
            "newsletter": (
                "Speakers include Justin Stebbins (Northgate, $5B+ AUM), Yaron Valler (Target Global), "
                "Gené Teare (Crunchbase), Sophie Buonassisi (GTMfund) and Douglas Sloan (Better Society Capital).\n\n"
                "In September, 1,300+ investors joined and founders got 4,270 1:1 matches.\n\n"
                f"Day 1 livestream is free. Founders get 10% off pitch tickets with code {code}.\n\n"
                f"Register free: {link}"
            ),
            "linkedin": (
                "Northgate, Target Global, Crunchbase, GTMfund, Better Society Capital.\n\n"
                "That's part of the speaker lineup at the free Virtual VC Conf, Jan 27–29. "
                "In September, 1,300+ investors joined and founders got 4,270 1:1 matches.\n\n"
                f"We're a media partner this year. Day 1 livestream is free, and founders get 10% off pitch tickets with code {code}.\n\n"
                f"Register free: {li}"
            ),
        },
        {
            "title": "Post 3: New year, new round",
            "when": "Jan 5–14",
            "headline": "Raising this year? Pitch matched investors on Jan 28",
            "newsletter": (
                "At the free Virtual VC Conf, founders get 8-minute 1:1 calls with investors matched "
                "by sector, stage and geography. The day before, 100+ VCs & angels lead the panels and breakout rooms.\n\n"
                f"Day 1 livestream is free. Founders get 10% off pitch tickets with code {code}.\n\n"
                f"Register free: {link}"
            ),
            "linkedin": (
                "Raising this year? Here's a fast way to get in front of investors.\n\n"
                "On Jan 28, founders at the free Virtual VC Conf get 8-minute 1:1 calls with investors matched by sector, stage and geography.\n\n"
                "The day before, 100+ VCs & angels lead the panels and breakout rooms. Free to watch.\n\n"
                f"Founders: code {code} for 10% off pitch tickets.\n"
                f"Register free: {li}"
            ),
        },
        {
            "title": "Post 4: Last call",
            "when": "Jan 19–22",
            "headline": "Next week: free Virtual VC Conf, Jan 27–29",
            "newsletter": (
                "The full program is live: VC panels on Day 1, 1:1 pitch calls on Day 2, family offices & LPs on Day 3. "
                "8 AM PT / 11 AM ET, 100% online.\n\n"
                f"Day 1 livestream is free. 1:1 pitch slots are limited. Founders get 10% off with code {code}.\n\n"
                f"Register free: {link}"
            ),
            "linkedin": (
                "Next week: Virtual VC Conf, and Day 1 is free to watch.\n\n"
                "Jan 27–29, 8 AM PT / 11 AM ET, 100% online:\n"
                "→ Day 1: VC panels + breakout rooms with 100+ VCs & angels\n"
                "→ Day 2: 1:1 pitch calls with matched investors\n"
                "→ Day 3: family offices & LPs\n\n"
                f"1:1 pitch slots are limited. Founders: code {code} for 10% off.\n\n"
                f"Register free: {li}"
            ),
        },
    ]


def markdown(
    *,
    company: str,
    track_url: str,
    promo: str,
    poster_url: str = "",
    poster_square_url: str = "",
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
        first_name=first_name,
        posting_dates=posting_dates,
        **extra,
    )
    p, link = c["partner"], c["link"]
    lines = [
        f"# {page_title(p)}",
        "",
        f"Great to have {p} on board as a media partner!",
        "",
        f"**Your link:** {link}",
        f"**Your code:** {c['code']}",
        "",
        f"**Planned posting dates:** {c['dates']}",
        "",
        "Below is ready-to-use copy for each date, with a newsletter and a LinkedIn version. Use the post that matches your date:",
        "",
        "- by Nov 20 → Post 1",
        "- December → Post 2",
        "- early January → Post 3",
        "- Jan 19–22 → Post 4",
        "- only two posts → Post 1 and Post 4",
        "",
        f'Feel free to adapt the copy to your voice. Just keep the word "free" and your link: they drive most of the clicks.',
        "",
        "Posters: vertical for newsletters, square for LinkedIn.",
        "",
    ]
    if c["poster_url"]:
        lines += [f"![Poster]({c['poster_url']})", ""]
    if c["poster_square_url"]:
        lines += [f"![Poster for LinkedIn]({c['poster_square_url']})", ""]
    lines += [
        "Click a poster → ⋯ → Download",
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
            f"**{item['headline']}**",
            "",
            item["newsletter"],
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
                out.append(f"<p>{rich(para)}</p>")
        if in_list:
            out.append("</ul>")
        return "".join(out)

    posts = []
    for item in copies(c):
        note = f"<p>{esc(item['note'])}</p>" if item.get("note") else ""
        posts.append(
            f"<h2>{esc(item['title'])}</h2>"
            f"<p><em>When:</em> {esc(item['when'])}</p>"
            f"<h3>Newsletter</h3>"
            f"<p><strong>{esc(item['headline'])}</strong></p>"
            f"{md_inline(item['newsletter'])}"
            f"<h3>LinkedIn</h3>"
            f"<pre>{esc(item['linkedin'])}</pre>"
            f"{note}"
        )
    imgs = ""
    if c["poster_url"]:
        imgs += f'<p><img src="{esc(c["poster_url"])}" alt="Poster" /></p>'
    if c["poster_square_url"]:
        imgs += f'<p><img src="{esc(c["poster_square_url"])}" alt="Poster for LinkedIn" /></p>'
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
  <p>Great to have {p} on board as a media partner!</p>
  <p><strong>Your link:</strong> <a href="{link}">{link}</a><br />
  <strong>Your code:</strong> <code>{code}</code></p>
  <p><strong>Planned posting dates:</strong> {esc(c["dates"])}</p>
  <p>Below is ready-to-use copy for each date, with a newsletter and a LinkedIn version. Use the post that matches your date:</p>
  <ul>
    <li>by Nov 20 → Post 1</li>
    <li>December → Post 2</li>
    <li>early January → Post 3</li>
    <li>Jan 19–22 → Post 4</li>
    <li>only two posts → Post 1 and Post 4</li>
  </ul>
  <p>Feel free to adapt the copy to your voice. Just keep the word “free” and your link: they drive most of the clicks.</p>
  <p>Posters: vertical for newsletters, square for LinkedIn.</p>
  {imgs}
  <p>Click a poster → ⋯ → Download</p>
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

    def code(text: str) -> dict:
        node = {
            "type": "text",
            "text": {"content": (text or "")[:2000], "link": None},
        }
        return {
            "object": "block",
            "type": "code",
            "code": {"rich_text": [node], "language": "plain text"},
        }

    def bullet(text: str) -> dict:
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [rt(text)]},
        }

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
        para(rt(f"Great to have {p} on board as a media partner!")),
        para(rt("Your link: ", bold=True), rt(c["link"])),
        para(rt("Your code: ", bold=True), rt(c["code"])),
        para(rt("Planned posting dates: ", bold=True), rt(c["dates"])),
        para(rt("Below is ready-to-use copy for each date, with a newsletter and a LinkedIn version. Use the post that matches your date:")),
        bullet("by Nov 20 → Post 1"),
        bullet("December → Post 2"),
        bullet("early January → Post 3"),
        bullet("Jan 19–22 → Post 4"),
        bullet("only two posts → Post 1 and Post 4"),
        para(rt('Feel free to adapt the copy to your voice. Just keep the word "free" and your link: they drive most of the clicks.')),
        para(rt("Posters: vertical for newsletters, square for LinkedIn.")),
    ]
    if c["poster_url"]:
        kids.append(image(c["poster_url"]))
    if c["poster_square_url"]:
        kids.append(image(c["poster_square_url"]))
    kids.append(para(rt("Click a poster → ⋯ → Download")))
    kids.append(divider())
    for item in copies(c):
        kids.append(h2(item["title"]))
        kids.append(para(rt("When: ", italic=True), rt(item["when"])))
        kids.append(h3("Newsletter"))
        kids.append(para(rt(item["headline"], bold=True)))
        for chunk in item["newsletter"].split("\n\n"):
            kids.append(para(rt(chunk.replace("**", ""))))
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
