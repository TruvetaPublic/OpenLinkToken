import hashlib
import runpy
from pathlib import Path
from unittest.mock import patch

from setuptools import Distribution

SETUP_PATH = Path(__file__).parents[5] / "setup.py"
MANIFEST_PATH = SETUP_PATH.parents[3] / "resources" / "inferencing" / "ml1" / "asset-manifest.json"


def _load_setup_namespace():
    """Load setup helpers without executing a real package build."""
    with patch("setuptools.find_namespace_packages", return_value=[]), patch("setuptools.setup"):
        return runpy.run_path(str(SETUP_PATH))


def test_sdist_release_tree_contains_the_verified_manifest(tmp_path):
    """The sdist hook should stage the manifest inside the package source tree."""
    setup_namespace = _load_setup_namespace()
    command = setup_namespace["SdistWithInferencingManifest"](Distribution())

    command.make_release_tree(str(tmp_path), [])

    staged_manifest = tmp_path / "src" / "main" / "openlinktoken" / "core" / "ai" / "tokens" / "asset-manifest.json"
    assert staged_manifest.read_bytes() == MANIFEST_PATH.read_bytes()
    assert hashlib.sha256(staged_manifest.read_bytes()).digest() == hashlib.sha256(MANIFEST_PATH.read_bytes()).digest()
