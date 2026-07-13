# -*- mode: python ; coding: utf-8 -*-
"""Konfiguracja PyInstaller dla Signum (onedir, bez konsoli).

Budowanie (z katalogu głównego repozytorium):
    .venv\\Scripts\\pyinstaller packaging\\signum.spec --noconfirm
"""

from pathlib import Path

ROOT = Path(SPECPATH).parent  # katalog główny repozytorium

a = Analysis(
    [str(ROOT / "src" / "signum" / "app.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        (str(ROOT / "src" / "signum" / "ui" / "resources" / "signum.ico"), "signum/ui/resources"),
        (str(ROOT / "src" / "signum" / "ui" / "resources" / "signum.png"), "signum/ui/resources"),
    ],
    hiddenimports=[
        # Backend keyring dla Windows ładowany dynamicznie przez entry-points.
        "keyring.backends.Windows",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Nieużywane, ciężkie moduły Qt — mniejsza paczka.
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.Qt3DCore",
        "PySide6.QtMultimedia",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtPdf",
        "tkinter",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="Signum",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "src" / "signum" / "ui" / "resources" / "signum.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Signum",
)
