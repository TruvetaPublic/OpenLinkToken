#!/usr/bin/env python3
"""Setup script for OpenToken CLI package."""

from setuptools import setup, find_packages
import os

# Read the contents of the project README file.
this_directory = os.path.abspath(os.path.dirname(__file__))
root_readme = os.path.abspath(os.path.join(this_directory, "..", "..", "..", "README.md"))
readme_path = root_readme if os.path.exists(root_readme) else os.path.join(this_directory, "README.md")
try:
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    # Fallback to a short description if README is unavailable
    long_description = "OpenToken CLI - Command line interface for person matching."

# Read requirements from requirements.txt
with open(os.path.join(this_directory, "requirements.txt"), encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="opentoken-cli",
    version="2.0.0-alpha",
    author="Truveta",
    description="OpenToken CLI - Command line interface for person matching",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Truveta/OpenToken",
    project_urls={
        "Source": "https://github.com/Truveta/OpenToken",
        "Documentation": "https://github.com/Truveta/OpenToken/blob/main/README.md",
    },
    package_dir={"": "src/main"},
    packages=find_packages(where="src/main"),
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
        ],
        "test": [
            "pytest"
        ],
    },
    entry_points={
        "console_scripts": [
            "opentoken=opentoken_cli.main:main",
        ],
    },
)
