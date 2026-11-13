from __future__ import annotations

from pathlib import Path

import uharfbuzz as hb
from PIL import Image, ImageDraw
from freetype import FT_LOAD_RENDER, Face as FreetypeFace

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_BUNDLED_FONT = _PROJECT_ROOT / "assets" / "fonts" / "NotoSansDevanagari-Bold.ttf"


def devanagari_font_path() -> str:
    return _font_path()


def _font_path() -> str:
    candidates = [
        str(_BUNDLED_FONT),
        "/System/Library/Fonts/Supplemental/NotoSansDevanagari-Bold.ttf",
        "/System/Library/Fonts/KohinoorDevanagari-Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    raise FileNotFoundError("No Devanagari bold font found")


def _load_hb_face(font_path: str) -> hb.Face:
    with open(font_path, "rb") as f:
        return hb.Face(f.read())


def _shape_buffer(text: str, font_path: str, size_px: int) -> tuple[hb.Buffer, hb.Font]:
    face = _load_hb_face(font_path)
    font = hb.Font(face)
    # 26.6 fixed-point: match FreeType pixel metrics at size_px
    font.scale = (size_px * 64, size_px * 64)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf)
    return buf, font


def shaped_text_width(text: str, font_path: str, size_px: int) -> float:
    buf, _font = _shape_buffer(text, font_path, size_px)
    return sum(pos.x_advance for pos in buf.glyph_positions) / 64.0


def draw_devanagari(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    size_px: int,
    fill: tuple[int, int, int],
    *,
    font_path: str | None = None,
) -> None:
    """Render Hindi with HarfBuzz shaping (fixes शिव vs शवि matra bugs)."""
    font_path = font_path or _font_path()
    x_start, y_baseline = xy

    buf, _hb_font = _shape_buffer(text, font_path, size_px)

    ft = FreetypeFace(font_path)
    ft.set_pixel_sizes(0, size_px)

    pen_x = x_start
    pen_y = y_baseline

    def render_glyph(gid: int, x_off: float, y_off: float) -> None:
        nonlocal pen_x
        ft.load_glyph(gid, FT_LOAD_RENDER)
        bitmap = ft.glyph.bitmap
        if not bitmap.width or not bitmap.rows:
            return
        img = Image.frombytes("L", (bitmap.width, bitmap.rows), bytes(bitmap.buffer))
        color_img = Image.new("RGBA", (bitmap.width, bitmap.rows), fill + (0,))
        color_img.putalpha(img)
        draw._image.paste(
            color_img,
            (int(pen_x + x_off + ft.glyph.bitmap_left), int(pen_y - y_off - ft.glyph.bitmap_top)),
            color_img,
        )

    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        x_off = pos.x_offset / 64.0
        y_off = pos.y_offset / 64.0
        x_advance = pos.x_advance / 64.0
        gid = info.codepoint
        render_glyph(gid, x_off, y_off)
        pen_x += x_advance


def draw_devanagari_outlined(
    img: Image.Image,
    xy: tuple[int, int],
    text: str,
    size_px: int,
    fill: tuple[int, int, int],
    *,
    font_path: str | None = None,
) -> None:
    """3D shadow + fill using shaped glyphs."""
    font_path = font_path or _font_path()
    for dx, dy, color in (
        (-3, 3, (0, 0, 0)),
        (3, 3, (0, 0, 0)),
        (-2, 0, (30, 20, 0)),
        (2, 0, (30, 20, 0)),
    ):
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        draw_devanagari(d, (xy[0] + dx, xy[1] + dy), text, size_px, color, font_path=font_path)
        img.alpha_composite(layer)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    draw_devanagari(d, xy, text, size_px, fill, font_path=font_path)
    img.alpha_composite(layer)
