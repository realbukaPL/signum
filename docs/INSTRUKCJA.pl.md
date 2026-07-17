# Signum — instrukcja użytkownika

Signum sprawdza, **czy dokumenty są podpisane**. Obsługuje PDF-y oraz skany
(JPG, PNG, TIFF, BMP, WEBP) i wykrywa:

- podpisy odręczne,
- parafki,
- pieczątki,
- podpisy cyfrowe (kwalifikowane i zwykłe: PAdES, PKCS#7, X.509, znaczniki czasu,
  podpisy certyfikujące).

Program **nie ocenia ważności prawnej ani poprawności kryptograficznej** podpisów —
stwierdza wyłącznie ich obecność i pokazuje wycinki do ręcznej weryfikacji.

## Instalacja

1. Uruchom `Signum-Setup-<wersja>.exe` i przejdź przez kreator (instalacja nie
   wymaga uprawnień administratora).
2. Jeśli chcesz pracować lokalnie (zalecane): zainstaluj [Ollamę](https://ollama.com)
   i pobierz model wizyjny, np.:

   ```
   ollama pull gemma4:12b
   ```

## Pierwsze uruchomienie — ustawienia AI

Otwórz **Ustawienia AI…** i wybierz dostawcę:

- **Ollama (model lokalny)** — dokumenty nie opuszczają komputera. Kliknij
  „Odśwież listę", wybierz model obsługujący obrazy (np. `gemma4:12b`),
  kliknij **Testuj połączenie**. Dodatkowo możesz ustawić **okno kontekstu
  (num_ctx)** — Ollama sama z siebie używa tylko 4096 tokenów; Signum domyślnie
  ustawia 8192 (większe okno = większe zużycie pamięci karty graficznej).
- **OpenAI / API zgodne z OpenAI** — podaj adres API, nazwę modelu i klucz API.
- **Claude (Anthropic)** — podaj nazwę modelu i klucz API.

**Uwaga — dostawcy chmurowi:** przy przełączeniu z Ollamy na OpenAI/Claude
program wyświetla ostrzeżenie, że analizowane dokumenty **będą wysyłane przez
internet poza komputer** — przycisk „Rozumiem zagrożenie" odblokowuje się po
3 sekundach. Dopóki aktywny jest dostawca chmurowy, w pasku stanu okna głównego
widoczna jest czerwona plakietka **„Model online"**.

Klucze API są zapisywane w Menedżerze poświadczeń systemu Windows, nie w plikach.

Ustawienia przetwarzania:

| Opcja | Znaczenie |
|---|---|
| Limit stron na dokument | ile pierwszych stron PDF-a jest analizowanych wizyjnie (podpisy cyfrowe są wykrywane zawsze, w całym pliku) |
| Rozmiar obrazu dla modelu | większy = dokładniej, wolniej. Uwaga: dla `gemma4` Ollama i tak zmniejsza obraz do ~0,65 Mpx — rozmiary powyżej 1120 px wykorzystają głównie modele chmurowe |
| Limit czasu odpowiedzi | maksymalny czas oczekiwania na model |
| Przeszukuj podfoldery | dotyczy dodawania folderów |

**Prompt programu** — w tej sekcji możesz edytować merytoryczną część polecenia
wysyłanego do modelu (np. dodać wskazówki specyficzne dla Twoich dokumentów:
„zwróć uwagę na pole przy napisie *czytelny podpis*"). Wymagany format
odpowiedzi program dokleja automatycznie — nie trzeba (i nie należy) go
opisywać. Przycisk **Przywróć domyślny** cofa zmiany.

## Praca z programem

1. **Dodaj dokumenty**: przeciągnij pliki lub całe foldery do okna, albo użyj
   przycisków **Dodaj pliki…** / **Pracuj na folderze…**.
2. Kliknij **Przetwórz**. Pliki są analizowane po kolei — pasek postępu pokazuje
   bieżący plik i szacowany pozostały czas. Możesz kliknąć **Anuluj**
   (dokończy się bieżąca strona).
3. Wyniki pojawiają się w tabeli na bieżąco:
   - **Tytuł (AI)** — kilkuwyrazowy opis dokumentu nadany przez model,
   - **Podpisy** — `PODPISANY (n)` albo `BRAK PODPISU`,
   - **Pewność** — najwyższa pewność wykrycia w pliku.
4. Kliknij wiersz, aby zobaczyć **szczegóły**: rodzaj każdego podpisu, stronę,
   pewność oraz **wycinek podpisu** (kliknij miniaturę, aby powiększyć).
   Dla podpisów cyfrowych wyświetlane są podtyp, podpisujący i data.
5. **Zapisz raport…** — samowystarczalny HTML albo CSV (średniki, zgodny
   z polskim Excelem). W raporcie HTML przy każdym znalezisku jest wycinek
   oraz **miniatura całej strony z czerwoną ramką** w miejscu wskazanym przez
   model — nawet gdy wycinek chybił, miniatura pokazuje, gdzie szukać podpisu.

Błąd jednego pliku (np. uszkodzony PDF, PDF z hasłem) nie przerywa pozostałych —
plik dostaje status „Błąd" z opisem w dymku. Utrata połączenia z modelem przerywa
partię z komunikatem.

## Tryb wiersza poleceń

Do automatyzacji służy `signum-cli` (w instalacji ze źródeł):

```
signum-cli C:\skany --html raport.html --csv raport.csv
signum-cli umowa.pdf --provider ollama --model gemma4:12b
```

## Rozwiązywanie problemów

| Objaw | Rozwiązanie |
|---|---|
| „Brak połączenia z Ollamą" | uruchom Ollamę (`ollama serve` lub aplikacja); sprawdź adres w ustawieniach |
| „Model … nie jest zainstalowany" | `ollama pull <model>` |
| Bardzo długi czas analizy | mniejszy model, mniejszy „rozmiar obrazu dla modelu", mniejszy limit stron |
| PDF ze statusem „Błąd: … zaszyfrowany" | zdejmij hasło z pliku przed analizą |
| Brak wycinka przy wykrytym podpisie | model nie podał wiarygodnej ramki — podpis jest mimo to zliczony; zweryfikuj w pliku |
| Wycinek pokazuje fragment bez podpisu | lokalizacja z modelu bywa przybliżona — spójrz na miniaturę strony z czerwoną ramką w raporcie HTML |
