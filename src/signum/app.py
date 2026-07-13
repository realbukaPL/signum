"""Punkt wejścia aplikacji GUI."""

from __future__ import annotations

import logging
import sys
from importlib import resources

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from signum import APP_NAME, __version__
from signum.ui.main_window import MainWindow


def _load_icon() -> QIcon:
    try:
        icon_path = resources.files("signum.ui.resources") / "signum.ico"
        return QIcon(str(icon_path))
    except (FileNotFoundError, ModuleNotFoundError):
        return QIcon()


def main() -> int:
    """Uruchamia GUI Signum."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(_load_icon())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
