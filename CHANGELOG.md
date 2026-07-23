# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/), wersjonowanie: [SemVer](https://semver.org/).

## [1.0.4] — 2026-07-22

### Added
- Diagnostyka Ollamy w ustawieniach oraz asynchroniczny preflight usługi i modelu
  przed uruchomieniem każdej partii; instalator wyjaśnia, że Python jest wbudowany,
  a Ollama jest opcjonalnym, osobno instalowanym składnikiem.
- Jawne potwierdzenie ryzyka w CLI (`--acknowledge-risks`) i ostrzeżenie o
  poufności przed eksportem raportu.
- Audyt zależności w CI, przypięte wersje zależności i akcji oraz Dependabot.

### Security
- Zdalne endpointy wymagają HTTPS, przekierowania HTTP są wyłączone, a Ollama
  na pętli zwrotnej nie dziedziczy proxy z otoczenia procesu.
- Raporty nie zawierają pełnych ścieżek; komórki CSV są chronione przed formula
  injection, a raport HTML ma restrykcyjną politykę CSP.
- Limity rozmiaru pliku, liczby pikseli, stron i złożoności hierarchii pól PDF
  ograniczają ryzyko wyczerpania pamięci lub czasu przez złośliwy dokument.
- Konfiguracja jest walidowana i zapisywana atomowo; treści pochodzące z modelu
  i dokumentu są wyświetlane w GUI jako tekst jawny.

### Changed
- Metadane autora zastąpiono neutralnym `Signum contributors`; pozostawiono
  wyłącznie wskazany wyjątek wydawcy w instalatorze.
- Usunięto screenshoty zawierające lokalne ścieżki i rozszerzono reguły ignorowania
  sekretów, artefaktów instalatora oraz lokalnych ustawień narzędzi.

## [1.0.3] — 2026-07-22

### Added
- Instalator: osobny polsko- i anglojęzyczny ekran świadomości ryzyka z czterema
  wymaganymi potwierdzeniami; instalacja cicha wymaga `/ACKNOWLEDGERISKS=1`.
- GUI: jedno ostrzeżenie przed uruchomieniem całej partii dokumentów, obejmujące
  uprawnienia do przetwarzania, sposób pracy modelu i ręczną weryfikację wyników.

### Changed
- Raport HTML i okno „O programie" wyraźniej opisują ograniczenia wyniku oraz
  obowiązek niezależnej weryfikacji.

## [1.0.2] — 2026-07-20

### Fixed
- Ollama: znacząco lepszy recall detekcji — structured outputs (`format` =
  schemat JSON) potrafił tłumić znaleziska (model zamykał listę po pieczątce
  i gubił podpis odręczny obok niej). Pierwsze zapytanie idzie teraz bez
  wymuszania schematu; `format` jest używany tylko jako jednorazowe ponowienie,
  gdy odpowiedź nie zawiera poprawnego obiektu JSON. Zweryfikowane na
  dokumencie z pieczątką i podpisem (wcześniej wykrywana tylko pieczątka)
  oraz na przykładach z repo (bez nowych fałszywych pozytywów).

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
