"""Wycinanie fragmentów stron z podpisami — do wizualnej weryfikacji przez człowieka."""

from __future__ import annotations

import io

from PIL import Image

PAD_FRACTION = 0.15  # margines wokół ramki (ułamek jej wymiarów)
MIN_CROP_PX = 8  # ramki mniejsze niż to uznajemy za szum
MAX_AREA_FRACTION = 0.65  # ramka większa niż 65% strony to błąd modelu
BOX_SCALE = 1000  # model zwraca współrzędne w skali 0-1000


def crop_box_2d(page: Image.Image, box_2d: tuple[int, int, int, int]) -> Image.Image | None:
    """Wycina ramkę ``[ymin, xmin, ymax, xmax]`` (skala 0-1000) z obrazu strony.

    Zwraca ``None``, gdy ramka jest zdegenerowana lub nieprawdopodobna —
    lepiej nie pokazać wycinka niż pokazać błędny.
    """
    ymin, xmin, ymax, xmax = box_2d
    x0 = xmin / BOX_SCALE * page.width
    y0 = ymin / BOX_SCALE * page.height
    x1 = xmax / BOX_SCALE * page.width
    y1 = ymax / BOX_SCALE * page.height
    return _crop_pixels(page, x0, y0, x1, y1)


def crop_pdf_rect(
    page: Image.Image,
    rect_pt: tuple[float, float, float, float],
    page_size_pt: tuple[float, float],
) -> Image.Image | None:
    """Wycina prostokąt podany w punktach PDF (origin w lewym dolnym rogu)."""
    page_w_pt, page_h_pt = page_size_pt
    if page_w_pt <= 0 or page_h_pt <= 0:
        return None
    scale_x = page.width / page_w_pt
    scale_y = page.height / page_h_pt
    x0_pt, y0_pt, x1_pt, y1_pt = rect_pt
    # Oś Y w PDF rośnie do góry, w obrazie — w dół.
    x0 = x0_pt * scale_x
    x1 = x1_pt * scale_x
    y0 = (page_h_pt - y1_pt) * scale_y
    y1 = (page_h_pt - y0_pt) * scale_y
    return _crop_pixels(page, x0, y0, x1, y1)


def _crop_pixels(
    page: Image.Image, x0: float, y0: float, x1: float, y1: float
) -> Image.Image | None:
    if x1 <= x0 or y1 <= y0:
        return None
    width = x1 - x0
    height = y1 - y0
    if width < MIN_CROP_PX or height < MIN_CROP_PX:
        return None
    if width * height > MAX_AREA_FRACTION * page.width * page.height:
        return None

    pad_x = width * PAD_FRACTION
    pad_y = height * PAD_FRACTION
    left = max(0, int(x0 - pad_x))
    top = max(0, int(y0 - pad_y))
    right = min(page.width, int(x1 + pad_x))
    bottom = min(page.height, int(y1 + pad_y))
    if right - left < MIN_CROP_PX or bottom - top < MIN_CROP_PX:
        return None
    return page.crop((left, top, right, bottom))


def to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
