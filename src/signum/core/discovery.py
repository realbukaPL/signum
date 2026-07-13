"""Wyszukiwanie dokumentów do analizy (pliki podane wprost i skan folderów)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
SUPPORTED_EXTENSIONS = PDF_EXTENSIONS | IMAGE_EXTENSIONS


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def collect_documents(paths: Iterable[Path], recursive: bool = True) -> list[Path]:
    """Zbiera obsługiwane dokumenty z podanych plików i folderów.

    Foldery są przeszukiwane (opcjonalnie rekurencyjnie), duplikaty usuwane,
    wynik posortowany alfabetycznie — kolejność przetwarzania jest wtedy
    przewidywalna dla użytkownika.
    """
    seen: set[Path] = set()
    result: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            pattern = "**/*" if recursive else "*"
            candidates = sorted(path.glob(pattern), key=lambda p: str(p).lower())
        else:
            candidates = [path]
        for candidate in candidates:
            if not candidate.is_file() or not is_supported(candidate):
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            result.append(resolved)
    result.sort(key=lambda p: str(p).lower())
    return result
