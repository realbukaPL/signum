"""Okno główne: kolejka plików, przetwarzanie z postępem i raport z wycinkami."""

from __future__ import annotations

import math
import time
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QSplitter,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from signum import APP_DISPLAY_NAME, __version__
from signum.ai import create_vision_model
from signum.ai.prompts import build_page_prompt
from signum.config import AppConfig, get_api_key
from signum.core.discovery import collect_documents
from signum.core.models import DocumentResult, DocumentStatus
from signum.core.pipeline import BatchResult, DocumentAnalyzer
from signum.report import write_csv, write_html
from signum.ui.settings_dialog import SettingsDialog
from signum.ui.worker import BatchWorker

_COL_FILE, _COL_TITLE, _COL_SIGNATURES, _COL_CONFIDENCE, _COL_STATUS = range(5)

_GREEN = QColor("#2e7d32")
_GRAY = QColor("#757575")
_RED = QColor("#c62828")
_BLUE = QColor("#1565c0")

_FILE_DIALOG_FILTER = (
    "Dokumenty (*.pdf *.jpg *.jpeg *.png *.tif *.tiff *.bmp *.webp);;Wszystkie pliki (*.*)"
)


class MainWindow(QMainWindow):
    """Główne okno aplikacji Signum."""

    def __init__(self) -> None:
        super().__init__()
        self._config = AppConfig.load()
        self._files: list[Path] = []
        self._results: dict[int, DocumentResult] = {}
        self._worker: BatchWorker | None = None
        self._last_batch: BatchResult | None = None
        self._batch_started = 0.0

        self.setWindowTitle(APP_DISPLAY_NAME)
        self.resize(1240, 800)
        self.setAcceptDrops(True)
        self._build_actions()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._update_action_states()

    # -- budowa UI ---------------------------------------------------------

    def _build_actions(self) -> None:
        self.act_add_files = QAction("Dodaj pliki…", self)
        self.act_add_files.triggered.connect(self._on_add_files)
        self.act_add_folder = QAction("Pracuj na folderze…", self)
        self.act_add_folder.triggered.connect(self._on_add_folder)
        self.act_process = QAction("Przetwórz", self)
        self.act_process.triggered.connect(self._on_process)
        self.act_cancel = QAction("Anuluj", self)
        self.act_cancel.triggered.connect(self._on_cancel)
        self.act_export = QAction("Zapisz raport…", self)
        self.act_export.triggered.connect(self._on_export)
        self.act_clear = QAction("Wyczyść", self)
        self.act_clear.triggered.connect(self._on_clear)
        self.act_settings = QAction("Ustawienia AI…", self)
        self.act_settings.triggered.connect(self._on_settings)
        self.act_about = QAction("O programie", self)
        self.act_about.triggered.connect(self._on_about)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Główne")
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        for action in (
            self.act_add_files,
            self.act_add_folder,
            None,
            self.act_process,
            self.act_cancel,
            None,
            self.act_export,
            self.act_clear,
            None,
            self.act_settings,
            self.act_about,
        ):
            if action is None:
                toolbar.addSeparator()
            else:
                toolbar.addAction(action)
        self.addToolBar(toolbar)

    def _build_central(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Lewa strona: podpowiedź (pusty stan) albo tabela wyników.
        left = QWidget()
        self._left_stack = QStackedLayout(left)

        hint = QLabel(
            "Przeciągnij tutaj pliki PDF lub skany\n(albo całe foldery)\n\n"
            "Możesz też użyć przycisków „Dodaj pliki…” i „Pracuj na folderze…”"
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #888; font-size: 15px; border: 2px dashed #bbb;")
        self._left_stack.addWidget(hint)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Plik", "Tytuł (AI)", "Podpisy", "Pewność", "Status"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(_COL_FILE, 240)
        self.table.setColumnWidth(_COL_TITLE, 250)
        self.table.setColumnWidth(_COL_SIGNATURES, 150)
        self.table.setColumnWidth(_COL_CONFIDENCE, 70)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self._left_stack.addWidget(self.table)

        splitter.addWidget(left)
        splitter.addWidget(self._build_details_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        self.setCentralWidget(splitter)

    def _build_details_panel(self) -> QWidget:
        self.details_scroll = QScrollArea()
        self.details_scroll.setWidgetResizable(True)
        self.details_container = QWidget()
        self.details_layout = QVBoxLayout(self.details_container)
        self.details_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.details_scroll.setWidget(self.details_container)
        self._show_details_placeholder()
        return self.details_scroll

    def _build_statusbar(self) -> None:
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(320)
        self.progress.setVisible(False)
        self.status_label = QLabel("Gotowy")
        self.online_badge = _OnlineBadge()
        self.statusBar().addWidget(self.status_label, 1)
        self.statusBar().addPermanentWidget(self.online_badge)
        self.statusBar().addPermanentWidget(self.progress)
        self._refresh_online_badge()

    def _refresh_online_badge(self) -> None:
        """Plakietka „model online" jest widoczna, gdy dostawca AI nie jest lokalny."""
        self.online_badge.setVisible(self._config.provider != "ollama")

    # -- drag & drop ---------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802 — API Qt
        if event.mimeData().hasUrls() and not self._is_processing():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802 — API Qt
        paths = [
            Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()
        ]
        if paths:
            self._add_documents(paths)

    # -- akcje użytkownika ---------------------------------------------------

    def _on_add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Wybierz dokumenty", self._config.last_dir, _FILE_DIALOG_FILTER
        )
        if files:
            self._remember_dir(Path(files[0]).parent)
            self._add_documents([Path(f) for f in files])

    def _on_add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Wybierz folder z dokumentami", self._config.last_dir
        )
        if folder:
            self._remember_dir(Path(folder))
            self._add_documents([Path(folder)])

    def _add_documents(self, paths: list[Path]) -> None:
        found = collect_documents(paths, recursive=self._config.recursive_folders)
        existing = set(self._files)
        new_files = [f for f in found if f not in existing]
        if not new_files:
            self.status_label.setText("Nie znaleziono nowych obsługiwanych dokumentów.")
            return
        for path in new_files:
            row = self.table.rowCount()
            self.table.insertRow(row)
            file_item = QTableWidgetItem(path.name)
            file_item.setToolTip(str(path))
            self.table.setItem(row, _COL_FILE, file_item)
            self.table.setItem(row, _COL_TITLE, QTableWidgetItem(""))
            self.table.setItem(row, _COL_SIGNATURES, QTableWidgetItem(""))
            self.table.setItem(row, _COL_CONFIDENCE, QTableWidgetItem(""))
            self.table.setItem(row, _COL_STATUS, QTableWidgetItem("Oczekuje"))
        self._files.extend(new_files)
        self._left_stack.setCurrentIndex(1)
        self.status_label.setText(f"W kolejce: {len(self._files)} plików.")
        self._update_action_states()

    def _on_process(self) -> None:
        if self._is_processing() or not self._files:
            return
        if not self._ensure_ai_ready():
            return
        try:
            model = create_vision_model(self._config)
        except ValueError as exc:
            QMessageBox.critical(self, "Ustawienia AI", str(exc))
            return
        analyzer = DocumentAnalyzer(
            model=model,
            max_pages=self._config.max_pages_per_doc,
            image_max_side=self._config.model_image_max_side,
            prompt=build_page_prompt(self._config.custom_prompt),
        )
        self._results.clear()
        self._last_batch = None
        for row in range(self.table.rowCount()):
            self._set_status_cell(row, "Oczekuje", _GRAY)
            self._cell(row, _COL_TITLE).setText("")
            self._cell(row, _COL_SIGNATURES).setText("")
            self._cell(row, _COL_CONFIDENCE).setText("")

        self._batch_started = time.monotonic()
        self.progress.setRange(0, len(self._files))
        self.progress.setValue(0)
        self.progress.setVisible(True)

        self._worker = BatchWorker(list(self._files), analyzer)
        self._worker.file_started.connect(self._on_file_started)
        self._worker.file_done.connect(self._on_file_done)
        self._worker.batch_done.connect(self._on_batch_done)
        self._worker.start()
        self._update_action_states()

    def _ensure_ai_ready(self) -> bool:
        """Dla dostawców chmurowych wymagany jest klucz API."""
        if self._config.provider in ("openai", "anthropic") and not get_api_key(
            self._config.provider
        ):
            answer = QMessageBox.question(
                self,
                "Brak klucza API",
                "Nie zapisano klucza API dla wybranego dostawcy.\n"
                "Otworzyć ustawienia AI?",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._on_settings()
            return False
        return True

    def _on_cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.status_label.setText("Anulowanie — czekam na zakończenie bieżącej strony…")
            self.act_cancel.setEnabled(False)

    def _on_clear(self) -> None:
        if self._is_processing():
            return
        self._files.clear()
        self._results.clear()
        self._last_batch = None
        self.table.setRowCount(0)
        self._left_stack.setCurrentIndex(0)
        self._show_details_placeholder()
        self.progress.setVisible(False)
        self.status_label.setText("Gotowy")
        self._update_action_states()

    def _on_settings(self) -> None:
        dialog = SettingsDialog(self._config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._config = AppConfig.load()
            self.status_label.setText("Zapisano ustawienia AI.")
        else:
            # Dialog mógł zmodyfikować obiekt konfiguracji (np. test połączenia)
            # bez zapisu — wracamy do stanu z dysku.
            self._config = AppConfig.load()
        self._refresh_online_badge()

    def _on_export(self) -> None:
        if self._last_batch is None:
            QMessageBox.information(
                self, "Raport", "Najpierw przetwórz dokumenty — raport powstaje z wyników."
            )
            return
        path_str, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Zapisz raport",
            str(Path(self._config.last_dir or ".") / "raport_podpisy.html"),
            "Raport HTML (*.html);;Raport CSV (*.csv)",
        )
        if not path_str:
            return
        path = Path(path_str)
        self._remember_dir(path.parent)
        try:
            if "CSV" in selected_filter or path.suffix.lower() == ".csv":
                write_csv(path, self._last_batch)
            else:
                write_html(path, self._last_batch)
        except OSError as exc:
            QMessageBox.critical(self, "Raport", f"Nie udało się zapisać raportu:\n{exc}")
            return
        self.status_label.setText(f"Zapisano raport: {path}")

    def _on_about(self) -> None:
        QMessageBox.about(
            self,
            "O programie",
            f"<b>{APP_DISPLAY_NAME}</b><br>wersja {__version__}<br><br>"
            "Wykrywa podpisy odręczne, parafki, pieczątki i podpisy cyfrowe "
            "w dokumentach PDF i skanach przy użyciu wizyjnych modeli AI "
            "(lokalnie przez Ollamę albo przez API chmurowe).<br><br>"
            "Program stwierdza wyłącznie <i>obecność</i> podpisów — nie weryfikuje "
            "ich ważności prawnej ani kryptograficznej.",
        )

    # -- zdarzenia wątku roboczego --------------------------------------------

    def _on_file_started(self, index: int, total: int, name: str) -> None:
        eta = self._format_eta(index, total)
        self.status_label.setText(f"Przetwarzanie {index + 1}/{total}: {name}{eta}")
        self._set_status_cell(index, "Analiza…", _BLUE)
        self.table.scrollToItem(self._cell(index, _COL_FILE))

    def _on_file_done(self, index: int, result: DocumentResult) -> None:
        self._results[index] = result
        self.progress.setValue(index + 1)
        self._fill_result_row(index, result)
        selected = self.table.currentRow()
        if selected == index:
            self._show_details(result)

    def _on_batch_done(self, batch: BatchResult) -> None:
        self._last_batch = batch
        self._worker = None
        self.progress.setValue(self.progress.maximum())
        summary = (
            f"Zakończono: {len(batch.results)} plików w {batch.duration_s:.0f} s — "
            f"z podpisami: {batch.signed_count}, błędy: {batch.error_count}."
        )
        self.status_label.setText(summary)
        # Uzupełnij wiersze anulowane (worker nie wysłał dla nich file_done).
        for index, result in enumerate(batch.results):
            if index not in self._results:
                self._results[index] = result
                self._fill_result_row(index, result)
        if batch.abort_error:
            QMessageBox.critical(
                self,
                "Przetwarzanie przerwane",
                f"Partia została przerwana z powodu błędu połączenia:\n\n{batch.abort_error}",
            )
        self._update_action_states()

    # -- pomocnicze ------------------------------------------------------------

    def _cell(self, row: int, col: int) -> QTableWidgetItem:
        item = self.table.item(row, col)
        if item is None:  # wiersze zawsze tworzymy z kompletem komórek
            raise RuntimeError(f"Brak komórki tabeli ({row}, {col})")
        return item

    def _fill_result_row(self, row: int, result: DocumentResult) -> None:
        if row >= self.table.rowCount():
            return
        self._cell(row, _COL_TITLE).setText(result.title)
        if result.status == DocumentStatus.OK:
            if result.is_signed:
                text = f"PODPISANY ({len(result.findings)})"
                color = _GREEN
            else:
                text = "BRAK PODPISU"
                color = _GRAY
            signatures_item = self._cell(row, _COL_SIGNATURES)
            signatures_item.setText(text)
            signatures_item.setForeground(color)
            confidence = result.max_confidence
            self._cell(row, _COL_CONFIDENCE).setText(
                f"{confidence}%" if confidence is not None else ""
            )
            self._set_status_cell(row, "OK", _GREEN)
        elif result.status == DocumentStatus.ERROR:
            self._set_status_cell(row, "Błąd", _RED)
            self._cell(row, _COL_STATUS).setToolTip(result.error or "")
        elif result.status == DocumentStatus.CANCELLED:
            self._set_status_cell(row, "Anulowano", _GRAY)

    def _set_status_cell(self, row: int, text: str, color: QColor) -> None:
        if row >= self.table.rowCount():
            return
        item = self._cell(row, _COL_STATUS)
        item.setText(text)
        item.setForeground(color)

    def _format_eta(self, done: int, total: int) -> str:
        if done == 0:
            return ""
        elapsed = time.monotonic() - self._batch_started
        remaining = elapsed / done * (total - done)
        minutes, seconds = divmod(int(remaining), 60)
        return f" (pozostało ok. {minutes}:{seconds:02d})"

    def _is_processing(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def _update_action_states(self) -> None:
        processing = self._is_processing()
        has_files = bool(self._files)
        self.act_add_files.setEnabled(not processing)
        self.act_add_folder.setEnabled(not processing)
        self.act_process.setEnabled(not processing and has_files)
        self.act_cancel.setEnabled(processing)
        self.act_clear.setEnabled(not processing and has_files)
        self.act_settings.setEnabled(not processing)
        self.act_export.setEnabled(self._last_batch is not None)

    def _remember_dir(self, directory: Path) -> None:
        self._config.last_dir = str(directory)
        self._config.save()

    # -- panel szczegółów --------------------------------------------------------

    def _on_selection_changed(self) -> None:
        row = self.table.currentRow()
        result = self._results.get(row)
        if result is None:
            self._show_details_placeholder()
        else:
            self._show_details(result)

    def _show_details_placeholder(self) -> None:
        self._clear_details()
        label = QLabel("Wybierz przetworzony plik, aby zobaczyć szczegóły i wycinki podpisów.")
        label.setWordWrap(True)
        label.setStyleSheet("color: #888;")
        self.details_layout.addWidget(label)

    def _show_details(self, result: DocumentResult) -> None:
        self._clear_details()
        title = QLabel(f"<h2>{result.title or result.path.name}</h2>")
        title.setWordWrap(True)
        self.details_layout.addWidget(title)
        path_label = QLabel(str(result.path))
        path_label.setWordWrap(True)
        path_label.setStyleSheet("color: #666; font-size: 11px;")
        self.details_layout.addWidget(path_label)

        if result.status == DocumentStatus.ERROR:
            error = QLabel(f"Błąd: {result.error}")
            error.setWordWrap(True)
            error.setStyleSheet("color: #c62828;")
            self.details_layout.addWidget(error)
            return
        if result.status == DocumentStatus.CANCELLED:
            self.details_layout.addWidget(QLabel("Plik pominięty (anulowano)."))
            return

        meta = QLabel(
            f"Przeanalizowano {result.pages_analyzed}/{result.page_count} stron "
            f"w {result.duration_s:.1f} s."
        )
        meta.setStyleSheet("color: #666;")
        self.details_layout.addWidget(meta)

        if not result.findings:
            none_label = QLabel("<b>Nie wykryto podpisów.</b>")
            self.details_layout.addWidget(none_label)
            return

        header = QLabel(f"<b>Wykryto: {result.kinds_summary}</b>")
        header.setWordWrap(True)
        self.details_layout.addWidget(header)
        for finding in result.findings:
            self.details_layout.addWidget(self._finding_widget(finding))

    def _finding_widget(self, finding) -> QWidget:  # type: ignore[no-untyped-def]
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(frame)
        caption = QLabel(
            f"<b>{finding.kind.label_pl.capitalize()}</b> — strona {finding.page}, "
            f"pewność {finding.confidence}%"
        )
        caption.setWordWrap(True)
        layout.addWidget(caption)
        if finding.detail:
            detail = QLabel(finding.detail)
            detail.setWordWrap(True)
            detail.setStyleSheet("color: #444; font-size: 11px;")
            layout.addWidget(detail)
        if finding.crop_png:
            pixmap = QPixmap()
            pixmap.loadFromData(finding.crop_png)
            crop_label = _ClickableLabel(pixmap)
            layout.addWidget(crop_label)
        else:
            layout.addWidget(QLabel("(brak wycinka — podpis niewidoczny lub błędna ramka)"))
        return frame

    def _clear_details(self) -> None:
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                # Odpięcie rodzica od razu — widget czekający na deleteLater
                # nie może malować się nad nową zawartością panelu.
                widget.setParent(None)
                widget.deleteLater()

    # -- zamknięcie okna -----------------------------------------------------------

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def] # noqa: N802 — API Qt
        if self._is_processing():
            answer = QMessageBox.question(
                self,
                "Trwa przetwarzanie",
                "Trwa analiza dokumentów. Przerwać i zamknąć program?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            if self._worker is not None:
                self._worker.cancel()
                self._worker.wait(10_000)
        event.accept()


class _ClickableLabel(QLabel):
    """Miniatura wycinka podpisu — kliknięcie otwiera podgląd 1:1."""

    clicked = Signal()

    def __init__(self, pixmap: QPixmap) -> None:
        super().__init__()
        self._full_pixmap = pixmap
        preview = pixmap
        if pixmap.width() > 380 or pixmap.height() > 140:
            preview = pixmap.scaled(
                380,
                140,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.setPixmap(preview)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Kliknij, aby powiększyć")
        self.setStyleSheet("border: 1px solid #ccc; background: white; padding: 2px;")

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def] # noqa: N802 — API Qt
        dialog = QDialog(self.window())
        dialog.setWindowTitle("Wycinek podpisu")
        layout = QVBoxLayout(dialog)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QLabel()
        inner.setPixmap(self._full_pixmap)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        dialog.resize(
            min(1000, self._full_pixmap.width() + 60),
            min(700, self._full_pixmap.height() + 60),
        )
        dialog.exec()
        super().mousePressEvent(event)


class _OnlineBadge(QFrame):
    """Plakietka ostrzegawcza: aktywny dostawca AI wysyła dane poza komputer."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("onlineBadge")
        self.setStyleSheet(
            "#onlineBadge { border: 2px solid #c62828; border-radius: 6px;"
            " background: #fff; }"
            "#onlineBadge QLabel { color: #c62828; font-weight: 600; border: none; }"
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 2, 8, 2)
        row.setSpacing(6)
        icon = QLabel()
        icon.setPixmap(_transfer_arrows_pixmap())
        row.addWidget(icon)
        row.addWidget(QLabel("Model online"))
        self.setToolTip(
            "Aktywny dostawca AI działa w chmurze — analizowane dokumenty "
            "są wysyłane przez internet poza ten komputer.\n"
            "Aby pracować w pełni lokalnie, wybierz Ollamę w ustawieniach AI."
        )


def _transfer_arrows_pixmap(size: int = 18) -> QPixmap:
    """Ikona wymiany danych: czerwona strzałka ↗ (wysyłka), niebieska ↙ (odbiór)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = float(size)
    _draw_arrow(painter, s * 0.25, s * 0.72, s * 0.90, s * 0.08, _RED)
    _draw_arrow(painter, s * 0.75, s * 0.28, s * 0.10, s * 0.92, _BLUE)
    painter.end()
    return pixmap


def _draw_arrow(
    painter: QPainter, x0: float, y0: float, x1: float, y1: float, color: QColor
) -> None:
    pen = QPen(color, 2.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))
    angle = math.atan2(y1 - y0, x1 - x0)
    head = 5.0
    for offset in (math.pi * 5 / 6, -math.pi * 5 / 6):  # grot: dwa skośne odcinki
        painter.drawLine(
            QPointF(x1, y1),
            QPointF(
                x1 + head * math.cos(angle + offset),
                y1 + head * math.sin(angle + offset),
            ),
        )


__all__ = ["MainWindow"]
