"""Konfiguracja aplikacji.

Ustawienia zapisujemy jako JSON w katalogu konfiguracji użytkownika
(``%APPDATA%/Signum`` na Windows). Klucze API NIGDY nie trafiają do pliku —
przechowuje je systemowy magazyn poświadczeń (Windows Credential Manager)
poprzez bibliotekę ``keyring``.
"""

from __future__ import annotations

import contextlib
import json
import logging
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

import keyring
import keyring.errors
import platformdirs

from signum import APP_NAME

logger = logging.getLogger(__name__)

KEYRING_SERVICE = APP_NAME
PROVIDERS = ("ollama", "openai", "anthropic")


def config_dir() -> Path:
    return Path(platformdirs.user_config_dir(APP_NAME, appauthor=False, roaming=True))


def config_file() -> Path:
    return config_dir() / "settings.json"


@dataclass(slots=True)
class AppConfig:
    """Wszystkie trwałe ustawienia aplikacji (bez sekretów)."""

    provider: str = "ollama"  # ollama | openai | anthropic
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:12b"
    ollama_num_ctx: int = 8192  # okno kontekstu (domyślne Ollamy to zaledwie 4096)
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"
    anthropic_model: str = "claude-sonnet-5"
    timeout_s: int = 300
    max_pages_per_doc: int = 10
    model_image_max_side: int = 1120
    custom_prompt: str = ""  # część merytoryczna promptu; pusta = domyślna
    recursive_folders: bool = True
    last_dir: str = ""

    @classmethod
    def load(cls) -> AppConfig:
        """Wczytuje ustawienia; przy braku/uszkodzeniu pliku zwraca domyślne."""
        path = config_file()
        try:
            raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return cls()
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Nie można wczytać %s (%s) — używam domyślnych", path, exc)
            return cls()
        known = {f.name: f.type for f in fields(cls)}
        kwargs = {k: v for k, v in raw.items() if k in known}
        config = cls(**kwargs)
        if config.provider not in PROVIDERS:
            config.provider = "ollama"
        return config

    def save(self) -> None:
        path = config_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8"
        )


def get_api_key(provider: str) -> str | None:
    """Pobiera klucz API z systemowego magazynu poświadczeń."""
    try:
        return keyring.get_password(KEYRING_SERVICE, f"{provider}_api_key")
    except keyring.errors.KeyringError as exc:
        logger.warning("Magazyn poświadczeń niedostępny: %s", exc)
        return None


def set_api_key(provider: str, key: str) -> None:
    """Zapisuje (lub usuwa, gdy pusty) klucz API w magazynie poświadczeń."""
    entry = f"{provider}_api_key"
    try:
        if key:
            keyring.set_password(KEYRING_SERVICE, entry, key)
        else:
            # Brak klucza do usunięcia nie jest błędem.
            with contextlib.suppress(keyring.errors.PasswordDeleteError):
                keyring.delete_password(KEYRING_SERVICE, entry)
    except keyring.errors.KeyringError as exc:
        logger.warning("Nie można zapisać klucza w magazynie poświadczeń: %s", exc)
        raise
