# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

block_cipher = None

# Anchor to spec file location for reproducible builds
# Note: SPECPATH is provided by PyInstaller when executing the spec
base_dir = os.path.abspath(SPECPATH)
sys.path.insert(0, os.path.join(base_dir, "src", "main"))

from openlinktoken_cli.extension.core_runtime_inventory import write_core_runtime_inventory

# OLT_TARGET_ARCH allows callers to request a specific target architecture
# (e.g. "universal2" for macOS universal binaries) without passing --target-arch,
# which is invalid when a .spec file is used directly.
target_arch = os.environ.get("OLT_TARGET_ARCH") or None
core_ai_source = os.path.join(base_dir, "..", "openlinktoken-core-ai", "src", "main")
inferencing_assets_source = os.path.join(base_dir, "..", "..", "..", "resources", "inferencing", "ml1")

datas = []
binaries = []
hiddenimports = []

# Core-AI loads these dependencies lazily during ML1 inference, so collect them
# explicitly for frozen binaries.
for package_name in (
    "openlinktoken",
    "openlinktoken.core",
    "openlinktoken.core.ai",
    "pyarrow",
    "pandas",
    "csv2parquet",
    "cryptography",
    "tokenizers",
    "onnxruntime",
    "installer",
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

if sys.platform.startswith("linux"):
    nvidia_library_patterns = ["*.so", "*.so.*"]
    for package_name in (
        "nvidia.cublas",
        "nvidia.cuda_nvrtc",
        "nvidia.cuda_runtime",
        "nvidia.cudnn",
        "nvidia.cufft",
        "nvidia.curand",
        "nvidia.nvjitlink",
    ):
        binaries += collect_dynamic_libs(package_name, search_patterns=nvidia_library_patterns)

datas += [
    (os.path.join(inferencing_assets_source, filename), "openlinktoken/core/ai/tokens")
    for filename in ("asset-manifest.json", "model.onnx", "model.onnx.data", "tokenizer.json")
]

a = Analysis(
    [os.path.join(base_dir, "src", "main", "openlinktoken_cli", "main.py")],
    pathex=[
        base_dir,
        os.path.join(base_dir, "src", "main"),
        os.path.join(base_dir, "..", "openlinktoken", "src", "main"),
        core_ai_source,
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

inventory_path = Path(base_dir) / "build" / "core_runtime_inventory.json"
write_core_runtime_inventory(a.pure + a.binaries + a.datas, inventory_path)
a.datas += [
    (
        "openlinktoken_cli/data/core_runtime_inventory.json",
        str(inventory_path),
        "DATA",
    )
]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    name="olt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    exclude_binaries=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="olt",
)
