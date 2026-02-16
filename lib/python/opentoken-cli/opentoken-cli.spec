# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# Anchor to spec file location for reproducible builds
base_dir = os.path.abspath(os.path.dirname(__file__))

datas = []
binaries = []
hiddenimports = []

for package_name in ("pyarrow", "pandas", "csv2parquet", "cryptography"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

hiddenimports += collect_submodules("opentoken.tokens.definitions")

a = Analysis(
    ["src/main/opentoken_cli/main.py"],
    pathex=[base_dir, os.path.join(base_dir, "src", "main")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
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
    name="opentoken",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)
