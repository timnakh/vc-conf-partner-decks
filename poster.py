"""Media-partner posters: January 2027 portrait + LinkedIn square."""

from __future__ import annotations

import csv
import gc
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
    _trim_mark,
    _wrap_text,
    ascii_filename,
    spill_payload,
)
from names import display_name

ROOT = Path(__file__).resolve().parent
POSTER_DIR = ROOT / "assets" / "posters"
SPEC_PATH = POSTER_DIR / "spec.json"
DEFAULT_URL = "https://vcconf.com/?15"
INK = (11, 31, 63, 255)
GRAD0 = (56, 163, 255)
GRAD1 = (31, 96, 224)
_SPEC: dict | None = None
_BASE: dict[str, Image.Image] = {}
_FONTS: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
_DUMMY = ImageDraw.Draw(Image.new("RGB", (1, 1)))


def _spec() -> dict:
    global _SPEC
    if _SPEC is None:
        _SPEC = json.loads(SPEC_PATH.read_text())
    return _SPEC


def _base(kind: str) -> Image.Image:
    cached = _BASE.get(kind)
    if cached is not None:
        return cached
    path = POSTER_DIR / _spec()[kind]["file"]
    im = Image.open(path).convert("RGB")
    _BASE[kind] = im
    return im


def _font(weight: str, px: int) -> ImageFont.FreeTypeFont:
    key = (weight, int(px))
    cached = _FONTS.get(key)
    if cached is not None:
        return cached
    files = {
        "bold": "Inter-Bold.otf",
        "extrabold": "Inter-Bold.otf",
        "semibold": "Inter-SemiBold.otf",
        "regular": "Inter-Regular.otf",
    }
    font = ImageFont.truetype(str(FONT_FILES / files.get(weight, "Inter-Bold.otf")), px)
    _FONTS[key] = font
    return font


def apply_utm(url: str, company: str) -> str:
    raw = (url or DEFAULT_URL).strip()
    if not raw:
        raw = DEFAULT_URL
    if not raw.lower().startswith(("http://", "https://")):
        raw = "https://" + raw
    parsed = urlparse(raw)
    slug = ascii_filename(display_name(company) or company).rsplit(".", 1)[0]
    slug = slug.replace("-", "_")[:40].lower() or "partner"
    utm = {
        "utm_source": slug,
        "utm_medium": "media_partner",
        "utm_campaign": "vcconf",
    }
    raw_q = parsed.query
    if raw_q and "=" not in raw_q:
        for key in list(utm):
            if key in raw_q:
                del utm[key]
        extra = urlencode(utm)
        query = f"{raw_q}&{extra}" if extra else raw_q
        return urlunparse(parsed._replace(query=query))
    query = dict(parse_qsl(raw_q, keep_blank_values=True))
    if query.get("utm_source"):
        query["utm_source"] = query["utm_source"].lower()
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


def _tracked_width(text: str, font: ImageFont.FreeTypeFont, tracking: float) -> float:
    if not text:
        return 0
    dummy = _DUMMY
    width = 0.0
    last = len(text) - 1
    for i, ch in enumerate(text):
        width += dummy.textlength(ch, font=font)
        if i < last:
            width += tracking
    return width


def _draw_tracked(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, font, fill, tracking: float) -> float:
    x, y = xy
    dummy = _DUMMY
    last = len(text) - 1
    for i, ch in enumerate(text):
        draw.text((x, y), ch, font=font, fill=fill)
        x += dummy.textlength(ch, font=font)
        if i < last:
            x += tracking
    return x


def _draw_gradient_tracked(im: Image.Image, xy: tuple[float, float], text: str, font, tracking: float) -> None:
    dummy = _DUMMY
    x, y = xy
    total = max(_tracked_width(text, font, tracking), 1)
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    walked = 0.0
    last = len(text) - 1
    for i, ch in enumerate(text):
        t = walked / total
        fill = (
            round(GRAD0[0] + (GRAD1[0] - GRAD0[0]) * t),
            round(GRAD0[1] + (GRAD1[1] - GRAD0[1]) * t),
            round(GRAD0[2] + (GRAD1[2] - GRAD0[2]) * t),
            255,
        )
        draw.text((x, y), ch, font=font, fill=fill)
        step = dummy.textlength(ch, font=font)
        x += step
        walked += step
        if i < last:
            x += tracking
            walked += tracking
    im.paste(Image.alpha_composite(im.convert("RGBA"), overlay).convert("RGB"))


def _fit_company(text: str, max_px: int, min_px: int, width: int, top0: float) -> tuple[ImageFont.FreeTypeFont, list[str], float, float]:
    size = max_px
    font = _font("extrabold", size)
    tracking = -0.03 * size
    while _tracked_width(text, font, tracking) > width and size > min_px:
        size -= 1
        font = _font("extrabold", size)
        tracking = -0.03 * size
    top = top0 + 0.864 * (max_px - size)
    if _tracked_width(text, font, tracking) > width:
        lines = _wrap_text(text, font, width)[:2]
        return font, lines, top, 0
    return font, [text], top, tracking


def _png(im: Image.Image) -> bytes:
    out = io.BytesIO()
    im.save(out, format="PNG", compress_level=2)
    return out.getvalue()


