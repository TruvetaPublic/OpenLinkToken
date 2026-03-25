#!/usr/bin/env python3
"""Setup script for OpenToken Core AI Python package."""

import os
import shutil

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py

THIS_DIR = os.path.abspath(os.path.dirname(__file__))

# Shared inferencing assets live here (single source of truth alongside the Java resources)
INFERENCING_ASSETS_SRC = os.path.abspath(os.path.join(THIS_DIR, "../../../resources/inferencing/t6"))
INFERENCING_ASSETS = ["model.onnx", "model.onnx.data", "tokenizer.json", "vocab.txt"]

# Target: opentoken_core_ai/tokens inside the built package tree
INFERENCING_ASSETS_PKG = os.path.join("opentoken_core_ai", "tokens")


class BuildWithInferencingAssets(build_py):
    """Copy shared T6 inferencing assets into the package at wheel-build time.

    Mirrors what the Maven <resources> block does for the Java JAR — the files
    live once in resources/inferencing/t6/ and are included in both artifacts
    during their respective build processes without duplicating them in source.
    """

    def run(self):
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
    long_description = "OpenToken Core AI package for T6/ONNX inference."

# Read requirements from requirements.txt
with open(os.path.join(THIS_DIR, "requirements.txt"), encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="opentoken-core-ai",
    version="2.0.0-alpha",
    author="Truveta",
    description="OpenToken Core AI package for T6/ONNX inference",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Truveta/OpenToken",
    project_urls={
        "Source": "https://github.com/Truveta/OpenToken",
        "Documentation": "https://github.com/Truveta/OpenToken/blob/main/README.md",
    },
    package_dir={"": "src/main"},
    packages=find_packages(where="src/main"),
    package_data={
        "opentoken_core_ai.tokens": INFERENCING_ASSETS,
    },
    python_requires=">=3.10",
    install_requires=requirements,
    cmdclass={"build_py": BuildWithInferencingAssets},
    entry_points={
        "opentoken.inference_providers": [
            "t6 = opentoken_core_ai.t6_signature_provider:OnnxT6SignatureProvider",
        ],
        "opentoken.tokens.definitions": [
            "t6_token = opentoken_core_ai.tokens.t6_token:T6Token",
        ],
    },
    extras_require={
        "test": ["pytest"],
    },
)
