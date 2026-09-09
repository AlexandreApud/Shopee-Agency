# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for Shopee Agency Pro.
Compiles standalone Windows executable with native windowing and zero console window.
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None
project_dir = Path(SPECPATH)


# Collect hidden modules
hidden_imports = [
    "sqlite3",
    "pandas",
    "openpyxl",
    "services",
    "database",
    "ui",
    "models",
    "config",
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.messagebox",
]
hidden_imports += collect_submodules("services")
hidden_imports += collect_submodules("database")
hidden_imports += collect_submodules("ui")

# Collect data files
datas = [
    (str(project_dir / "assets" / "icon.ico"), "assets"),
]
if (project_dir / "database" / "migrations").exists():
    datas.append((str(project_dir / "database" / "migrations"), "database/migrations"))

a = Analysis(
    [str(project_dir / "main.py")],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "notebook", "pytest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="ShopeeAgencyPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_dir / "assets" / "icon.ico"),
)

