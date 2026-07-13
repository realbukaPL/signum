"""Testy wyszukiwania dokumentów (pliki, foldery, rekurencja, duplikaty)."""

from __future__ import annotations

from pathlib import Path

from signum.core.discovery import collect_documents, is_supported


def test_filtruje_nieobslugiwane_rozszerzenia(docs_dir: Path) -> None:
    found = collect_documents([docs_dir], recursive=False)
    names = [f.name for f in found]
    assert "notatka.txt" not in names
    assert "faktura.pdf" in names
    assert "skan_protokol.png" in names


def test_rekurencja(docs_dir: Path) -> None:
    non_recursive = collect_documents([docs_dir], recursive=False)
    recursive = collect_documents([docs_dir], recursive=True)
    assert "zalacznik.png" not in [f.name for f in non_recursive]
    assert "zalacznik.png" in [f.name for f in recursive]


def test_deduplikacja_pliku_i_folderu(docs_dir: Path) -> None:
    # Ten sam plik podany wprost i przez folder nie może się zdublować.
    found = collect_documents([docs_dir / "faktura.pdf", docs_dir], recursive=False)
    assert sum(1 for f in found if f.name == "faktura.pdf") == 1


def test_sortowanie_deterministyczne(docs_dir: Path) -> None:
    found = collect_documents([docs_dir], recursive=True)
    assert found == sorted(found, key=lambda p: str(p).lower())


def test_nieistniejaca_sciezka_jest_pomijana(tmp_path: Path) -> None:
    assert collect_documents([tmp_path / "brak.pdf"]) == []


def test_is_supported_wielkosc_liter() -> None:
    assert is_supported(Path("SKAN.JPG"))
    assert is_supported(Path("dokument.Pdf"))
    assert not is_supported(Path("archiwum.zip"))
