#!/usr/bin/env python3
"""Setup script for OpenToken PySpark package."""

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
    long_description = "OpenToken PySpark bridge for distributed token generation."

# Core dependencies (version-agnostic, no PySpark)
core_requirements = [
    "opentoken==2.0.0-alpha",
    "pycryptodome>=3.18.0",
]

setup(
    name="opentoken-pyspark",
    version="2.0.0-alpha",
    author="Truveta",
    description="OpenToken PySpark bridge for distributed token generation",
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
    install_requires=core_requirements,
    extras_require={
        # Spark 4.1.x - Latest for Java 21
        # Note: PySpark 4.1+ requires pandas 2.0+
        "spark41": [
            "pyspark>=4.1.0,<4.2",
            "pyarrow>=17.0.0,<18.0",  # Upper bound to prevent future incompatibilities
            "pandas>=2.0.0,<2.4",  # PySpark 4.1+ requires pandas 2.0+
        ],
        # Spark 4.0.x - Recommended for Java 21
        # Note: PySpark 4.0+ requires pandas 2.0+
        "spark40": [
            "pyspark>=4.0.1,<4.1",
            "pyarrow>=17.0.0,<18.0",  # Upper bound to prevent future incompatibilities
            "pandas>=2.0.0,<2.4",  # PySpark 4.0+ requires pandas 2.0+
        ],
        # Spark 3.5.x - For Java 8-17 (NOT compatible with Java 21)
        "spark35": [
            "pyspark>=3.5.0,<3.6",
            "pyarrow>=15.0.0,<20",
            "pandas>=1.5,<2.3",  # Supports both pandas 1.x and 2.x
        ],
        # Spark 3.4.x - Legacy support
        "spark34": [
            "pyspark>=3.4.0,<3.5",
            "pyarrow>=10.0.0,<23",
            "pandas>=1.5,<2.2",  # Supports both pandas 1.x and 2.x
        ],
        # Development dependencies
        "dev": [
            "pytest",
            "pytest-cov",
            "flake8",
            "jupyter",
            "notebook",
            "ipykernel",
        ],
    },
    entry_points={},
)
