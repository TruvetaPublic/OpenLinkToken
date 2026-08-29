"""Regression tests for the standalone PyInstaller specification."""

import runpy
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
    """The frozen bundle must include the lazily imported ML1 runtime packages."""
    collected_packages = []

    def collect_all(package_name):
        collected_packages.append(package_name)
        return [], [], []

    with patch("PyInstaller.utils.hooks.collect_all", side_effect=collect_all):
        runpy.run_path(
            str(SPEC_PATH),
            init_globals={
                "SPECPATH": str(SPEC_PATH.parent),
                "Analysis": lambda *args, **kwargs: _FakeAnalysis(),
                "PYZ": lambda *args, **kwargs: object(),
                "EXE": lambda *args, **kwargs: object(),
                "COLLECT": lambda *args, **kwargs: object(),
            },
        )

    assert {"tokenizers", "onnxruntime"}.issubset(collected_packages)
