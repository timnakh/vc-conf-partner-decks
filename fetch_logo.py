"""Pull a company logo from a website. Not for LinkedIn / people photos."""

from __future__ import annotations


import io
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from PIL import Image, ImageChops

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126 Safari/537.36"
)
CTX = ssl.create_default_context()
TIMEOUT = 8
_CACHE: dict[str, bytes | None] = {}


class IconParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.icons: list[tuple[int, str]] = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "link" and a.get("href"):
            rel = a.get("rel", "").lower()
            if "icon" in rel:
                m = re.search(r"(\d+)\s*x\s*(\d+)", a.get("sizes", ""), re.I)
                size = int(m.group(1)) if m else (180 if "apple" in rel else 32)
                if a["href"].lower().endswith(".svg") or "svg" in a.get("type", ""):
                    return
                self.icons.append((size, a["href"]))


def _get(url: str, retries: int = 1) -> tuple[bytes, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    last: Exception | None = None
    for _ in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
                return r.read(), (r.headers.get("Content-Type") or ""), r.geturl()
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            last = e
    assert last is not None
    raise last


def _normalize(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise ValueError("сайт не указан")
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def _to_png(data: bytes) -> tuple[io.BytesIO, Image.Image] | None:
    if len(data) < 80:
        return None
    try:
        im = Image.open(io.BytesIO(data))
        if getattr(im, "n_frames", 1) > 1:
            best = None
            for i in range(im.n_frames):
                im.seek(i)
                frame = im.convert("RGBA")
                if best is None or min(frame.size) > min(best.size):
                    best = frame.copy()
            im = best
        else:
            im = im.convert("RGBA")
        if min(im.size) < 16:
            return None
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        buf.seek(0)
        return buf, im
    except Exception:
        return None


def _mark_score(im: Image.Image) -> float:
    rgba = im.convert("RGBA")
    if min(rgba.size) >= 320:
        sample = rgba.resize((32, 32), Image.Resampling.BOX)
        trans = sum(1 for px in sample.getdata() if px[3] < 200)
        if trans <= 4:
            return 0.0
    r, g, b, a = rgba.split()
    opaque = a.point(lambda p: 255 if p > 16 else 0)
    not_white = ImageChops.lighter(
        ImageChops.lighter(
            r.point(lambda p: 255 if p < 248 else 0),
            g.point(lambda p: 255 if p < 248 else 0),
        ),
        b.point(lambda p: 255 if p < 248 else 0),
    )
    mask = ImageChops.multiply(opaque, not_white)
    bbox = mask.getbbox() or opaque.getbbox()
    if not bbox:
        return 0.0
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    fill = (tw * th) / max(1, rgba.width * rgba.height)
    ratio = tw / max(th, 1)
    square = 1.0 if 0.75 <= ratio <= 1.35 else 0.5
    return min(tw, th) * (0.25 + 0.75 * fill) * square


def _pick_icon(candidates: list[tuple[int, str]]) -> io.BytesIO | None:
    best: tuple[float, str, io.BytesIO] | None = None
    seen: set[str] = set()
    native: list[tuple[int, str]] = []
    google: list[tuple[int, str]] = []
    for item in candidates:
        href = item[1]
        if "google.com/s2/favicons" in href:
            google.append(item)
        else:
            native.append(item)
    for group in (native, google):
        if best is not None and group is google:
            break
        for _size, href in group:
            if href in seen:
                continue
            seen.add(href)
            try:
                data, ctype, _ = _get(href)
            except (urllib.error.URLError, TimeoutError, ValueError, OSError):
                continue
            if "html" in (ctype or "").lower():
                continue
            converted = _to_png(data)
            if converted is None:
                continue
            png, im = converted
            score = _mark_score(im)
            if score <= 0:
                continue
            key = (score, href, png)
            if best is None or score > best[0] or (score == best[0] and href < best[1]):
                best = key
    if best is None:
        return None
    best[2].seek(0)
    return best[2]


POSTER_LOGO_PX = 160
MIN_RASTER_PX = POSTER_LOGO_PX * 2
SVG_RASTER_PX = 1024
MAX_LOGO_BYTES = 8 * 1024 * 1024


def is_svg(data: bytes, name: str = "", ctype: str = "") -> bool:
    if "svg" in (ctype or "").lower() or (name or "").lower().endswith(".svg"):
        return True
    head = data.lstrip()[:400].lower()
    return head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in head)


def rasterize_svg(data: bytes, px: int = SVG_RASTER_PX) -> Image.Image:
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPDF
        import pypdfium2 as pdfium
    except ImportError as e:
        raise ValueError("сервер не умеет SVG — загрузи PNG") from e
    drawing = svg2rlg(io.BytesIO(data))
    if drawing is None:
        raise ValueError("не разобрал SVG")
    w = float(getattr(drawing, "width", 0) or 1)
    h = float(getattr(drawing, "height", 0) or 1)
    scale = px / max(w, h)
    drawing.width = w * scale
    drawing.height = h * scale
    drawing.scale(scale, scale)
    pdf_bytes = renderPDF.drawToString(drawing)
    doc = pdfium.PdfDocument(pdf_bytes)
    try:
        page = doc[0]
        im = page.render(scale=2).to_pil().convert("RGBA")
    finally:
        doc.close()
    if min(im.size) < 16:
        raise ValueError("SVG получился пустым")
    return im


def decode_logo(data: bytes, name: str = "", ctype: str = "") -> dict:
    if not data:
        raise ValueError("пустой файл логотипа")
    if len(data) > MAX_LOGO_BYTES:
        raise ValueError("логотип больше 8 МБ")
    svg = is_svg(data, name, ctype)
    if svg:
        im = rasterize_svg(data)
    else:
        converted = _to_png(data)
        if converted is None:
            raise ValueError("не открыл логотип — нужен SVG, PNG или JPG")
        _buf, im = converted
        im = im.convert("RGBA")
    w, h = im.size
    warn = ""
    if not svg and min(w, h) < MIN_RASTER_PX:
        warn = (
            f"лого {w}×{h} px — на постере будет мыло. "
            f"Нужно от {MIN_RASTER_PX} px по короткой стороне "
            f"(2× круга {POSTER_LOGO_PX} px)."
        )
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    buf.seek(0)
    return {
        "png": buf,
        "width": w,
        "height": h,
        "svg": svg,
        "warn": warn,
    }


def fetch_image(url: str) -> tuple[bytes, str, str]:
    site = _normalize(url)
    data, ctype, final = _get(site, retries=1)
    if len(data) > MAX_LOGO_BYTES:
        raise ValueError("логотип по URL больше 8 МБ")
    if "html" in (ctype or "").lower() or data[:20].lstrip().lower().startswith((b"<!doctype", b"<html")):
        raise ValueError("URL отдаёт HTML, а не картинку")
    return data, ctype, final


def load_from_url(url: str) -> dict:
    data, ctype, final = fetch_image(url)
    return decode_logo(data, final, ctype)


def fetch_logo(url: str) -> io.BytesIO:
    site = _normalize(url)
    host = urllib.parse.urlparse(site).netloc.lower()
    if "linkedin.com" in host or "lnkd.in" in host:
        raise ValueError("это LinkedIn — загрузи фото файлом, с сайта человека логотип не качаем")
    if host in _CACHE:
        cached = _CACHE[host]
        if cached is None:
            raise ValueError(f"не удалось скачать логотип с {site}")
        return io.BytesIO(cached)

    candidates: list[tuple[int, str]] = []
    root = site
    try:
        html, ctype, final = _get(site)
        root = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(final))
        if "html" in ctype or html[:20].lstrip().lower().startswith((b"<!doctype", b"<html")):
            parser = IconParser()
            parser.feed(html.decode("utf-8", "ignore"))
            for size, href in parser.icons:
                candidates.append((size, urllib.parse.urljoin(final, href)))
    except Exception:
        root = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(site))

    host_only = urllib.parse.urlparse(root).netloc
    candidates.extend(
        [
            (180, root.rstrip("/") + "/apple-touch-icon.png"),
            (180, root.rstrip("/") + "/apple-touch-icon-precomposed.png"),
            (32, root.rstrip("/") + "/favicon.ico"),
            (1, f"https://www.google.com/s2/favicons?domain={host_only}&sz=128"),
        ]
    )
    picked = _pick_icon(candidates)
    if picked is None:
        _CACHE[host] = None
        raise ValueError(f"не удалось скачать логотип с {site}")
    raw = picked.getvalue()
    _CACHE[host] = raw
    return io.BytesIO(raw)
