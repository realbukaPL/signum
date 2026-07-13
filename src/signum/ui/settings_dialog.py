"""Dialog ustawień AI i przetwarzania.

Klucze API są zapisywane w systemowym magazynie poświadczeń (keyring),
nigdy w pliku konfiguracyjnym.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from signum.ai import create_vision_model
from signum.config import AppConfig, get_api_key, set_api_key
from signum.ui.worker import ConnectionTestWorker, ModelListWorker

_PROVIDER_ORDER = ("ollama", "openai", "anthropic")
_PROVIDER_LABELS = {
    "ollama": "Ollama (model lokalny)",
    "openai": "OpenAI / API zgodne z OpenAI",
    "anthropic": "Claude (Anthropic)",
}


class SettingsDialog(QDialog):
    """Konfiguracja dostawcy AI, modelu i parametrów przetwarzania."""

    def __init__(self, config: AppConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._test_worker: ConnectionTestWorker | None = None
        self._models_worker: ModelListWorker | None = None
        self.setWindowTitle("Ustawienia AI")
        self.setMinimumWidth(520)
        self._build_ui()
        self._load_config()

    # -- budowa UI ---------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        provider_form = QFormLayout()
        self.provider_combo = QComboBox()
        for key in _PROVIDER_ORDER:
            self.provider_combo.addItem(_PROVIDER_LABELS[key], userData=key)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        provider_form.addRow("Dostawca AI:", self.provider_combo)
        layout.addLayout(provider_form)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_ollama_page())
        self.stack.addWidget(self._build_openai_page())
        self.stack.addWidget(self._build_anthropic_page())
        layout.addWidget(self.stack)

        test_row = QHBoxLayout()
        self.test_button = QPushButton("Testuj połączenie")
        self.test_button.clicked.connect(self._on_test_clicked)
        self.test_result = QLabel("")
        self.test_result.setWordWrap(True)
        test_row.addWidget(self.test_button)
        test_row.addWidget(self.test_result, stretch=1)
        layout.addLayout(test_row)

        layout.addWidget(self._build_processing_group())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Zapisz")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_ollama_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.ollama_url = QLineEdit()
        self.ollama_url.setPlaceholderText("http://localhost:11434")
        form.addRow("Adres Ollamy:", self.ollama_url)

        model_row = QHBoxLayout()
        self.ollama_model = QComboBox()
        self.ollama_model.setEditable(True)
        refresh = QPushButton("Odśwież listę")
        refresh.clicked.connect(self._on_refresh_models)
        model_row.addWidget(self.ollama_model, stretch=1)
        model_row.addWidget(refresh)
        form.addRow("Model:", model_row)
        form.addRow(
            "", QLabel("Model musi obsługiwać obrazy (np. gemma4:12b, llava, qwen-vl).")
        )
        return page

    def _build_openai_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.openai_base_url = QLineEdit()
        self.openai_base_url.setPlaceholderText("https://api.openai.com/v1")
        form.addRow("Adres API:", self.openai_base_url)
        self.openai_model = QLineEdit()
        self.openai_model.setPlaceholderText("gpt-4o")
        form.addRow("Model:", self.openai_model)
        self.openai_key = self._password_edit()
        form.addRow("Klucz API:", self._with_reveal(self.openai_key))
        return page

    def _build_anthropic_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.anthropic_model = QLineEdit()
        self.anthropic_model.setPlaceholderText("claude-sonnet-5")
        form.addRow("Model:", self.anthropic_model)
        self.anthropic_key = self._password_edit()
        form.addRow("Klucz API:", self._with_reveal(self.anthropic_key))
        return page

    def _build_processing_group(self) -> QGroupBox:
        group = QGroupBox("Przetwarzanie")
        form = QFormLayout(group)
        self.max_pages = QSpinBox()
        self.max_pages.setRange(1, 500)
        self.max_pages.setSuffix(" stron")
        form.addRow("Limit stron na dokument:", self.max_pages)

        self.image_side = QComboBox()
        for value in (768, 1024, 1120, 1400):
            self.image_side.addItem(f"{value} px", userData=value)
        form.addRow("Rozmiar obrazu dla modelu:", self.image_side)

        self.timeout = QSpinBox()
        self.timeout.setRange(30, 3600)
        self.timeout.setSuffix(" s")
        form.addRow("Limit czasu odpowiedzi:", self.timeout)

        self.recursive = QCheckBox("Przeszukuj podfoldery przy dodawaniu folderu")
        form.addRow("", self.recursive)
        return group

    @staticmethod
    def _password_edit() -> QLineEdit:
        edit = QLineEdit()
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        return edit

    @staticmethod
    def _with_reveal(edit: QLineEdit) -> QWidget:
        """Pole hasła z przyciskiem pokaż/ukryj."""
        wrapper = QWidget()
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        toggle = QPushButton("Pokaż")
        toggle.setCheckable(True)
        toggle.setFixedWidth(60)

        def on_toggle(checked: bool) -> None:
            edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
            toggle.setText("Ukryj" if checked else "Pokaż")

        toggle.toggled.connect(on_toggle)
        row.addWidget(edit, stretch=1)
        row.addWidget(toggle)
        return wrapper

    # -- konfiguracja ------------------------------------------------------

    def _load_config(self) -> None:
        cfg = self._config
        self.provider_combo.setCurrentIndex(_PROVIDER_ORDER.index(cfg.provider))
        self.stack.setCurrentIndex(_PROVIDER_ORDER.index(cfg.provider))
        self.ollama_url.setText(cfg.ollama_url)
        self.ollama_model.setEditText(cfg.ollama_model)
        self.openai_base_url.setText(cfg.openai_base_url)
        self.openai_model.setText(cfg.openai_model)
        self.anthropic_model.setText(cfg.anthropic_model)
        self.openai_key.setText(get_api_key("openai") or "")
        self.anthropic_key.setText(get_api_key("anthropic") or "")
        self.max_pages.setValue(cfg.max_pages_per_doc)
        index = self.image_side.findData(cfg.model_image_max_side)
        self.image_side.setCurrentIndex(index if index >= 0 else 2)
        self.timeout.setValue(cfg.timeout_s)
        self.recursive.setChecked(cfg.recursive_folders)

    def _collect_config(self) -> AppConfig:
        """Zbiera ustawienia z formularza (bez zapisywania)."""
        cfg = self._config
        cfg.provider = self.provider_combo.currentData()
        cfg.ollama_url = self.ollama_url.text().strip() or "http://localhost:11434"
        cfg.ollama_model = self.ollama_model.currentText().strip() or "gemma4:12b"
        cfg.openai_base_url = self.openai_base_url.text().strip() or "https://api.openai.com/v1"
        cfg.openai_model = self.openai_model.text().strip() or "gpt-4o"
        cfg.anthropic_model = self.anthropic_model.text().strip() or "claude-sonnet-5"
        cfg.max_pages_per_doc = self.max_pages.value()
        cfg.model_image_max_side = self.image_side.currentData()
        cfg.timeout_s = self.timeout.value()
        cfg.recursive_folders = self.recursive.isChecked()
        return cfg

    def _current_api_key(self) -> str:
        provider = self.provider_combo.currentData()
        if provider == "openai":
            return self.openai_key.text().strip()
        if provider == "anthropic":
            return self.anthropic_key.text().strip()
        return ""

    # -- akcje -------------------------------------------------------------

    def _on_provider_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.test_result.setText("")

    def _on_refresh_models(self) -> None:
        self.test_result.setText("Pobieranie listy modeli…")
        self._models_worker = ModelListWorker(self.ollama_url.text().strip())
        self._models_worker.finished_with_result.connect(self._on_models_loaded)
        self._models_worker.start()

    def _on_models_loaded(self, ok: bool, payload: object) -> None:
        if not ok:
            self.test_result.setText(str(payload))
            return
        models = list(payload)  # type: ignore[call-overload]
        current = self.ollama_model.currentText()
        self.ollama_model.clear()
        self.ollama_model.addItems(models)
        if current:
            self.ollama_model.setEditText(current)
        self.test_result.setText(f"Znaleziono {len(models)} modeli.")

    def _on_test_clicked(self) -> None:
        self.test_button.setEnabled(False)
        self.test_result.setText("Łączenie…")
        config = self._collect_config()
        model = create_vision_model(config, api_key=self._current_api_key())
        self._test_worker = ConnectionTestWorker(model)
        self._test_worker.finished_with_result.connect(self._on_test_finished)
        self._test_worker.start()

    def _on_test_finished(self, ok: bool, message: str) -> None:
        self.test_button.setEnabled(True)
        prefix = "✔ " if ok else "✘ "
        self.test_result.setText(prefix + message)
        color = "#2e7d32" if ok else "#c62828"
        self.test_result.setStyleSheet(f"color: {color};")

    def _on_save(self) -> None:
        config = self._collect_config()
        try:
            set_api_key("openai", self.openai_key.text().strip())
            set_api_key("anthropic", self.anthropic_key.text().strip())
        except Exception:
            QMessageBox.warning(
                self,
                "Magazyn poświadczeń",
                "Nie udało się zapisać klucza API w magazynie poświadczeń systemu.\n"
                "Klucz nie został zapisany — wprowadź go ponownie po restarcie.",
            )
        config.save()
        self.accept()

    # -- sprzątanie --------------------------------------------------------

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def] # noqa: N802 — API Qt
        for worker in (self._test_worker, self._models_worker):
            if worker is not None and worker.isRunning():
                worker.wait(100)
        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:  # type: ignore[no-untyped-def] # noqa: N802 — API Qt
        # Enter w polu tekstowym nie powinien zapisywać dialogu.
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return
        super().keyPressEvent(event)
