#!/usr/bin/env python3
"""Setup script for Open Link Token Core AI Python package."""

import os
import shutil

from setuptools import find_namespace_packages, setup
from setuptools.command.build_py import build_py

THIS_DIR = os.path.abspath(os.path.dirname(__file__))

# Shared inferencing assets live here (single source of truth alongside the Java resources)
INFERENCING_ASSETS_SRC = os.path.abspath(os.path.join(THIS_DIR, "../../../resources/inferencing/ml1"))
INFERENCING_ASSETS = ["model.onnx", "model.onnx.data", "tokenizer.json"]

# Target: openlinktoken/core/ai/tokens inside the built package tree
INFERENCING_ASSETS_PKG = os.path.join("openlinktoken", "core", "ai", "tokens")


class BuildWithInferencingAssets(build_py):
    """Copy shared ML1 inferencing assets into the package at wheel-build time.

    Mirrors what the Maven <resources> block does for the Java JAR — the files
    live once in resources/inferencing/ml1/ and are included in both artifacts
    during their respective build processes without duplicating them in source.
    """

    def run(self):
        """Build Python modules and copy shared ML1 assets into the package."""
        super().run()
        dst = os.path.join(self.build_lib, INFERENCING_ASSETS_PKG)
        os.makedirs(dst, exist_ok=True)
        for filename in INFERENCING_ASSETS:
            src_file = os.path.join(INFERENCING_ASSETS_SRC, filename)
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst)


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
    version="2.1.0",
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
    cmdclass={"build_py": BuildWithInferencingAssets},
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
