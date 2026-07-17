# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/), wersjonowanie: [SemVer](https://semver.org/).

## [1.0.1] — 2026-07-17

### Added
- Raport HTML: obok wycinka każdego znaleziska miniatura całej strony
  z czerwoną ramką w miejscu wskazanym przez model — nawet niedokładna
  ramka pokazuje, gdzie na stronie model widzi podpis (miniatura powstaje
  także wtedy, gdy sam wycinek został odrzucony jako nieprawdopodobny).
- Ustawienia AI: sekcja „Prompt programu" — edytowalna część merytoryczna
  promptu (stały format odpowiedzi JSON program dokleja automatycznie),
  z przyciskiem „Przywróć domyślny".
- Ustawienia AI (Ollama): konfigurowalne okno kontekstu `num_ctx`
  (domyślnie 8192; Ollama sama z siebie używa zaledwie 4096).
- Ostrzeżenie przy przełączeniu dostawcy z lokalnego na chmurowy: modal
  „Dane opuszczą ten komputer" z przyciskiem „Rozumiem zagrożenie"
  odblokowywanym po 3 s; czerwone ostrzeżenie na stronach dostawców
  chmurowych; plakietka „Model online" w pasku stanu okna głównego.
- Większe opcje rozmiaru obrazu dla modelu (1600, 2048 px) — z adnotacją,
  że dla gemma4 Ollama i tak ogranicza obraz do ~0,65 Mpx (280 tokenów
  wizyjnych), więc większe rozmiary wykorzystają głównie modele chmurowe.

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
