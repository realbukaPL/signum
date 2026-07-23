"""Testy konfiguracji (zapis/odczyt, odporność na uszkodzenia)."""

from __future__ import annotations

import json
from pathlib import Path

from signum.config import AppConfig


def test_domyslna_konfiguracja_gdy_brak_pliku(isolated_config: Path) -> None:
    config = AppConfig.load()
    assert config.provider == "ollama"
    assert config.ollama_model == "gemma4:12b"
    assert not isolated_config.exists()


def test_zapis_i_odczyt(isolated_config: Path) -> None:
    config = AppConfig.load()
    config.provider = "anthropic"
    config.max_pages_per_doc = 25
    config.save()
    assert isolated_config.exists()

    loaded = AppConfig.load()
    assert loaded.provider == "anthropic"
    assert loaded.max_pages_per_doc == 25


def test_uszkodzony_plik_daje_domyslne(isolated_config: Path) -> None:
    isolated_config.parent.mkdir(parents=True, exist_ok=True)
    isolated_config.write_text("{to nie jest json", encoding="utf-8")
    config = AppConfig.load()
    assert config.provider == "ollama"


def test_nieznane_klucze_sa_ignorowane(isolated_config: Path) -> None:
    isolated_config.parent.mkdir(parents=True, exist_ok=True)
    isolated_config.write_text(
        json.dumps({"provider": "openai", "stary_klucz_z_v0": 123}), encoding="utf-8"
    )
    config = AppConfig.load()
    assert config.provider == "openai"


def test_nieznany_provider_wraca_do_ollamy(isolated_config: Path) -> None:
    isolated_config.parent.mkdir(parents=True, exist_ok=True)
    isolated_config.write_text(json.dumps({"provider": "skynet"}), encoding="utf-8")
    assert AppConfig.load().provider == "ollama"


def test_niepoprawne_typy_i_zakresy_sa_sanitowane(isolated_config: Path) -> None:
    isolated_config.parent.mkdir(parents=True, exist_ok=True)
    isolated_config.write_text(
        json.dumps(
            {
                "timeout_s": "bez limitu",
                "max_pages_per_doc": 999_999,
                "model_image_max_side": -1,
                "recursive_folders": 1,
                "last_dir": ["C:/prywatne"],
                "ollama_model": "   ",
            }
        ),
        encoding="utf-8",
    )

    config = AppConfig.load()

    assert config.timeout_s == 300
    assert config.max_pages_per_doc == 500
    assert config.model_image_max_side == 1120
    assert config.recursive_folders is True
    assert config.last_dir == ""
    assert config.ollama_model == "gemma4:12b"


def test_klucze_api_nie_trafiaja_do_pliku(isolated_config: Path) -> None:
    config = AppConfig.load()
    config.save()
    content = isolated_config.read_text(encoding="utf-8")
    assert "api_key" not in content
    assert "key" not in json.loads(content)