def _preview(im: Image.Image, size: tuple[int, int]) -> bytes:
    buf = io.BytesIO()
    im.resize(size, Image.Resampling.BILINEAR).save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _fill_kind(kind: str, name: str, shown_url: str, logo) -> Image.Image:
    spec = _spec()[kind]
    im = _base(kind).copy()
    draw = ImageDraw.Draw(im)

    logo_s = spec["logo"]
    lx, ly, lw = int(logo_s["x"]), int(logo_s["y"]), int(logo_s["w"])
    if logo is not None:
        if hasattr(logo, "seek"):
            logo.seek(0)
        src = Image.open(logo)
        trimmed = _trim_mark(src)
        ratio = trimmed.width / max(trimmed.height, 1)
        frac = 0.88 if ratio >= 2 else 0.74
        inner = max(8, round(lw * frac))
        mark = _place_mark(trimmed, inner, inner // 2)
        im.paste(mark, (lx + (lw - inner) // 2, ly + (lw - inner) // 2), mark)
        draw = ImageDraw.Draw(im)

    name_s = spec["name"]
    font, lines, top, tracking = _fit_company(
        name, int(name_s["max"]), int(name_s["min"]), int(name_s["width"]), float(name_s["y"])
    )
    nx = float(name_s["x"])
    if len(lines) == 1:
        _draw_tracked(draw, (nx, top), lines[0], font, INK, tracking)
    else:
        spacing = round(font.size * 0.08)
        y = top
        for line in lines:
            draw.text((nx, y), line, font=font, fill=INK)
            bbox = _DUMMY.textbbox((0, 0), line, font=font)
            y += (bbox[3] - bbox[1]) + spacing

    foot = spec["footer"]
    cx0, cy0, cx1, cy1 = foot["cover"]
    sample_y = max(0, int(cy0) - 6)
    cover = im.getpixel((im.width // 2, sample_y))
    draw.rectangle([cx0, cy0, cx1, cy1], fill=cover)
    size = int(foot["size"])
    font = _font("extrabold", size)
    tracking = float(foot["tracking"]) * size
    prefix = "Register free: "
    full_w = _tracked_width(prefix + shown_url, font, tracking)
    x = (im.width - full_w) / 2
    y = float(foot["y"])
    end_x = _draw_tracked(draw, (x, y), prefix, font, INK, tracking)
    rgb = im.convert("RGB")
    _draw_gradient_tracked(rgb, (end_x, y), shown_url, font, tracking)
    return rgb


def fill_poster(
    company: str,
    logo: Path | io.BytesIO | None = None,
    url: str = "",
    promo: str = "",
    first_name: str = "",
    posting_dates: str = "",
) -> dict:
    name = display_name(company) or (company or "").strip()
    if not name:
        raise ValueError("укажи название компании")
    entered = (url or DEFAULT_URL).strip() or DEFAULT_URL
    final_url = apply_utm(entered, name)
    shown_url = print_url(entered)
    code = (promo or "").strip().upper()
    portrait = _fill_kind("portrait", name, shown_url, logo)
    if logo is not None and hasattr(logo, "seek"):
        logo.seek(0)
    square = _fill_kind("square", name, shown_url, logo)
    meta = {
        "company": name,
        "url": final_url,
        "promo": code,
        "first_name": (first_name or "").strip(),
        "posting_dates": (posting_dates or "").strip(),
        "kind": "media-partner",
    }
    return {
        "portrait": _png(portrait),
        "square": _png(square),
        "preview": _preview(portrait, (410, 512)),
        "preview_square": _preview(square, (410, 410)),
        "meta": meta,
    }


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
        first_name = (
            lower.get("first_name")
            or lower.get("firstname")
            or lower.get("contact")
            or ""
        )
        posting_dates = (
            lower.get("posting_dates")
            or lower.get("dates")
            or lower.get("planned_dates")
            or ""
        )
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
            filled = fill_poster(
                company,
                logo=photo,
                url=link,
                promo=promo,
                first_name=first_name,
                posting_dates=posting_dates,
            )
        except Exception as e:
            failed.append({"name": company, "url": link, "reason": str(e), "row": original})
            continue
        filename = poster_filename("", company)
        square_name = f"VC Conf poster — {company} (LinkedIn).png"
        if filename in used:
            used[filename] += 1
            n = used[filename]
            filename = f"VC Conf poster — {company} ({n}).png"
            square_name = f"VC Conf poster — {company} (LinkedIn) ({n}).png"
        else:
            used[filename] = 1
        portrait_path = spill_payload(filled["portrait"], ".png")
        square_path = spill_payload(filled["square"], ".png")
        previews.append(
            {
                "name": company,
                "jpeg": filled["preview"],
                "pdf_path": portrait_path,
                "filename": filename,
                "files": [
                    {"filename": filename, "pdf_path": portrait_path, "kind": "portrait"},
                    {"filename": square_name, "pdf_path": square_path, "kind": "square"},
                ],
                "row": original,
                "row_index": i - 1,
                "meta": filled["meta"],
            }
        )
        del filled
        gc.collect()
        if on_progress:
            on_progress(i, total, company)
    if on_progress:
        on_progress(total, total, "готово")
    return failed, previews, fieldnames, rows
