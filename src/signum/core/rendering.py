"""Renderowanie dokumentów do obrazów rastrowych.

PDF-y renderuje pypdfium2 (licencja BSD/Apache), pliki graficzne wczytuje
Pillow. Obrazy stron trzymamy w pełnej rozdzielczości roboczej (do wycinków
podpisów), a do modelu AI wysyłamy pomniejszoną kopię JPEG.
"""

from __future__ import annotations

import io
import math
import warnings
from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageOps

from signum.core.discovery import PDF_EXTENSIONS

RENDER_SCALE = 150 / 72  # rendering PDF w ~150 DPI
MAX_WORKING_SIDE = 2400  # px — limit pamięci dla obrazu roboczego
JPEG_QUALITY = 85
MAX_INPUT_FILE_BYTES = 250 * 1024 * 1024
MAX_IMAGE_PIXELS = 50_000_000

# Ostrzeżenie Pillow zamieniamy niżej w błąd, zanim obraz zostanie w pełni
# zdekompresowany. Limit 50 Mpx nadal obejmuje duże skany biurowe.
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


class DocumentReadError(Exception):
    """Nie udało się odczytać/wyrenderować dokumentu."""


@dataclass(slots=True)
class PageImage:
    """Jedna strona dokumentu wyrenderowana do obrazu.

    ``page_size_pt`` jest ustawione tylko dla PDF (potrzebne do mapowania
    prostokątów pól podpisu z układu współrzędnych PDF na piksele).
    """

    number: int  # 1-bazowy numer strony
    image: Image.Image  # RGB, pełna rozdzielczość robocza
    page_size_pt: tuple[float, float] | None = None  # (szerokość, wysokość) w punktach


def is_pdf(path: Path) -> bool:
    return path.suffix.lower() in PDF_EXTENSIONS


def load_pages(path: Path, max_pages: int) -> tuple[list[PageImage], int]:
    """Wczytuje do ``max_pages`` stron dokumentu.

    Zwraca (strony, łączna_liczba_stron). Obsługuje PDF, obrazy jedno-
    i wielostronicowe (TIFF). Rzuca :class:`DocumentReadError` dla plików
    uszkodzonych lub zabezpieczonych hasłem.
    """
    try:
        size = path.stat().st_size
        if size > MAX_INPUT_FILE_BYTES:
            raise DocumentReadError(
                f"Plik ma {size / (1024 * 1024):.1f} MB; limit bezpieczeństwa wynosi "
                f"{MAX_INPUT_FILE_BYTES // (1024 * 1024)} MB"
            )
        max_pages = max(1, min(int(max_pages), 500))
        if is_pdf(path):
            return _load_pdf_pages(path, max_pages)
        return _load_image_pages(path, max_pages)
    except DocumentReadError:
        raise
    except Exception as exc:  # pdfium/Pillow rzucają własne, różnorodne wyjątki
        raise DocumentReadError(f"Nie można odczytać pliku: {exc}") from exc


def render_pdf_page(path: Path, page_number: int) -> PageImage:
    """Renderuje pojedynczą stronę PDF (1-bazowa) — np. dla wycinka podpisu
    cyfrowego leżącego poza zakresem stron analizowanych wizyjnie."""
    try:
        pdf = pdfium.PdfDocument(str(path))
    except Exception as exc:
        raise DocumentReadError(f"Nie można otworzyć PDF: {exc}") from exc
    try:
        if not 1 <= page_number <= len(pdf):
            raise DocumentReadError(f"Strona {page_number} poza zakresem")
        return _render_page(pdf, page_number)
    finally:
        pdf.close()


def _load_pdf_pages(path: Path, max_pages: int) -> tuple[list[PageImage], int]:
    try:
        pdf = pdfium.PdfDocument(str(path))
    except Exception as exc:
        raise DocumentReadError(f"Nie można otworzyć PDF: {exc}") from exc
    try:
        total = len(pdf)
        pages = [_render_page(pdf, i + 1) for i in range(min(total, max_pages))]
        return pages, total
    finally:
        pdf.close()


def _render_page(pdf: pdfium.PdfDocument, page_number: int) -> PageImage:
    page = pdf[page_number - 1]
    width_pt, height_pt = page.get_size()
    if (
        not math.isfinite(width_pt)
        or not math.isfinite(height_pt)
        or width_pt <= 0
        or height_pt <= 0
    ):
        raise DocumentReadError("PDF zawiera niepoprawny rozmiar strony")
    scale = RENDER_SCALE
    longest = max(width_pt, height_pt) * scale
    if longest > MAX_WORKING_SIDE:
        scale = MAX_WORKING_SIDE / max(width_pt, height_pt)
    bitmap = page.render(scale=scale)
    image = bitmap.to_pil().convert("RGB")
    return PageImage(number=page_number, image=image, page_size_pt=(width_pt, height_pt))


def _load_image_pages(path: Path, max_pages: int) -> tuple[list[PageImage], int]:
    pages: list[PageImage] = []
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as im:
            total = getattr(im, "n_frames", 1)
            for frame in range(min(total, max_pages)):
                if total > 1:
                    im.seek(frame)
                frame_img = ImageOps.exif_transpose(im) or im
                frame_img = frame_img.convert("RGB")
                frame_img = _cap_size(frame_img)
                pages.append(PageImage(number=frame + 1, image=frame_img))
    return pages, total


def _cap_size(image: Image.Image) -> Image.Image:
    longest = max(image.size)
    if longest <= MAX_WORKING_SIDE:
        return image
    ratio = MAX_WORKING_SIDE / longest
    new_size = (max(1, round(image.width * ratio)), max(1, round(image.height * ratio)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def to_model_jpeg(image: Image.Image, max_side: int) -> bytes:
    """Pomniejszona kopia strony jako JPEG — wejście dla modelu wizyjnego."""
    copy = image.copy()
    copy.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    copy.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return buf.getvalue()
