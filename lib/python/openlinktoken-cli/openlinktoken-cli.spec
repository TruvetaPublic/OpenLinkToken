# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Anchor to spec file location for reproducible builds
# Note: SPECPATH is provided by PyInstaller when executing the spec
base_dir = os.path.abspath(SPECPATH)

# OLT_TARGET_ARCH allows callers to request a specific target architecture
# (e.g. "universal2" for macOS universal binaries) without passing --target-arch,
# which is invalid when a .spec file is used directly.
target_arch = os.environ.get("OLT_TARGET_ARCH") or None

datas = []
binaries = []
hiddenimports = []

for package_name in ("openlinktoken", "pyarrow", "pandas", "csv2parquet", "cryptography"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

# Standalone CLI binaries include ML1 assets so ML1 works without network access.
ml1_assets_dir = os.path.abspath(os.path.join(base_dir, "..", "..", "..", "resources", "inferencing", "ml1"))
ml1_package_dir = os.path.join("openlinktoken", "core", "ai", "tokens")
for asset_name in ("asset-manifest.json", "model.onnx", "model.onnx.data", "tokenizer.json"):
    datas.append((os.path.join(ml1_assets_dir, asset_name), ml1_package_dir))

a = Analysis(
    [os.path.join(base_dir, "src", "main", "openlinktoken_cli", "main.py")],
    pathex=[
        base_dir,
        os.path.join(base_dir, "src", "main"),
        os.path.join(base_dir, "..", "openlinktoken", "src", "main"),
    ],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    target_arch=target_arch,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="olt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)
