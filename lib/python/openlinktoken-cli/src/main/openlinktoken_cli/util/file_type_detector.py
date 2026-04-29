# SPDX-License-Identifier: MIT

from pathlib import Path


class FileTypeDetector:
    """Detects file types based on file extensions."""

    TYPE_CSV = "csv"
    TYPE_PARQUET = "parquet"

    @staticmethod
    def detect_input_type(path: str) -> str:
        """Detect input file type from extension. Supports: csv, parquet."""
        suffix = Path(path).suffix.lower()
        if suffix == ".csv":
            return FileTypeDetector.TYPE_CSV
        if suffix == ".parquet":
            return FileTypeDetector.TYPE_PARQUET
        return ""

    @staticmethod
    def detect_output_type(path: str) -> str:
        """Detect output file type from extension. Supports: csv, parquet."""
        suffix = Path(path).suffix.lower()
        if suffix == ".csv":
            return FileTypeDetector.TYPE_CSV
        if suffix == ".parquet":
            return FileTypeDetector.TYPE_PARQUET
        return ""
