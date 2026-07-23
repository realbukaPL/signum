"""Punkt wejścia aplikacji GUI."""

from __future__ import annotations

import ctypes
import logging
import sys
from importlib import resources

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from signum import APP_NAME, __version__
from signum.ui.main_window import MainWindow

_INSTANCE_MUTEX_NAME = "Local\\Signum-6D6C3F52-9C1B-4E6A-9A57-2B1FBD6A7E31"
_instance_mutex_handles: list[object] = []


def _load_icon() -> QIcon:
    try:
        icon_path = resources.files("signum.ui.resources") / "signum.ico"
        return QIcon(str(icon_path))
    except (FileNotFoundError, ModuleNotFoundError):
        return QIcon()


def main() -> int:
    """Uruchamia GUI Signum."""
    if "--self-test" in sys.argv:
        return _self_test()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(_load_icon())
    if not _acquire_instance_mutex():
        QMessageBox.information(
            None,
            APP_NAME,
            "Signum jest już uruchomione w tej sesji użytkownika.",
        )
        return 0
    window = MainWindow()
    window.show()
    return app.exec()


def _self_test() -> int:
    """Minimalny test spakowanego runtime'u używany podczas budowania instalatora."""
    import keyring  # noqa: PLC0415
    import pypdf  # noqa: PLC0415
    import pypdfium2  # noqa: PLC0415
    import requests  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    dependencies = (keyring, pypdf, pypdfium2, requests, Image)
    icon_path = resources.files("signum.ui.resources") / "signum.ico"
    try:
        keyring.get_password("Signum self-test", "missing-test-entry")
    except Exception:
        return 1
    return 0 if all(dependencies) and icon_path.is_file() else 1


def _acquire_instance_mutex() -> bool:
    """Tworzy mutex używany także przez instalator do wykrycia działającej aplikacji."""
    if sys.platform != "win32":
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_mutex = kernel32.CreateMutexW
    create_mutex.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    create_mutex.restype = ctypes.c_void_p
    handle = create_mutex(None, False, _INSTANCE_MUTEX_NAME)
    if not handle:
        logging.getLogger(__name__).warning("Nie udało się utworzyć mutexu aplikacji")
        return True
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return False
    _instance_mutex_handles.append(handle)
    return True


if __name__ == "__main__":
    sys.exit(main())
