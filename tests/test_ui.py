"""Testy dymne GUI (pytest-qt, platforma offscreen)."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from signum.core.models import DocumentResult, DocumentStatus, SignatureFinding, SignatureKind
from signum.ui.main_window import MainWindow
from signum.ui.settings_dialog import SettingsDialog

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

    def test_zmiana_dostawcy_przelacza_strone(self, qtbot, isolated_config) -> None:  # type: ignore[no-untyped-def]
        from signum.config import AppConfig

        dialog = SettingsDialog(AppConfig.load())
        qtbot.addWidget(dialog)
        dialog.provider_combo.setCurrentIndex(1)  # openai
        assert dialog.stack.currentIndex() == 1
        assert dialog._collect_config().provider == "openai"


def _collect_labels(window: MainWindow) -> list[str]:
    from PySide6.QtWidgets import QLabel

    return [
        label.text()
        for label in window.details_container.findChildren(QLabel)
        if label.text()
    ]
