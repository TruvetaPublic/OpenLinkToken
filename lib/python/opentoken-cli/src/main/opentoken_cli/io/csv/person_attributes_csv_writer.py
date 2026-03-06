"""
Copyright (c) Truveta. All rights reserved.
"""

import csv
import logging
import os
from typing import Dict

from opentoken_cli.io.person_attributes_writer import PersonAttributesWriter

logger = logging.getLogger(__name__)


class PersonAttributesCSVWriter(PersonAttributesWriter):
    """
    The PersonAttributeCSVWriter class is responsible for writing person
    attributes to a CSV file.
    It implements the PersonAttributesWriter interface.
    """

    def __init__(self, file_path: str):
        """
        Initialize the class with the output file in CSV format.

        Args:
            file_path: The output file path.

        Raises:
            IOError: If an I/O error occurs.
        """
        self.file_path = file_path

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        self.file_handle = open(file_path, "w", newline="", encoding="utf-8")
        self.csv_writer = csv.writer(self.file_handle, lineterminator="\n")
        self.header_written = False

    def write_attributes(self, data: Dict[str, str]) -> None:
        """
        Write attributes to the CSV file.

        Args:
            data: A map of person attributes.
        """
        try:
            if not self.header_written:
                # Write the header
                self.csv_writer.writerow(data.keys())
                self.header_written = True

            self.csv_writer.writerow(data.values())

        except IOError as e:
            logger.error(f"Error in writing CSV file: {e}")
            raise

    def close(self) -> None:
        """Close the CSV writer and file handle."""
        if self.file_handle:
            self.file_handle.close()
