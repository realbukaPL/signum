"""Testy renderowania PDF i wczytywania obrazów."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from signum.core import rendering
from signum.core.rendering import (
    DocumentReadError,
    load_pages,
    render_pdf_page,
    to_model_jpeg,
)
from tests import docfactory


def test_pdf_renderuje_wszystkie_strony_do_limitu(tmp_path: Path) -> None:
    pdf = tmp_path / "trzy_strony.pdf"
    pdf.write_bytes(docfactory.make_text_pdf(pages=3))
    pages, total = load_pages(pdf, max_pages=2)
    assert total == 3
    assert [p.number for p in pages] == [1, 2]
    assert pages[0].page_size_pt is not None
    assert pages[0].image.mode == "RGB"
    # A4 przy 150 DPI ≈ 1240×1754 px
    assert 1200 < pages[0].image.width < 1300


def test_obraz_jednostronicowy(tmp_path: Path) -> None:
    png = tmp_path / "skan.png"
    docfactory.make_clean_scan().save(png)
    pages, total = load_pages(png, max_pages=10)
    assert total == 1
    assert pages[0].number == 1
    assert pages[0].page_size_pt is None


def test_tiff_wielostronicowy(tmp_path: Path) -> None:
    tif = tmp_path / "sklejka.tif"
    frames = [docfactory.make_clean_scan(), docfactory.make_signed_scan()]
    frames[0].save(tif, save_all=True, append_images=frames[1:])
    pages, total = load_pages(tif, max_pages=10)
    assert total == 2
    assert [p.number for p in pages] == [1, 2]


def test_render_pojedynczej_strony(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(docfactory.make_text_pdf(pages=3))
    page = render_pdf_page(pdf, 3)
    assert page.number == 3
    with pytest.raises(DocumentReadError):
        render_pdf_page(pdf, 9)


def test_uszkodzony_plik_rzuca_documentreaderror(tmp_path: Path) -> None:
    bad = tmp_path / "zepsuty.pdf"
    bad.write_bytes(b"nie-pdf")
    with pytest.raises(DocumentReadError):
        load_pages(bad, max_pages=1)


def test_plik_przekraczajacy_limit_jest_odrzucany(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = tmp_path / "za_duzy.png"
    image.write_bytes(b"12345")
    monkeypatch.setattr(rendering, "MAX_INPUT_FILE_BYTES", 4)
    with pytest.raises(DocumentReadError, match="limit bezpieczeństwa"):
        load_pages(image, max_pages=1)


def test_bomba_dekompresyjna_jest_odrzucana(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = tmp_path / "duzo_pikseli.png"
    Image.new("RGB", (40, 40), "white").save(image)
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    with pytest.raises(DocumentReadError):
        load_pages(image, max_pages=1)


def test_to_model_jpeg_pomniejsza(tmp_path: Path) -> None:
    image = Image.new("RGB", (3000, 2000), "white")
    jpeg = to_model_jpeg(image, max_side=1024)
    import io

    decoded = Image.open(io.BytesIO(jpeg))
    assert max(decoded.size) == 1024
    assert decoded.format == "JPEG"
    # oryginał nietknięty
    assert image.size == (3000, 2000)
