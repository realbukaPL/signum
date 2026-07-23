"""Testy dymne GUI (pytest-qt, platforma offscreen)."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from signum.ai import create_vision_model
from signum.core.models import DocumentResult, DocumentStatus, SignatureFinding, SignatureKind
from signum.ui.main_window import BatchRiskDialog, MainWindow
from signum.ui.settings_dialog import OnlineWarningDialog, SettingsDialog

_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGA"
    "hKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture()
def window(qtbot, isolated_config):  # type: ignore[no-untyped-def]
    win = MainWindow()
    qtbot.addWidget(win)
    return win


class TestMainWindow:
    def test_stan_poczatkowy(self, window: MainWindow) -> None:
        assert window.table.rowCount() == 0
        assert not window.act_process.isEnabled()
        assert not window.act_cancel.isEnabled()
        assert window._left_stack.currentIndex() == 0  # podpowiedź drag&drop

    def test_dodanie_dokumentow(self, window: MainWindow, docs_dir: Path) -> None:
        window._add_documents([docs_dir])
        assert window.table.rowCount() == 5  # 2×pdf + 2×skan + 1 w podfolderze
        assert window.act_process.isEnabled()
        assert window._left_stack.currentIndex() == 1  # tabela widoczna
        # plik .txt pominięty
        names = [window.table.item(r, 0).text() for r in range(window.table.rowCount())]
        assert "notatka.txt" not in names

    def test_duplikaty_nie_sa_dodawane(self, window: MainWindow, docs_dir: Path) -> None:
        window._add_documents([docs_dir])
        count = window.table.rowCount()
        window._add_documents([docs_dir])
        assert window.table.rowCount() == count

    def test_wiersz_wyniku_podpisany(self, window: MainWindow, docs_dir: Path) -> None:
        window._add_documents([docs_dir])
        result = DocumentResult(
            path=window._files[0],
            status=DocumentStatus.OK,
            title="Umowa najmu",
            findings=[
                SignatureFinding(
                    kind=SignatureKind.HANDWRITTEN, page=1, confidence=88, crop_png=_PNG
                )
            ],
            page_count=1,
            pages_analyzed=1,
        )
        window._on_file_done(0, result)
        assert window.table.item(0, 1).text() == "Umowa najmu"
        assert window.table.item(0, 2).text() == "PODPISANY (1)"
        assert window.table.item(0, 3).text() == "88%"
        assert window.table.item(0, 4).text() == "OK"

    def test_wiersz_wyniku_blad(self, window: MainWindow, docs_dir: Path) -> None:
        window._add_documents([docs_dir])
        result = DocumentResult(
            path=window._files[0], status=DocumentStatus.ERROR, error="zepsuty plik"
        )
        window._on_file_done(0, result)
        assert window.table.item(0, 4).text() == "Błąd"
        assert window.table.item(0, 4).toolTip() == "zepsuty plik"

    def test_panel_szczegolow_z_wycinkiem(self, window: MainWindow, docs_dir: Path) -> None:
        window._add_documents([docs_dir])
        result = DocumentResult(
            path=window._files[0],
            status=DocumentStatus.OK,
            title="Protokół",
            findings=[
                SignatureFinding(kind=SignatureKind.STAMP, page=2, confidence=75, crop_png=_PNG)
            ],
            page_count=2,
            pages_analyzed=2,
        )
        window._on_file_done(0, result)
        window.table.selectRow(0)
        texts = _collect_labels(window)
        assert any("Protokół" in t for t in texts)
        assert any("pieczątka" in t.lower() for t in texts)
        assert any("75%" in t for t in texts)

    def test_wyczysc(self, window: MainWindow, docs_dir: Path) -> None:
        window._add_documents([docs_dir])
        window._on_clear()
        assert window.table.rowCount() == 0
        assert window._files == []
        assert window._left_stack.currentIndex() == 0

    def test_plakietka_online_ukryta_dla_ollamy(self, window: MainWindow) -> None:
        assert not window.online_badge.isVisibleTo(window)

    def test_plakietka_online_widoczna_dla_chmury(self, qtbot, isolated_config) -> None:  # type: ignore[no-untyped-def]
        from signum.config import AppConfig

        config = AppConfig()
        config.provider = "openai"
        config.save()
        win = MainWindow()
        qtbot.addWidget(win)
        assert win.online_badge.isVisibleTo(win)

    def test_plakietka_online_widoczna_dla_zdalnej_ollamy(self, qtbot, isolated_config) -> None:  # type: ignore[no-untyped-def]
        from signum.config import AppConfig

        config = AppConfig(ollama_url="https://ollama.example.test")
        config.save()
        win = MainWindow()
        qtbot.addWidget(win)
        assert win.online_badge.isVisibleTo(win)

    def test_jedno_ostrzezenie_przed_cala_partia(
        self, window: MainWindow, docs_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        window._add_documents([docs_dir])
        calls = 0

        def reject_risk() -> bool:
            nonlocal calls
            calls += 1
            return False

        monkeypatch.setattr(window, "_confirm_batch_risk", reject_risk)

        window._start_batch(create_vision_model(window._config))

        assert calls == 1
        assert len(window._files) == 5
        assert window._worker is None


class TestSettingsDialog:
    def test_wczytuje_i_zbiera_konfiguracje(self, qtbot, isolated_config) -> None:  # type: ignore[no-untyped-def]
        from signum.config import AppConfig

        config = AppConfig.load()
        dialog = SettingsDialog(config)
        qtbot.addWidget(dialog)
        assert dialog.provider_combo.currentData() == "ollama"
        assert dialog.ollama_model.currentText() == "gemma4:12b"

        dialog.max_pages.setValue(42)
        collected = dialog._collect_config()
        assert collected.max_pages_per_doc == 42
        assert config.max_pages_per_doc != 42

    def test_zmiana_dostawcy_przelacza_strone(self, qtbot, isolated_config) -> None:  # type: ignore[no-untyped-def]
        from signum.config import AppConfig

        dialog = SettingsDialog(AppConfig.load())
        qtbot.addWidget(dialog)
        dialog.provider_combo.setCurrentIndex(1)  # openai
        assert dialog.stack.currentIndex() == 1
        assert dialog._collect_config().provider == "openai"

    def test_prompt_programu_domyslny_i_wlasny(self, qtbot, isolated_config) -> None:  # type: ignore[no-untyped-def]
        from signum.ai.prompts import PROMPT_INSTRUCTIONS
        from signum.config import AppConfig

        dialog = SettingsDialog(AppConfig.load())
        qtbot.addWidget(dialog)
        assert dialog.prompt_edit.toPlainText() == PROMPT_INSTRUCTIONS
        # Domyślna treść jest zapisywana jako pusta (= podążaj za aktualizacjami).
        assert dialog._collect_config().custom_prompt == ""
        dialog.prompt_edit.setPlainText("Szukaj też adnotacji przy słowie Podpis.")
        assert dialog._collect_config().custom_prompt == "Szukaj też adnotacji przy słowie Podpis."

    def test_zbyt_dlugi_prompt_jest_odrzucany(self, qtbot, isolated_config) -> None:  # type: ignore[no-untyped-def]
        from signum.config import AppConfig

        dialog = SettingsDialog(AppConfig.load())
        qtbot.addWidget(dialog)
        dialog.prompt_edit.setPlainText("x" * 20_001)

        with pytest.raises(ValueError):
            dialog._collect_config()

    def test_num_ctx_wczytanie_i_zapis(self, qtbot, isolated_config) -> None:  # type: ignore[no-untyped-def]
        from signum.config import AppConfig

        config = AppConfig.load()
        config.ollama_num_ctx = 16384
        dialog = SettingsDialog(config)
        qtbot.addWidget(dialog)
        assert dialog.ollama_num_ctx.value() == 16384
        dialog.ollama_num_ctx.setValue(32768)
        assert dialog._collect_config().ollama_num_ctx == 32768


class TestOnlineWarningDialog:
    def test_odliczanie_odblokowuje_przycisk(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        dialog = OnlineWarningDialog()
        qtbot.addWidget(dialog)
        assert not dialog.accept_button.isEnabled()
        assert "(3)" in dialog.accept_button.text()
        for _ in range(dialog.COUNTDOWN_S):
            dialog._tick()
        assert dialog.accept_button.isEnabled()
        assert dialog.accept_button.text() == "Rozumiem zagrożenie"


class TestBatchRiskDialog:
    def test_wymaga_wszystkich_trzech_potwierdzen(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        from signum.config import AppConfig

        dialog = BatchRiskDialog(AppConfig(), 12)
        qtbot.addWidget(dialog)

        assert not dialog.accept_button.isEnabled()
        assert "12 dokumentów" in _dialog_text(dialog)
        assert "Tryb lokalny" in _dialog_text(dialog)

        dialog.rights_ack.setChecked(True)
        dialog.result_ack.setChecked(True)
        assert not dialog.accept_button.isEnabled()
        dialog.processing_ack.setChecked(True)
        assert dialog.accept_button.isEnabled()

    def test_tryb_online_ostrzega_o_wysylce(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        from signum.config import AppConfig

        config = AppConfig(provider="openai")
        dialog = BatchRiskDialog(config, 3)
        qtbot.addWidget(dialog)

        text = _dialog_text(dialog)
        assert "Tryb online" in text
        assert "zewnętrznego dostawcy AI" in text
        assert "opuszczą komputer" in dialog.processing_ack.text()

    def test_zdalna_ollama_jest_trybem_online(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        from signum.config import AppConfig

        config = AppConfig(ollama_url="https://ollama.example.test")
        dialog = BatchRiskDialog(config, 2)
        qtbot.addWidget(dialog)

        assert "Tryb zdalny" in _dialog_text(dialog)
        assert "opuszczą komputer" in dialog.processing_ack.text()


def _collect_labels(window: MainWindow) -> list[str]:
    from PySide6.QtWidgets import QLabel

    return [label.text() for label in window.details_container.findChildren(QLabel) if label.text()]


def _dialog_text(dialog: BatchRiskDialog) -> str:
    from PySide6.QtWidgets import QLabel

    return " ".join(label.text() for label in dialog.findChildren(QLabel))
