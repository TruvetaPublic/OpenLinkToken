# SPDX-License-Identifier: MIT

import csv
import logging
from typing import Dict, Iterator

from openlinktoken_cli.io.token_reader import TokenReader
from openlinktoken_cli.processor.token_constants import TokenConstants

logger = logging.getLogger(__name__)


class TokenCSVReader(TokenReader):
    """
    Reads encrypted tokens from a CSV file for decryption.
    Expected columns: RuleId, Token, RecordId
    """

    def __init__(self, file_path: str):
        """
        Initialize the class with the input file in CSV format.

        Args:
            file_path: The input file path.

        Raises:
            IOError: If an I/O error occurs.
        """
        try:
            self.file_path = file_path
            self.file_handle = open(file_path, "r", encoding="utf-8")
            self.csv_reader = csv.DictReader(self.file_handle)

            # Validate required columns
            required_columns = {TokenConstants.RULE_ID, TokenConstants.TOKEN, TokenConstants.RECORD_ID}
            fieldnames = set(self.csv_reader.fieldnames or [])
            if not required_columns.issubset(fieldnames):
                missing = required_columns - fieldnames
                raise ValueError(f"Missing required columns: {missing}")

            self.iterator = iter(self.csv_reader)

        except IOError as e:
            logger.error(f"Error in reading CSV file: {e}")
            raise

    def __iter__(self) -> Iterator[Dict[str, str]]:
        """
        Iterate over rows in the CSV file.

        Returns:
            Iterator of dictionaries with RuleId, Token, and RecordId.
        """
        return self

    def __next__(self) -> Dict[str, str]:
        """
        Get the next row from the CSV file.

        Returns:
            Dictionary with RuleId, Token, and RecordId.
        """
        return next(self.iterator)

    def close(self):
        """Close the file handle."""
        if self.file_handle:
            self.file_handle.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
