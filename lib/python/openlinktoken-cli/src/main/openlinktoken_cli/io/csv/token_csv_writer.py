# SPDX-License-Identifier: MIT

import csv
import logging
import os
from typing import Dict

from openlinktoken_cli.io.token_writer import TokenWriter
from openlinktoken_cli.processor.token_constants import TokenConstants

logger = logging.getLogger(__name__)


class TokenCSVWriter(TokenWriter):
    """Writes decrypted tokens to a CSV file.

    Parity notes (Java `TokenCSVWriter`):
    - Java uses a simple BufferedWriter and manual comma separation.
    - We use `csv.DictWriter` for safer quoting; order and header names match.
    - Added an explicit flush after each write to approximate Java's immediate write semantics.
    Output columns: RuleId, Token, RecordId
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
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else ".", exist_ok=True)

        self.file_handle = open(file_path, "w", newline="", encoding="utf-8")
        self.csv_writer = csv.DictWriter(
            self.file_handle,
            fieldnames=[TokenConstants.RULE_ID, TokenConstants.TOKEN, TokenConstants.RECORD_ID],
            lineterminator="\n",
        )
        self.csv_writer.writeheader()

    def write_token(self, data: Dict[str, str]) -> None:
        """Write a token row to the CSV file.

        Args:
            data: Dict containing RuleId, Token, RecordId (missing keys default to empty string).
        """
        try:
            self.csv_writer.writerow(
                {
                    TokenConstants.RULE_ID: data.get(TokenConstants.RULE_ID, ""),
                    TokenConstants.TOKEN: data.get(TokenConstants.TOKEN, ""),
                    TokenConstants.RECORD_ID: data.get(TokenConstants.RECORD_ID, ""),
                }
            )
            # Flush to keep behavior closer to Java's line-by-line writes
            self.file_handle.flush()
        except IOError as e:
            logger.error(f"Error in writing to CSV file: {e}")
            raise

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
