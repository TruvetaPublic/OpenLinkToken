"""
Copyright (c) Truveta. All rights reserved.
"""

import csv
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

MAPPING_FILE_SUFFIX = ".record-id-mapping.csv"
ORIGINAL_RECORD_ID = "original_record_id"
HASHED_RECORD_ID = "hashed_record_id"


class RecordIdMappingWriter:
    """
    Writes a record-ID mapping CSV file containing two columns:
    ``original_record_id`` and ``hashed_record_id``.

    Used when ``--hash-record-ids`` is specified on the ``tokenize`` or
    ``package`` subcommands, so that callers can reconcile hashed output back
    to their source records.
    """

    def __init__(self, file_path: str):
        """
        Open the mapping file for writing and emit the CSV header.

        Args:
            file_path: Path of the mapping CSV file to create.

        Raises:
            IOError: If the file cannot be opened for writing.
        """
        self.file_path = file_path
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        self._file_handle = open(file_path, "w", newline="", encoding="utf-8")
        self._csv_writer = csv.writer(self._file_handle, lineterminator="\n")
        self._csv_writer.writerow([ORIGINAL_RECORD_ID, HASHED_RECORD_ID])

    def write_mapping(self, original_record_id: str, hashed_record_id: str) -> None:
        """
        Write a mapping row to the CSV file.

        Args:
            original_record_id: The original record ID.
            hashed_record_id: The SHA-256 hash of the record ID.
        """
        self._csv_writer.writerow([original_record_id, hashed_record_id])

    def close(self) -> None:
        """Close the underlying file handle."""
        if self._file_handle:
            self._file_handle.close()

    def __enter__(self) -> "RecordIdMappingWriter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @staticmethod
    def build_mapping_file_path(output_file_path: str) -> str:
        """
        Build the mapping file path from an output file path by stripping the
        file extension and appending ``MAPPING_FILE_SUFFIX``.

        Args:
            output_file_path: The token output file path.

        Returns:
            The corresponding mapping file path.
        """
        output_dir = os.path.dirname(output_file_path)
        base_name = os.path.splitext(os.path.basename(output_file_path))[0]
        return os.path.join(output_dir, base_name + MAPPING_FILE_SUFFIX)
