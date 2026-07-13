"""Testy wycinania fragmentów z podpisami."""

from __future__ import annotations

from PIL import Image

from signum.core.cropping import crop_box_2d, crop_pdf_rect, to_png_bytes


def _page(width: int = 1000, height: int = 1400) -> Image.Image:
    return Image.new("RGB", (width, height), "white")


def test_poprawna_ramka_z_paddingiem() -> None:
    crop = crop_box_2d(_page(), (500, 400, 600, 700))
    assert crop is not None
    # 30% szerokości strony (300 px) + 2×15% padding
    assert 330 <= crop.width <= 400
    assert 130 <= crop.height <= 190


def test_ramka_przy_krawedzi_jest_przycinana() -> None:
    crop = crop_box_2d(_page(), (900, 800, 1000, 1000))
    assert crop is not None  # padding wychodzący poza stronę zostaje obcięty


def test_zdegenerowana_ramka_daje_none() -> None:
    assert crop_box_2d(_page(), (500, 400, 501, 401)) is None  # za mała


def test_ramka_na_cala_strone_odrzucona() -> None:
    assert crop_box_2d(_page(), (0, 0, 1000, 1000)) is None  # > MAX_AREA_FRACTION


def test_crop_pdf_rect_odwraca_os_y() -> None:
    page = _page(1000, 1400)  # strona 500×700 pt → skala 2
    # Prostokąt przy DOLNEJ krawędzi PDF (y od 0 do 100 pt).
    crop = crop_pdf_rect(page, (100.0, 0.0, 300.0, 100.0), (500.0, 700.0))
    assert crop is not None
    # W obrazie musi wylądować przy DOLNEJ krawędzi (duże y) — wysokość
    # wycinka 200 px + pad, więc środek > połowa strony.
    assert crop.height >= 200


def test_crop_pdf_rect_zla_strona_daje_none() -> None:
    assert crop_pdf_rect(_page(), (0.0, 0.0, 10.0, 10.0), (0.0, 0.0)) is None


def test_to_png_bytes_naglowek() -> None:
    data = to_png_bytes(_page(50, 50))
    assert data.startswith(b"\x89PNG")
