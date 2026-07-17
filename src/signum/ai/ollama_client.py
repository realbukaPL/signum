"""Klient Ollamy — lokalny model wizyjny przez HTTP API (domyślny dostawca)."""

from __future__ import annotations

import base64

import requests

from signum.ai.base import AIConnectionError, AIResponseError, VisionModel
from signum.ai.prompts import RESPONSE_SCHEMA

DEFAULT_URL = "http://localhost:11434"
DEFAULT_NUM_CTX = 8192


class OllamaVisionModel(VisionModel):
    """Model wizyjny serwowany przez Ollamę (np. ``gemma4:12b``).

    Używa structured outputs (``format`` = schemat JSON), co znacząco
    poprawia zgodność odpowiedzi ze schematem; resztę dosztywnia parser.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_s: int = 300,
        num_ctx: int = DEFAULT_NUM_CTX,
    ) -> None:
        self._base_url = (base_url or DEFAULT_URL).rstrip("/")
        self._model = model
        self._timeout_s = timeout_s
        self._num_ctx = num_ctx

    @property
    def name(self) -> str:
        return f"Ollama: {self._model}"

    def _generate(self, image_jpeg: bytes, prompt: str) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [base64.b64encode(image_jpeg).decode("ascii")],
                }
            ],
            "stream": False,
            "format": RESPONSE_SCHEMA,
            "options": {"temperature": 0, "num_ctx": self._num_ctx},
        }
        try:
            response = requests.post(
                f"{self._base_url}/api/chat", json=payload, timeout=self._timeout_s
            )
        except requests.exceptions.RequestException as exc:
            raise AIConnectionError(
                f"Brak połączenia z Ollamą pod {self._base_url}: {exc}"
            ) from exc
        if response.status_code != 200:
            raise AIResponseError(
                f"Ollama zwróciła HTTP {response.status_code}: {response.text[:300]}"
            )
        try:
            content = response.json()["message"]["content"]
        except (ValueError, KeyError) as exc:
            raise AIResponseError(f"Niepoprawna odpowiedź Ollamy: {exc}") from exc
        return str(content)

    def check_connection(self) -> str:
        try:
            version = requests.get(f"{self._base_url}/api/version", timeout=10).json()
            models = self.list_models(self._base_url)
        except requests.exceptions.RequestException as exc:
            raise AIConnectionError(
                f"Brak połączenia z Ollamą pod {self._base_url}: {exc}"
            ) from exc
        if not _model_available(self._model, models):
            raise AIResponseError(
                f"Model {self._model!r} nie jest zainstalowany w Ollamie. "
                f"Dostępne: {', '.join(models) or '(brak)'}. "
                f"Pobierz go poleceniem: ollama pull {self._model}"
            )
        return f"Ollama {version.get('version', '?')} — model {self._model} dostępny"

    @staticmethod
    def list_models(base_url: str, timeout_s: int = 10) -> list[str]:
        """Lista modeli zainstalowanych w Ollamie (do rozwijanej listy w GUI)."""
        url = (base_url or DEFAULT_URL).rstrip("/")
        try:
            response = requests.get(f"{url}/api/tags", timeout=timeout_s)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            raise AIConnectionError(f"Brak połączenia z Ollamą pod {url}: {exc}") from exc
        return sorted(model["name"] for model in data.get("models", []))


def _model_available(wanted: str, installed: list[str]) -> bool:
    # Ollama traktuje "model" i "model:latest" zamiennie.
    candidates = {wanted, f"{wanted}:latest"}
    return any(name in candidates for name in installed)
