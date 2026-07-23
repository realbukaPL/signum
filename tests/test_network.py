"""Walidacja endpointów AI i klasyfikacja przetwarzania lokalnego."""

from __future__ import annotations

import pytest

from signum.network import (
    EndpointValidationError,
    is_loopback_endpoint,
    normalize_ai_endpoint,
    processing_is_local,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:11434",
        "http://127.0.0.1:11434/",
        "http://[::1]:11434",
        "https://ollama.example.test",
    ],
)
def test_poprawne_endpointy(url: str) -> None:
    assert normalize_ai_endpoint(url, "https://default.invalid", "test")


@pytest.mark.parametrize(
    "url",
    [
        "http://192.168.1.20:11434",
        "http://ollama.example.test",
        "ftp://localhost/model",
        "https://user:secret@example.test",
        "https://example.test/path?token=secret",
        "https://example .test",
        "https://example.test\\api",
    ],
)
def test_niebezpieczne_endpointy_sa_odrzucane(url: str) -> None:
    with pytest.raises(EndpointValidationError):
        normalize_ai_endpoint(url, "https://default.invalid", "test")


def test_tylko_ollama_loopback_jest_lokalna() -> None:
    assert is_loopback_endpoint("http://127.0.0.1:11434")
    assert processing_is_local("ollama", "http://localhost:11434")
    assert not processing_is_local("ollama", "https://ollama.example.test")
    assert not processing_is_local("openai", "http://localhost:8000/v1")


def test_ipv6_zachowuje_poprawne_nawiasy() -> None:
    assert (
        normalize_ai_endpoint("http://[::1]:11434/", "https://default.invalid", "test")
        == "http://[::1]:11434"
    )
