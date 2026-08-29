"""Regression tests for the standalone PyInstaller specification."""

import runpy
import sys
import types
from pathlib import Path
from unittest.mock import patch

SPEC_PATH = Path(__file__).parents[3] / "openlinktoken-cli.spec"


class _FakeAnalysis:
    """Minimal Analysis result needed to execute the spec in a unit test."""

    pure = ()
    zipped_data = ()
    scripts = ()
    binaries = ()
    zipfiles = ()
    datas = ()


def test_pyinstaller_spec_collects_ml1_runtime_dependencies():
    """The frozen bundle must wire ML1 dependencies and assets into Analysis."""
    collected_packages = []
    analysis_kwargs = {}

    def collect_all(package_name):
        collected_packages.append(package_name)
        return [f"{package_name}:data"], [f"{package_name}:binary"], [f"{package_name}:hidden"]

    def fake_analysis(*args, **kwargs):
        analysis_kwargs.update(kwargs)
        return _FakeAnalysis()

    fake_hooks = types.ModuleType("PyInstaller.utils.hooks")
    fake_hooks.collect_all = collect_all
    fake_utils = types.ModuleType("PyInstaller.utils")
    fake_utils.hooks = fake_hooks
    fake_pyinstaller = types.ModuleType("PyInstaller")
    fake_pyinstaller.utils = fake_utils

    with patch.dict(
        sys.modules,
        {
            "PyInstaller": fake_pyinstaller,
            "PyInstaller.utils": fake_utils,
            "PyInstaller.utils.hooks": fake_hooks,
        },
    ):
        runpy.run_path(
            str(SPEC_PATH),
            init_globals={
                "SPECPATH": str(SPEC_PATH.parent),
                "Analysis": fake_analysis,
                "PYZ": lambda *args, **kwargs: object(),
                "EXE": lambda *args, **kwargs: object(),
                "COLLECT": lambda *args, **kwargs: object(),
            },
        )

    assert {"tokenizers", "onnxruntime"}.issubset(collected_packages)
    assert {"tokenizers:data", "onnxruntime:data"}.issubset(analysis_kwargs["datas"])
    assert {"tokenizers:binary", "onnxruntime:binary"}.issubset(analysis_kwargs["binaries"])
    assert {"tokenizers:hidden", "onnxruntime:hidden"}.issubset(analysis_kwargs["hiddenimports"])

    repository_root = SPEC_PATH.parents[3]
    expected_asset_paths = {
        (
            str((repository_root / "resources" / "inferencing" / "ml1" / filename).resolve()),
            "openlinktoken/core/ai/tokens",
        )
        for filename in ("asset-manifest.json", "model.onnx", "model.onnx.data", "tokenizer.json")
    }
    actual_asset_paths = set()
    for data in analysis_kwargs["datas"]:
        if not isinstance(data, tuple) or len(data) != 2:
            continue
        source_path, destination = data
        if isinstance(source_path, str) and destination == "openlinktoken/core/ai/tokens":
            actual_asset_paths.add((str(Path(source_path).resolve()), destination))
    assert expected_asset_paths.issubset(actual_asset_paths)
