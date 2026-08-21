#!/usr/bin/env python3
"""Setup script for Open Link Token Python package."""

import os

from setuptools import find_packages, setup

THIS_DIR = os.path.abspath(os.path.dirname(__file__))


# Read the contents of the project README file.
root_readme = os.path.abspath(os.path.join(THIS_DIR, "..", "..", "README.md"))
readme_path = root_readme if os.path.exists(root_readme) else os.path.join(THIS_DIR, "README.md")
try:
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "Open Link Token Python implementation for record linkage."
# Read requirements from requirements.txt
with open(os.path.join(THIS_DIR, "requirements.txt"), encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="openlinktoken",
    version="2.1.2",
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
    package_data={},
    python_requires=">=3.10",
    install_requires=requirements,
)
