"""Media-partner poster fill. Slots from Figma PSD; pixels from flattened PNG."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from PIL import Image, ImageDraw, ImageFont

from fill import (
    FONT_FILES,
    SAFE_FILE,
    _logo_by_company,
    _photo_from_row,
    _place_mark,
    _wrap_text,
    ascii_filename,
)
from names import display_name

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "assets" / "posters" / "media-partner.png"
SPEC_PATH = ROOT / "assets" / "posters" / "media-partner.json"
DEFAULT_URL = "https://vcconf.com/?15"


def _spec() -> dict:
    return json.loads(SPEC_PATH.read_text())


def _s(v: float, scale: float) -> int:
    return round(v * scale)


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


def _sample(im: Image.Image, x: int, y: int) -> tuple[int, int, int, int]:
    x = min(max(x, 0), im.width - 1)
    y = min(max(y, 0), im.height - 1)
    px = im.getpixel((x, y))
    return (px[0], px[1], px[2], 255)


def _wipe_rows(im: Image.Image, box: tuple[int, int, int, int], sample_x: int) -> None:
    x, y, w, h = box
    draw = ImageDraw.Draw(im)
    for yy in range(y, y + h):
        draw.line([(x, yy), (x + w, yy)], fill=_sample(im, sample_x, yy))


def _fit_px(text: str, max_w: int, max_h: int, size: int) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for s in range(size, 20, -2):
        font = _font("bold", s)
        lines = _wrap_text(text, font, max_w)
        if len(lines) > 2:
            continue
        spacing = round(s * -0.04)
        bbox = dummy.multiline_textbbox((0, 0), "\n".join(lines), font=font, spacing=spacing)
        if bbox[2] - bbox[0] <= max_w and bbox[3] - bbox[1] <= max_h:
            return font, lines, spacing
    font = _font("bold", 22)
    return font, _wrap_text(text, font, max_w)[:2], 0


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
    spec = _spec()
    s = float(spec.get("scale") or 0.5)
    canvas_w, canvas_h = spec["canvas"]
    out_w, out_h = _s(canvas_w, s), _s(canvas_h, s)

    base = Image.open(TEMPLATE).convert("RGBA")
    im = base.resize((out_w, out_h), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(im)

    logo_s = spec["logo"]
    lx, ly = _s(logo_s["x"], s), _s(logo_s["y"], s)
    lw, lh = _s(logo_s["w"], s), _s(logo_s["h"], s)
    pad = max(4, _s(12, s))
    white = _sample(im, _s(80, s), _s(400, s))
    draw.ellipse([lx - pad, ly - pad, lx + lw + pad, ly + lh + pad], fill=white)
    draw.ellipse([lx, ly, lx + lw, ly + lh], fill=(255, 255, 255, 255))
    if logo is not None:
        if hasattr(logo, "seek"):
            logo.seek(0)
        d = min(lw, lh)
        mark = _place_mark(Image.open(logo), d, d // 2)
        im.paste(mark, (lx + (lw - d) // 2, ly + (lh - d) // 2), mark)
        draw = ImageDraw.Draw(im)

    name_s = spec["name"]
    nx, ny = _s(name_s["x"], s), _s(name_s["y"], s)
    nw, nh = _s(name_s["w"], s), _s(name_s["h"], s)
    wipe_h = min(nh, _s(200, s))
    _wipe_rows(
        im,
        (nx - pad, ny - pad, _s(1360, s) + 2 * pad, wipe_h + 2 * pad),
        max(0, nx - _s(40, s)),
    )
    font, lines, spacing = _fit_px(name, nw, nh, _s(name_s["size"], s))
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    draw.multiline_text(
        (nx, ny),
        "\n".join(lines),
        font=font,
        fill=tuple(name_s["color"]) + (255,),
        spacing=spacing,
    )

    cta = spec["cta"]
    cx, cy = _s(cta["x"], s), _s(cta["y"], s)
    ctw, cth = _s(cta["w"], s), _s(cta["h"], s)
    teal = _sample(im, cx + ctw // 2, cy + cth // 2)
    inset = max(8, _s(40, s))
    draw.rectangle([cx + inset, cy + inset, cx + ctw - inset, cy + cth - inset], fill=teal)

    line1 = f"Free registration: {shown_url}"
    line2 = (
        f"1:1 pitch tickets – 10% off with code {code}"
        if code
        else "1:1 pitch tickets on the site"
    )
    max_w = ctw - 2 * inset
    size1, size2 = _s(cta["line1_size"], s), _s(cta["line2_size"], s)
    f1 = _font("bold", size1)
    f2 = _font("regular", size2)
    while dummy.textlength(line1, font=f1) > max_w and size1 > 18:
        size1 -= 2
        f1 = _font("bold", size1)
    while dummy.textlength(line2, font=f2) > max_w and size2 > 16:
        size2 -= 2
        f2 = _font("regular", size2)
    w1 = dummy.textlength(line1, font=f1)
    w2 = dummy.textlength(line2, font=f2)
    color = tuple(cta["color"]) + (255,)
    draw.text((cx + (ctw - w1) / 2, _s(cta["line1_y"], s)), line1, font=f1, fill=color)
    draw.text((cx + (ctw - w2) / 2, _s(cta["line2_y"], s)), line2, font=f2, fill=color)

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
