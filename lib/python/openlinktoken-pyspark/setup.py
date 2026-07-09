#!/usr/bin/env python3
"""Setup script for Open Link Token PySpark package."""

import os

from setuptools import find_packages, setup

# Read the contents of the project README file.
this_directory = os.path.abspath(os.path.dirname(__file__))
root_readme = os.path.abspath(os.path.join(this_directory, "..", "..", "..", "README.md"))
readme_path = root_readme if os.path.exists(root_readme) else os.path.join(this_directory, "README.md")
try:
    with open(readme_path, encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    # Fallback to a short description if README is unavailable
    long_description = "Open Link Token PySpark bridge for distributed token generation."

# Core dependencies (version-agnostic, no PySpark)
core_requirements = [
    "openlinktoken==2.0.0",
    "pycryptodome==3.23.0",
    "jwcrypto==1.5.8",
]

setup(
    name="openlinktoken-pyspark",
    version="2.0.0",
    author="Open Link Token Contributors",
    description="Open Link Token PySpark bridge for distributed token generation",
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
    install_requires=core_requirements,
    extras_require={
        # Spark 4.1.x - Latest for Java 21
        "spark41": [
            "pyspark==4.1.0",
            "pyarrow==24.0.0",
            "pandas==2.2.3; python_version < '3.11'",
            "pandas==3.0.3; python_version >= '3.11'",
        ],
        # Spark 4.0.x - Recommended for Java 21
        "spark40": [
            "pyspark==4.0.1",
            "pyarrow==24.0.0",
            "pandas==2.2.3; python_version < '3.11'",
            "pandas==3.0.3; python_version >= '3.11'",
        ],
        # Spark 3.5.x - For Java 8-17 (NOT compatible with Java 21)
        "spark35": [
            "pyspark==3.5.5",
            "pyarrow==19.0.0",
            "pandas==2.2.3; python_version < '3.11'",
            "pandas==3.0.3; python_version >= '3.11'",
            "setuptools==82.0.1; python_version >= '3.12'",
        ],
        # Spark 3.4.x - Legacy support
        "spark34": [
            "pyspark==3.4.4",
            "pyarrow==15.0.0",
            "pandas==2.1.4; python_version < '3.11'",
            "pandas==3.0.3; python_version >= '3.11'",
            "setuptools==82.0.1; python_version >= '3.12'",
        ],
        # Development dependencies
        "dev": [
            "pytest==9.1.1",
            "pytest-cov==7.1.0",
            "flake8==7.3.0",
            "jupyter==1.1.1",
            "notebook==7.6.0",
            "ipykernel==7.3.0",
        ],
    },
)
