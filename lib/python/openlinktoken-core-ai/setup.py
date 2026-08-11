#!/usr/bin/env python3
"""Setup script for Open Link Token Core AI Python package."""

import os
import shutil

from setuptools import find_namespace_packages, setup
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

THIS_DIR = os.path.abspath(os.path.dirname(__file__))

# The small manifest lives alongside the shared inferencing assets. Large model
# files are resolved lazily at runtime instead of being copied into Python wheels.
INFERENCING_ASSETS_SRC = os.path.abspath(os.path.join(THIS_DIR, "../../../resources/inferencing/ml1"))
INFERENCING_ASSETS = ["asset-manifest.json"]

# Target: openlinktoken/core/ai/tokens inside the built package tree
INFERENCING_ASSETS_PKG = os.path.join("openlinktoken", "core", "ai", "tokens")
INFERENCING_ASSETS_SOURCE_PKG = os.path.join("src", "main", INFERENCING_ASSETS_PKG)


def _find_manifest_source():
    """Find the manifest in the checkout or in an sdist's package source tree."""
    candidates = [
        os.path.join(INFERENCING_ASSETS_SRC, "asset-manifest.json"),
        os.path.join(THIS_DIR, INFERENCING_ASSETS_SOURCE_PKG, "asset-manifest.json"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError("ML1 asset-manifest.json is missing from resources and package source data.")


class BuildWithInferencingAssets(build_py):
    """Copy the small ML1 asset manifest into the package at wheel-build time.

    The model and tokenizer are intentionally not bundled in Python artifacts;
    the runtime downloads them on first use or resolves local CLI assets.
    """

    def run(self):
        """Build Python modules and copy the ML1 manifest into the package."""
        super().run()
        dst = os.path.join(self.build_lib, INFERENCING_ASSETS_PKG)
        os.makedirs(dst, exist_ok=True)
        for filename in INFERENCING_ASSETS:
            shutil.copy2(_find_manifest_source(), os.path.join(dst, filename))


class SdistWithInferencingManifest(sdist):
    """Stage the ML1 manifest inside source distributions for source installs."""

    def make_release_tree(self, base_dir, files):
        """Copy the manifest into the package source tree in the sdist."""
        super().make_release_tree(base_dir, files)
        dst = os.path.join(base_dir, INFERENCING_ASSETS_SOURCE_PKG)
        os.makedirs(dst, exist_ok=True)
        shutil.copy2(_find_manifest_source(), os.path.join(dst, "asset-manifest.json"))


# Read the contents of the project README file.
root_readme = os.path.abspath(os.path.join(THIS_DIR, "..", "..", "README.md"))
readme_path = root_readme if os.path.exists(root_readme) else os.path.join(THIS_DIR, "README.md")
try:
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "Open Link Token Core AI package for ML1/ONNX inference."

# Read requirements from requirements.txt
with open(os.path.join(THIS_DIR, "requirements.txt"), encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="openlinktoken-core-ai",
    version="2.1.1",
    author="Open Link Token Contributors",
    description="Open Link Token Core AI package for ML1/ONNX inference",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Truveta/OpenTokenPrivate",
    project_urls={
        "Source": "https://github.com/Truveta/OpenTokenPrivate",
        "Documentation": "https://github.com/Truveta/OpenTokenPrivate/blob/main/README.md",
    },
    package_dir={"": "src/main"},
    packages=find_namespace_packages(where="src/main"),
    package_data={
        "openlinktoken.core.ai.tokens": INFERENCING_ASSETS,
    },
    python_requires=">=3.10",
    install_requires=requirements,
    cmdclass={"build_py": BuildWithInferencingAssets, "sdist": SdistWithInferencingManifest},
    entry_points={
        "openlinktoken.inference_providers": [
            "ml1 = openlinktoken.core.ai.tokens.ml1_onnx_signature_provider:ML1OnnxSignatureProvider",
        ],
        "openlinktoken.tokens.definitions": [
            "ml1_token = openlinktoken.core.ai.tokens.ml1_token:ML1Token",
        ],
    },
    extras_require={
        "test": ["pytest==9.1.1"],
    },
)
