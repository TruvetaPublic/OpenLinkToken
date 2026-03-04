"""
Copyright (c) Truveta. All rights reserved.
"""

import logging
import os
from typing import Dict, List

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    raise ImportError("pyarrow is required for Parquet support. Install with: pip install pyarrow")

from opentoken_cli.io.token_writer import TokenWriter
from opentoken_cli.processor.token_constants import TokenConstants

logger = logging.getLogger(__name__)


class TokenParquetWriter(TokenWriter):
    """
    Writes decrypted tokens to a Parquet file.
    Output columns: RuleId, Token, RecordId
    """

    def __init__(self, file_path: str):
        """
        Initialize the class with the output file in Parquet format.

        Args:
            file_path: The output file path.

        Raises:
            IOError: If an I/O error occurs.
        """
        self.file_path = file_path
        self.rows: List[Dict[str, str]] = []

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else ".", exist_ok=True)

    def write_token(self, data: Dict[str, str]) -> None:
        """
        Write a token row to the buffer (will be written to Parquet on close).

        Args:
            data: A dictionary with RuleId, Token, and RecordId.
        """
        self.rows.append(
            {
                TokenConstants.RULE_ID: data.get(TokenConstants.RULE_ID, ""),
                TokenConstants.TOKEN: data.get(TokenConstants.TOKEN, ""),
                TokenConstants.RECORD_ID: data.get(TokenConstants.RECORD_ID, ""),
            }
        )

    def close(self):
        """Write all buffered rows to the Parquet file."""
        if not self.rows:
            logger.warning("No rows to write to Parquet file")
            return

        try:
            # Create PyArrow table from the list of dictionaries
            table = pa.Table.from_pylist(self.rows)

            # Write to Parquet file
            # Use snappy compression to mirror Java implementation
            pq.write_table(table, self.file_path, compression="snappy")

        except Exception as e:
            logger.error(f"Error in writing to Parquet file: {e}")
            raise IOError(f"Failed to write Parquet file: {self.file_path}") from e

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
