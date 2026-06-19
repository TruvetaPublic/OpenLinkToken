#!/usr/bin/env python3
"""Setup script for Open Link Token Python package."""

import os

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib

from setuptools import find_packages, setup

# Read the contents of the project README file.
this_directory = os.path.abspath(os.path.dirname(__file__))
root_readme = os.path.abspath(os.path.join(this_directory, "..", "..", "README.md"))
readme_path = root_readme if os.path.exists(root_readme) else os.path.join(this_directory, "README.md")
try:
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    # Fallback to a short description if README is unavailable
    long_description = "Open Link Token Python implementation for record linkage."

with open(os.path.join(this_directory, "pyproject.toml"), "rb") as f:
    project_config = tomllib.load(f).get("project", {})

requirements = project_config.get("dependencies", [])
optional_dependencies = project_config.get("optional-dependencies", {})

setup(
    name="openlinktoken",
    version="2.0.0-alpha",
    author="Open Link Token Contributors",
    description="Open Link Token Python core library for record linkage",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TruvetaPublic/OpenLinkToken",
    project_urls={
        "Source": "https://github.com/TruvetaPublic/OpenLinkToken",
        "Documentation": "https://github.com/TruvetaPublic/OpenLinkToken/blob/main/README.md",
    },
    package_dir={"": "src/main"},
    packages=find_packages(where="src/main"),
    python_requires=">=3.10",
    install_requires=requirements,
<<<<<<< HEAD
    extras_require=optional_dependencies,
=======
    extras_require={
        "dev": [
            "cryptography==48.0.1",
            "pycryptodome==3.23.0",
        ],
        "test": ["pytest==9.0.3"],
    },
>>>>>>> develop
)
