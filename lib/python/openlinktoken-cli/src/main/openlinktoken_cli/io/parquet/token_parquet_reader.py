# SPDX-License-Identifier: MIT

import logging
from typing import Dict, Iterator

try:
    import pyarrow.parquet as pq
except ImportError:
    raise ImportError("pyarrow is required for Parquet support. Install with: uv pip install pyarrow")

from openlinktoken_cli.io.token_reader import TokenReader
from openlinktoken_cli.processor.token_constants import TokenConstants

logger = logging.getLogger(__name__)


class TokenParquetReader(TokenReader):
    """
    Reads encrypted tokens from a Parquet file for decryption.
    Expected columns: RuleId, Token, RecordId
    """

    def __init__(self, file_path: str):
        """
        Initialize the class with the input file in Parquet format.

        Args:
            file_path: The input file path.

        Raises:
            IOError: If an I/O error occurs.
        """
        try:
            self.file_path = file_path
            self.parquet_file = pq.ParquetFile(file_path)
            self.table = self.parquet_file.read()
            self.current_row = 0
            self.total_rows = len(self.table)

            # Validate required columns
            required_columns = {TokenConstants.RULE_ID, TokenConstants.TOKEN, TokenConstants.RECORD_ID}
            column_names = set(self.table.column_names)
            if not required_columns.issubset(column_names):
                missing = required_columns - column_names
                raise ValueError(f"Missing required columns: {missing}")

        except Exception as e:
            logger.error(f"Error in reading Parquet file: {e}")
            raise IOError(f"Failed to read Parquet file: {file_path}") from e

    def row_count(self) -> int:
        return self.total_rows

    def __iter__(self) -> Iterator[Dict[str, str]]:
        """
        Iterate over rows in the Parquet file.

        Returns:
            Iterator of dictionaries with RuleId, Token, and RecordId.
        """
        return self

    def __next__(self) -> Dict[str, str]:
        """
        Get the next row from the Parquet file.

        Returns:
            Dictionary with RuleId, Token, and RecordId.
        """
        if self.current_row >= self.total_rows:
            raise StopIteration

        row_dict = {}
        for column_name in self.table.column_names:
            value = self.table.column(column_name)[self.current_row].as_py()
            row_dict[column_name] = str(value) if value is not None else ""

        self.current_row += 1
        return row_dict

    def close(self):
        """Close the file handle."""
        # PyArrow ParquetFile doesn't need explicit closing
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
