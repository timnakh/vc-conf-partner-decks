"""Partner kit page sent to the media partner."""

from __future__ import annotations

import html as html_lib
from urllib.parse import quote

DEFAULT_DATES = (
    "3–4 posts (newsletter + LinkedIn): by Nov 20, early Dec, early Jan, "
    "Jan 19–22. Posting Mon–Fri 9–11 am EST"
)
BANNER_HINT = "Add the banner here and link it to your link."
POST1_LATEST = "by Nov 20"


def page_title(company: str) -> str:
    return f"{company} × Virtual VC Conf 2027"


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
    **_extra,
) -> dict:
    partner = (company or "").strip() or "partner"
    code = (promo or "").strip().upper() or "{{code}}"
    link = (track_url or "").strip() or "{{reg_url}}"
    short = _short_link(link)
    dates = (posting_dates or "").strip() or DEFAULT_DATES
    post1_list, post1_when = _post1_labels(first_post_date)
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
        "poster_url": poster_url or "",
        "poster_square_url": poster_square_url or "",
        "poster_banner_url": poster_banner_url or "",
        "first_name": (first_name or "").strip(),
    }


def _post1_labels(first_post_date: str) -> tuple[str, str]:
    date = (first_post_date or "").strip()
    if date:
        return (
            f"first post (ideally {date})",
            f"ideally {date}, at the latest by Nov 20",
        )
    return POST1_LATEST, POST1_LATEST


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
    return [
        {
            "title": "Post 1: Announcement",
            "when": c["post1_when"],
            "kicker": "ON JAN 27–29",
            "headline": "Virtual VC Conf 2027 is coming up!",
            "newsletter": (
                f"{p} is partnering with Virtual VC Conf: three days online with 1,000+ VCs, angels, family offices and LPs.\n\n"
                "- **Attend for free** and watch Day 1 panels with top VCs.\n"
                "- **Grab a 1:1 Pitch Ticket** if you want to pitch matched investors on Day 2.\n"
                "- **Investors join free** for all three days.\n\n"
                "Day 1: VC panels + 25+ breakout rooms. Day 2: 1:1 pitch calls. Day 3: family office & LP insights.\n\n"
                "In September, 1,300+ investors joined, looking to invest in AI, fintech, healthcare and beyond. You'll be matched with them by sector, stage and geography.\n\n"
                f"With code **{code}**, you get 10% off pitch tickets.\n\n"
                f"Register free at {link}"
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
            "banner_hint": BANNER_HINT,
        },
        {
            "title": "Post 2: Speakers",
            "when": "Dec 1–11",
            "kicker": "ON JAN 27–29",
            "headline": "Meet the speakers at Virtual VC Conf",
            "newsletter": (
                "Speakers include Justin Stebbins (Northgate, $5B+ AUM), Yaron Valler (Target Global), "
                "Gené Teare (Crunchbase), Sophie Buonassisi (GTMfund) and Douglas Sloan (Better Society Capital).\n\n"
                "- **Attend for free** and watch their panels on Day 1.\n"
                "- **Grab a 1:1 Pitch Ticket** to pitch investors matched to your sector, stage and geography.\n\n"
                "In September, founders got 4,270 1:1 matches with 1,300+ investors.\n\n"
                f"With code **{code}**, you get 10% off pitch tickets.\n\n"
                f"Register free at {link}"
            ),
            "linkedin": (
                "Northgate, Target Global, Crunchbase, GTMfund, Better Society Capital.\n\n"
                "That's part of the speaker lineup at the free Virtual VC Conf, Jan 27–29. "
                "In September, 1,300+ investors joined and founders got 4,270 1:1 matches.\n\n"
                f"We're a media partner this year. Day 1 livestream is free, and founders get 10% off pitch tickets with code {code}.\n\n"
                f"Register free: {li}"
            ),
            "banner_hint": BANNER_HINT,
        },
        {
            "title": "Post 3: New year, new round",
            "when": "Jan 5–14",
            "kicker": "ON JAN 28",
            "headline": "Raising this year? Pitch matched investors in 8-minute 1:1s",
            "newsletter": (
                "At Virtual VC Conf, founders get 1:1 calls with investors matched by sector, stage and geography.\n\n"
                "- **Attend for free** and watch Day 1 panels with 100+ VCs & angels.\n"
                "- **Grab a 1:1 Pitch Ticket** to get on investors' calendars on Day 2.\n\n"
                f"With code **{code}**, you get 10% off pitch tickets.\n\n"
                f"Register free at {link}"
            ),
            "linkedin": (
                "Raising this year? Here's a fast way to get in front of investors.\n\n"
                "On Jan 28, founders at the free Virtual VC Conf get 8-minute 1:1 calls with investors matched by sector, stage and geography.\n\n"
                "The day before, 100+ VCs & angels lead the panels and breakout rooms. Free to watch.\n\n"
                f"Founders: code {code} for 10% off pitch tickets.\n"
                f"Register free: {li}"
            ),
            "banner_hint": BANNER_HINT,
        },
        {
            "title": "Post 4: Last call",
            "when": "Jan 19–22",
            "kicker": "NEXT WEEK, JAN 27–29",
            "headline": "Last call for Virtual VC Conf",
            "newsletter": (
                "The full program is live. 8 AM PT / 11 AM ET, 100% online.\n\n"
                "- **Attend for free** and watch Day 1 panels with top VCs.\n"
                "- **Grab a 1:1 Pitch Ticket** before slots run out. Pitch calls are on Day 2.\n"
                "- **Investors join free** for all three days.\n\n"
                f"With code **{code}**, you get 10% off pitch tickets.\n\n"
                f"Register free at {link}"
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
        f"Great to have {p} on board as a media partner!",
        "",
        f"**Your link:** {link}",
        "",
        f"**Your code:** {c['code']}",
        "",
        f"**Planned posting dates:** {c['dates']}",
        "",
        "Below is ready-to-use copy for each date, with a newsletter and a LinkedIn version. Use the post that matches your date:",
        "",
        f"- {c['post1_list']} → Post 1",
        "- December → Post 2",
        "- early January → Post 3",
        "- Jan 19–22 → Post 4",
        "- only two posts → Post 1 and Post 4",
        "",
        f'Feel free to adapt the copy to your voice. Just keep the word "free" and your link: they drive most of the clicks.',
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
                if para.startswith("Register free at "):
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
  <p>Great to have {p} on board as a media partner!</p>
  <p><strong>Your link:</strong> <a href="{link}">{link}</a></p>
  <p><strong>Your code:</strong> <code>{code}</code></p>
  <p><strong>Planned posting dates:</strong> {esc(c["dates"])}</p>
  <p>Below is ready-to-use copy for each date, with a newsletter and a LinkedIn version. Use the post that matches your date:</p>
  <ul>
    <li>{esc(c["post1_list"])} → Post 1</li>
    <li>December → Post 2</li>
    <li>early January → Post 3</li>
    <li>Jan 19–22 → Post 4</li>
    <li>only two posts → Post 1 and Post 4</li>
  </ul>
  <p>Feel free to adapt the copy to your voice. Just keep the word “free” and your link: they drive most of the clicks.</p>
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
        marker = "Register free: "
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
        para(rt(f"Great to have {p} on board as a media partner!")),
        para(rt("Your link: ", bold=True), rt(c["link"])),
        para(rt("Your code: ", bold=True), rt(c["code"])),
        para(rt("Planned posting dates: ", bold=True), rt(c["dates"])),
        para(rt("Below is ready-to-use copy for each date, with a newsletter and a LinkedIn version. Use the post that matches your date:")),
        bullet(f"{c['post1_list']} → Post 1"),
        bullet("December → Post 2"),
        bullet("early January → Post 3"),
        bullet("Jan 19–22 → Post 4"),
        bullet("only two posts → Post 1 and Post 4"),
        para(rt('Feel free to adapt the copy to your voice. Just keep the word "free" and your link: they drive most of the clicks.')),
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
            elif chunk.startswith("Register free at "):
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
