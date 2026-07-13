"""Testy wykrywania podpisów cyfrowych w strukturze PDF."""

from __future__ import annotations

from pathlib import Path

from signum.core.digital import scan_digital_signatures


def _write(tmp_path: Path, name: str, data: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_wykrywa_podpis_pkcs7(tmp_path: Path, signed_pdf_bytes: bytes) -> None:
    result = scan_digital_signatures(_write(tmp_path, "signed.pdf", signed_pdf_bytes))
    assert len(result.signatures) == 1
    sig = result.signatures[0]
    assert sig.field_name == "Signature1"
    assert "adbe.pkcs7.detached" in sig.kind_label
    assert sig.page == 1
    assert sig.rect_pt is not None
    assert sig.signing_time is not None
    assert sig.reason == "Akceptacja aneksu"


def test_wykrywa_podpis_pades(tmp_path: Path, pades_pdf_bytes: bytes) -> None:
    result = scan_digital_signatures(_write(tmp_path, "pades.pdf", pades_pdf_bytes))
    assert len(result.signatures) == 1
    assert "PAdES" in result.signatures[0].kind_label


def test_podpis_niewidoczny_bez_rect(
    tmp_path: Path, invisible_signed_pdf_bytes: bytes
) -> None:
    result = scan_digital_signatures(
        _write(tmp_path, "invisible.pdf", invisible_signed_pdf_bytes)
    )
    assert len(result.signatures) == 1
    assert result.signatures[0].rect_pt is None  # zerowy widget = podpis niewidoczny


def test_puste_pole_podpisu_nie_jest_podpisem(
    tmp_path: Path, empty_field_pdf_bytes: bytes
) -> None:
    result = scan_digital_signatures(_write(tmp_path, "empty.pdf", empty_field_pdf_bytes))
    assert result.signatures == []
    assert result.empty_signature_fields == ["PodpisPracownika"]


def test_pdf_bez_formularza(tmp_path: Path, text_pdf_bytes: bytes) -> None:
    result = scan_digital_signatures(_write(tmp_path, "plain.pdf", text_pdf_bytes))
    assert result.signatures == []
    assert result.empty_signature_fields == []


def test_uszkodzony_pdf_nie_rzuca_wyjatku(tmp_path: Path) -> None:
    result = scan_digital_signatures(_write(tmp_path, "broken.pdf", b"to nie jest pdf"))
    assert result.signatures == []
    assert result.notes  # problem odnotowany zamiast wyjątku


def test_detail_zawiera_kluczowe_informacje(tmp_path: Path, signed_pdf_bytes: bytes) -> None:
    result = scan_digital_signatures(_write(tmp_path, "signed.pdf", signed_pdf_bytes))
    detail = result.signatures[0].detail
    assert "adbe.pkcs7.detached" in detail
    assert "powód: Akceptacja aneksu" in detail
