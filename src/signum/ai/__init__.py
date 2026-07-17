"""Warstwa modeli wizyjnych AI: Ollama (lokalnie) oraz API chmurowe."""

from __future__ import annotations

from typing import TYPE_CHECKING

from signum.ai.anthropic_client import AnthropicVisionModel
from signum.ai.base import AIConnectionError, AIError, AIResponseError, VisionModel
from signum.ai.ollama_client import OllamaVisionModel
from signum.ai.openai_client import OpenAIVisionModel
from signum.config import get_api_key

if TYPE_CHECKING:
    from signum.config import AppConfig

__all__ = [
    "AIConnectionError",
    "AIError",
    "AIResponseError",
    "AnthropicVisionModel",
    "OllamaVisionModel",
    "OpenAIVisionModel",
    "VisionModel",
    "create_vision_model",
]


def create_vision_model(config: AppConfig, api_key: str | None = None) -> VisionModel:
    """Fabryka modelu wizyjnego na podstawie konfiguracji aplikacji.

    ``api_key`` przekazuje się wprost (np. z dialogu ustawień przed zapisem);
    domyślnie klucz jest pobierany z systemowego magazynu poświadczeń.
    """
    if config.provider == "ollama":
        return OllamaVisionModel(
            base_url=config.ollama_url,
            model=config.ollama_model,
            timeout_s=config.timeout_s,
            num_ctx=config.ollama_num_ctx,
        )
    if config.provider == "openai":
        return OpenAIVisionModel(
            base_url=config.openai_base_url,
            api_key=api_key if api_key is not None else (get_api_key("openai") or ""),
            model=config.openai_model,
            timeout_s=config.timeout_s,
        )
    if config.provider == "anthropic":
        return AnthropicVisionModel(
            api_key=api_key if api_key is not None else (get_api_key("anthropic") or ""),
            model=config.anthropic_model,
            timeout_s=config.timeout_s,
        )
    raise ValueError(f"Nieznany dostawca AI: {config.provider!r}")
