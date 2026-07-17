"""Wspólny interfejs modeli wizyjnych i typy ich odpowiedzi."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from signum.core.models import SignatureKind


class AIError(Exception):
    """Błąd warstwy AI (bazowy)."""


class AIConnectionError(AIError):
    """Nie można połączyć się z usługą AI — przerywa całą partię plików."""


class AIResponseError(AIError):
    """Usługa odpowiedziała, ale odpowiedź jest błędna/nieparsowalna."""


@dataclass(frozen=True, slots=True)
class VisualSignature:
    """Podpis wykryty wizyjnie na stronie przez model."""

    kind: SignatureKind
    confidence: int  # 0-100
    box_2d: tuple[int, int, int, int] | None  # [ymin, xmin, ymax, xmax] w skali 0-1000


@dataclass(frozen=True, slots=True)
class PageAnalysis:
    """Wynik analizy jednej strony przez model wizyjny."""

    description: str  # kilkuwyrazowy opis dokumentu (może być pusty)
    signatures: tuple[VisualSignature, ...]


class VisionModel(ABC):
    """Model wizyjny analizujący obraz strony dokumentu.

    Podklasy implementują wyłącznie transport (:meth:`_generate`); prompt
    i parsowanie odpowiedzi są wspólne, więc każdy dostawca zachowuje się
    identycznie z punktu widzenia pipeline'u.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Czytelna nazwa, np. ``Ollama: gemma4:12b`` — trafia do raportu."""

    @abstractmethod
    def _generate(self, image_jpeg: bytes, prompt: str) -> str:
        """Wysyła obraz + prompt, zwraca surowy tekst odpowiedzi modelu."""

    @abstractmethod
    def check_connection(self) -> str:
        """Sprawdza łączność i dostępność modelu.

        Zwraca komunikat dla użytkownika albo rzuca :class:`AIError`.
        """

    def analyze_page(self, image_jpeg: bytes, prompt: str | None = None) -> PageAnalysis:
        """Analizuje stronę: opis dokumentu + podpisy widoczne na obrazie.

        ``prompt`` pozwala nadpisać domyślny prompt strony (np. część
        merytoryczną edytowaną w ustawieniach programu).
        """
        # Import lokalny — parsing importuje typy z tego modułu (cykl importów).
        from signum.ai.parsing import parse_page_analysis  # noqa: PLC0415
        from signum.ai.prompts import PAGE_PROMPT  # noqa: PLC0415

        raw = self._generate(image_jpeg, prompt or PAGE_PROMPT)
        return parse_page_analysis(raw)
