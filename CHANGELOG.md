# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/), wersjonowanie: [SemVer](https://semver.org/).

## [1.0.0] — 2026-07-13

### Added
- GUI (PySide6): drag & drop plików i folderów, kolejka, sekwencyjne przetwarzanie
  z paskiem postępu i ETA, anulowanie, tabela wyników + panel szczegółów
  z wycinkami podpisów (klik = powiększenie).
- Detekcja wizyjna (vision LLM): podpisy odręczne, parafki, pieczątki —
  z pewnością 0–100 i ramkami `box_2d` walidowanymi przed wycięciem.
- Detekcja strukturalna podpisów cyfrowych w PDF (pypdf): PAdES/CAdES,
  CMS/PKCS#7, X.509, znaczniki czasu RFC 3161, podpisy certyfikujące (DocMDP),
  podpisy praw użycia (UR3); wycinki widocznych widgetów podpisu; raportowanie
  pustych pól podpisu.
- Dostawcy AI: Ollama (structured outputs, lista modeli), API zgodne z OpenAI,
  Claude (Anthropic). Klucze API w Windows Credential Manager (keyring).
- Raporty: samowystarczalny HTML z osadzonymi wycinkami oraz CSV (`;`, BOM,
  CRLF — zgodny z polskim Excelem).
- Tryb `signum-cli` do automatyzacji (te same wyniki co GUI).
- Fabryka dokumentów testowych (w tym PDF-y naprawdę podpisane cyfrowo przez
  pyhanko) + 80 testów jednostkowych i GUI (pytest, pytest-qt), ruff, mypy.
- Instalator Windows (PyInstaller + Inno Setup 6, per-user, PL/EN).
