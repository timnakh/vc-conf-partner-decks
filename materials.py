"""Announcement pack for a media partner — same shape as last conf’s Notion page."""

from __future__ import annotations

import html as html_lib
from urllib.parse import quote

HEADLINE = "Get your CEO 20 investor pitches in one day"
LEAD = "The Virtual 1:1 VC Pitch Conf on September 17."
BULLETS = [
    "Attend for free and watch keynotes and panels with speakers from a16z, 500 Global, Plug & Play, Antler, Entrepreneurs First, Crunchbase and other VCs.",
    "Get a 1:1 Startup Pitch Ticket so your founder can pitch 20 VCs one-on-one, 7 minutes each, all online.",
    "If you invest yourself (2+ investments in the last 12 months, $25K+ checks), you can also apply for free as an investor and get 1,200+ decks, 20 founder pitches and 2 hours of investor-only networking.",
]
CLOSING = (
    "380+ VCs, angels, and family offices are looking to invest in AI, fintech, "
    "healthcare, and beyond. Matching is based on your sector, stage, and geography. "
    'Check your likely matches with the free "My 20 VC Matches" tool on the site, '
    "no registration needed."
)


def page_title(company: str) -> str:
    return f"For {company} - VC Pitch Conf announcements"


def intro(company: str) -> str:
    return f"Great to have {company} joining as a media partner!"


def promo_line(code: str) -> str:
    code = (code or "").strip()
    if not code:
        return "If you decide to pitch 20 VCs, tickets are on the site."
    return f"If you decide to pitch 20 VCs, use code {code} for 10% off."


def markdown(*, company: str, track_url: str, promo: str, poster_url: str = "") -> str:
    title = page_title(company)
    lines = [
        f"# {title}",
        "",
        intro(company),
        "",
        "## Template:",
        "",
        f"### {HEADLINE}",
        "",
        LEAD,
        "",
    ]
    for b in BULLETS:
        lines.append(f"- {b}")
    lines += [
        "",
        CLOSING,
        "",
    ]
    if poster_url:
        lines += [f"![Poster]({poster_url})", ""]
    lines += [
        f"[Register for free]({track_url})",
        "",
        promo_line(promo),
        "",
    ]
    return "\n".join(lines)


def html_page(*, company: str, track_url: str, promo: str, poster_url: str) -> str:
    esc = html_lib.escape
    bullets = "".join(f"<li>{esc(b)}</li>" for b in BULLETS)
    poster = (
        f'<p><img src="{esc(poster_url)}" alt="Poster" style="max-width:100%;border-radius:12px" /></p>'
        if poster_url
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(page_title(company))}</title>
  <style>
    body {{ margin:0; font: 16px/1.45 Inter, ui-sans-serif, system-ui, sans-serif;
      background:#111; color:#f4f4f5; }}
    main {{ max-width: 720px; margin: 0 auto; padding: 48px 20px 80px; }}
    h1 {{ font-size: 28px; letter-spacing:-.03em; margin: 0 0 12px; }}
    h2 {{ font-size: 20px; margin: 28px 0 12px; }}
    h3 {{ font-size: 18px; margin: 0 0 8px; }}
    .muted {{ color:#a1a1aa; }}
    a.btn {{ display:inline-block; margin: 16px 0; padding: 10px 16px; background:#fff;
      color:#111; border-radius:10px; font-weight:700; text-decoration:none; }}
    ul {{ padding-left: 1.2em; }}
  </style>
</head>
<body>
<main>
  <h1>{esc(page_title(company))}</h1>
  <p class="muted">{esc(intro(company))}</p>
  <h2>Template:</h2>
  <h3>{esc(HEADLINE)}</h3>
  <p>{esc(LEAD)}</p>
  <ul>{bullets}</ul>
  <p>{esc(CLOSING)}</p>
  {poster}
  <p><a class="btn" href="{esc(track_url)}">Register for free</a></p>
  <p>{esc(promo_line(promo))}</p>
</main>
</body>
</html>
"""


def md_filename(company: str) -> str:
    slug = quote(company.strip() or "partner", safe="")
    return f"For-{slug}-VC-Pitch-Conf-announcements.md"
