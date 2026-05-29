# SPDX-License-Identifier: MIT

from enum import Enum


class FileExtension(str, Enum):
    """Canonical file extensions supported by the Open Link Token CLI."""

    CSV = ".csv"
    PARQUET = ".parquet"
    ZIP = ".zip"
