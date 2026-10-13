"""Media-partner poster fill. MVP template from the 1:1 Pitch Conf example."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from PIL import Image, ImageDraw, ImageFont

from fill import (
    FONT_FILES,
    SAFE_FILE,
    _fit_name,
    _logo_by_company,
    _photo_from_row,
    _place_mark,
    ascii_filename,
    unpack_logo_zip,
)
from names import display_name

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "assets" / "posters" / "media-partner.png"
SCALE = 2
# Coordinates on the 819×1024 source.
LOGO = (50, 154, 168)  # x, y, diameter
NAME = (248, 162, 540, 96)
CTA = (40, 878, 740, 100, 24)  # x, y, w, h, radius
NAME_COLOR = (40, 22, 58)
CTA_FILL = (29, 247, 210)
CTA_TEXT = (40, 22, 58)
DEFAULT_URL = "https://vcconf.com/?15"


def _font(weight: str, px: int) -> ImageFont.FreeTypeFont:
    file = "Inter-Bold.otf" if weight == "bold" else "Inter-Regular.otf"
    return ImageFont.truetype(str(FONT_FILES / file), px)


def apply_utm(url: str, company: str) -> str:
    raw = (url or DEFAULT_URL).strip()
    if not raw:
        raw = DEFAULT_URL
    if not raw.lower().startswith(("http://", "https://")):
        raw = "https://" + raw
    parsed = urlparse(raw)
    slug = ascii_filename(display_name(company) or company).rsplit(".", 1)[0]
    slug = slug.replace("-", "_")[:40] or "partner"
    utm = {
        "utm_source": slug,
        "utm_medium": "media_partner",
        "utm_campaign": "vcconf",
    }
    raw_q = parsed.query
    if raw_q and "=" not in raw_q:
        for key, val in list(utm.items()):
            if key in raw_q:
                del utm[key]
        extra = urlencode(utm)
        query = f"{raw_q}&{extra}" if extra else raw_q
        return urlunparse(parsed._replace(query=query))
    query = dict(parse_qsl(raw_q, keep_blank_values=True))
    for key, val in utm.items():
        query.setdefault(key, val)
    return urlunparse(parsed._replace(query=urlencode(query)))


def print_url(url: str) -> str:
    text = (url or "").strip()
    for prefix in ("https://", "http://"):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :]
            break
    if text.startswith("www."):
        text = text[4:]
    return text or "vcconf.com"


def poster_filename(pattern: str | None, name: str) -> str:
    raw = (pattern or "").strip() or "VC Conf poster — {name}.png"
    filled = (
        raw.replace("{name}", name.strip() or "partner")
        .replace("{template}", "медиапартнёр")
        .replace("{role}", "медиапартнёр")
    )
    cleaned = SAFE_FILE.sub("", filled)
    cleaned = " ".join(cleaned.split()).strip(" .")
    if not cleaned.lower().endswith(".png"):
        cleaned = (cleaned or "poster") + ".png"
    return cleaned or "poster.png"


def _wipe_rect(im: Image.Image, box: tuple[int, int, int, int], sample: tuple[int, int]) -> None:
    x, y, w, h = box
    sx = min(max(sample[0], 0), im.width - 1)
    sy = min(max(sample[1], 0), im.height - 1)
    color = im.getpixel((sx, sy))[:3] + (255,)
    draw = ImageDraw.Draw(im)
    draw.rectangle([x, y, x + w, y + h], fill=color)


def fill_poster(
    company: str,
    logo: Path | io.BytesIO | None = None,
    url: str = "",
    promo: str = "",
) -> tuple[bytes, bytes, dict]:
    name = display_name(company) or (company or "").strip()
    if not name:
        raise ValueError("укажи название компании")
    entered = (url or DEFAULT_URL).strip() or DEFAULT_URL
    final_url = apply_utm(entered, name)
    shown_url = print_url(entered)
    code = (promo or "").strip().upper()

    base = Image.open(TEMPLATE).convert("RGBA")
    s = SCALE
    im = base.resize((base.width * s, base.height * s), Image.Resampling.LANCZOS)

    lx, ly, d = [v * s for v in LOGO]
    nx, ny, nw, nh = [v * s for v in NAME]
    cx, cy, cw, ch, cr = [v * s for v in CTA]

    # Cover baked-in Founders Bay + "Company's name".
    draw = ImageDraw.Draw(im)
    bg = im.getpixel((20 * s, 140 * s))
    pad = 3 * s
    draw.ellipse([lx - pad, ly - pad, lx + d + pad, ly + d + pad], fill=bg)
    _wipe_rect(im, (nx - 4 * s, ny - 4 * s, nw + 8 * s, nh + 8 * s), (240 * s, 140 * s))

    draw.ellipse([lx, ly, lx + d, ly + d], fill=(255, 255, 255, 255))
    if logo is not None:
        if hasattr(logo, "seek"):
            logo.seek(0)
        mark = _place_mark(Image.open(logo), d, d // 2)
        im.paste(mark, (lx, ly), mark)

    draw = ImageDraw.Draw(im)
    font, lines = _fit_name(name, nw, nh, s, pts=(36, 32, 28, 24, 20))
    spacing = round(-2 * s)
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox = dummy.multiline_textbbox((0, 0), "\n".join(lines), font=font, spacing=spacing)
    text_h = bbox[3] - bbox[1]
    draw.multiline_text(
        (nx, ny + max(0, (nh - text_h) // 2)),
        "\n".join(lines),
        font=font,
        fill=NAME_COLOR + (255,),
        spacing=spacing,
    )

    draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=cr, fill=CTA_FILL + (255,))
    line1 = f"Free registration: {shown_url}"
    line2 = f"1:1 pitch tickets – 10% off with code {code}" if code else "1:1 pitch tickets on the site"
    max_w = cw - 24 * s
    size1, size2 = 18 * s, 14 * s
    f1 = _font("bold", size1)
    f2 = _font("regular", size2)
    while dummy.textlength(line1, font=f1) > max_w and size1 > 10 * s:
        size1 -= s
        f1 = _font("bold", size1)
    while dummy.textlength(line2, font=f2) > max_w and size2 > 9 * s:
        size2 -= s
        f2 = _font("regular", size2)
    y1 = cy + 18 * s
    y2 = cy + 48 * s
    w1 = dummy.textlength(line1, font=f1)
    w2 = dummy.textlength(line2, font=f2)
    draw.text(((cx + (cw - w1) / 2), y1), line1, font=f1, fill=CTA_TEXT + (255,))
    draw.text(((cx + (cw - w2) / 2), y2), line2, font=f2, fill=CTA_TEXT + (255,))

    rgb = im.convert("RGB")
    out = io.BytesIO()
    rgb.save(out, format="PNG", optimize=True)
    preview = io.BytesIO()
    rgb.resize((410, 512), Image.Resampling.LANCZOS).save(preview, format="JPEG", quality=88)
    meta = {
        "company": name,
        "url": final_url,
        "promo": code,
        "kind": "media-partner",
    }
    return out.getvalue(), preview.getvalue(), meta


def fill_posters_from_csv(
    csv_file,
    logos_map: dict[str, bytes] | None = None,
    on_progress=None,
) -> tuple[list[dict], list[dict], list[str], list[dict]]:
    from fetch_logo import fetch_logo

    logos_map = logos_map or {}
    if hasattr(csv_file, "read"):
        reader = csv.DictReader(csv_file)
        fieldnames = [h for h in (reader.fieldnames or []) if h is not None]
        rows = list(reader)
    else:
        with Path(csv_file).open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = [h for h in (reader.fieldnames or []) if h is not None]
            rows = list(reader)
    if not rows:
        raise ValueError("CSV пустой")

    failed: list[dict] = []
    previews: list[dict] = []
    used: dict[str, int] = {}
    total = len(rows)
    for i, row in enumerate(rows, start=1):
        original = {(k or ""): (v or "").strip() for k, v in row.items() if k is not None}
        lower = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        company = display_name(
            lower.get("company") or lower.get("name") or lower.get("company_name") or ""
        )
        label = company or f"строка {i}"
        if on_progress:
            on_progress(i - 1, total, label)
        if not company:
            failed.append({"name": label, "url": "", "reason": "нет компании", "row": original})
            continue
        site = lower.get("website") or lower.get("site") or ""
        link = lower.get("link") or lower.get("url") or lower.get("utm") or ""
        promo = lower.get("promo") or lower.get("code") or lower.get("promocode") or ""
        photo_val = lower.get("logo") or lower.get("photo") or lower.get("image") or ""
        photo = _photo_from_row(photo_val, None, logos_map) if photo_val else None
        if photo is None:
            photo = _logo_by_company(company, logos_map)
        if photo is None and site:
            try:
                photo = fetch_logo(site)
            except Exception:
                photo = None
        try:
            data, preview, meta = fill_poster(company, logo=photo, url=link, promo=promo)
        except Exception as e:
            failed.append({"name": company, "url": link, "reason": str(e), "row": original})
            continue
        filename = poster_filename("", company)
        if filename in used:
            used[filename] += 1
            filename = f"VC Conf poster — {company} ({used[filename]}).png"
        else:
            used[filename] = 1
        previews.append(
            {
                "name": company,
                "jpeg": preview,
                "pdf": data,
                "filename": filename,
                "row": original,
                "row_index": i - 1,
                "meta": meta,
            }
        )
        if on_progress:
            on_progress(i, total, company)
    if on_progress:
        on_progress(total, total, "готово")
    return failed, previews, fieldnames, rows
