# SPDX-License-Identifier: MIT

import logging
from typing import Dict, Set

try:
    import pyarrow.parquet as pq
except ImportError:
    raise ImportError("pyarrow is required for Parquet support. Install with: uv pip install pyarrow")

from openlinktoken.attributes.attribute import Attribute
from openlinktoken.attributes.attribute_loader import AttributeLoader
from openlinktoken_cli.io.person_attributes_reader import PersonAttributesReader

logger = logging.getLogger(__name__)


class PersonAttributesParquetReader(PersonAttributesReader):
    """
    Reads person attributes from a Parquet file.
    Implements the PersonAttributesReader interface.
    """

    def __init__(self, file_path: str, attribute_map: Dict[str, str] | None = None):
        """
        Initialize the class with the input file in Parquet format.

        Args:
            file_path: The input file path.
            attribute_map: Optional explicit mapping from input column name to field id.
                When omitted, mapping is discovered via built-in attribute aliases and each
                column is mapped to its canonical attribute name (e.g. "FirstName").

        Raises:
            IOError: If an I/O error occurs.
        """
        try:
            self.file_path = file_path
            self.parquet_file = pq.ParquetFile(file_path)
            self.total_rows = self.parquet_file.metadata.num_rows
            self.table = self.parquet_file.read()
            self.current_row = 0
            self.closed = False
            self.has_next_called = False
            self.has_next_result = False
            self._attribute_map: Dict[str, str] = {}
            if attribute_map is not None:
                self.attribute_map = attribute_map
            else:
                self.attribute_map = self._build_column_to_field_id_map()

        except Exception as e:
            logger.error(f"Error in reading Parquet file: {e}")
            raise IOError(f"Failed to read Parquet file: {file_path}") from e

    @property
    def attribute_map(self) -> Dict[str, str]:
        """Return the normalized input-column mapping for this reader."""
        return self._attribute_map

    @attribute_map.setter
    def attribute_map(self, value: Dict[str, str]) -> None:
        """Store column mappings using lowercase keys for case-insensitive lookups."""
        self._attribute_map = {column_name.lower(): field_id for column_name, field_id in value.items()}

    def __iter__(self):
        """Return the iterator object."""
        return self

    def has_next(self) -> bool:
        """
        Check if there are more records to read.

        Returns:
            True if there are more records, False otherwise.

        Raises:
            StopIteration: If the reader is closed.
        """
        if self.closed:
            raise StopIteration("Reader is closed")

        if not self.has_next_called:
            self.has_next_result = self.current_row < self.total_rows
            self.has_next_called = True

        return self.has_next_result

    def __next__(self) -> Dict[str, str]:
        """
        Get the next record from the Parquet file.

        Returns:
            A person attributes map keyed by field id.

        Raises:
            StopIteration: When there are no more records or reader is closed.
        """
        if self.closed:
            raise StopIteration("Reader is closed")

        if not self.has_next_called:
            if not self.has_next():
                raise StopIteration

        if not self.has_next_result:
            raise StopIteration

        self.has_next_called = False

        # Get the current row as a dictionary
        row_dict = {}
        for i, column_name in enumerate(self.table.schema.names):
            column = self.table.column(i)
            value = column[self.current_row].as_py()
            row_dict[column_name] = value

        self.current_row += 1

        # Map to field ids
        attributes: Dict[str, str] = {}
        for field_name, field_value in row_dict.items():
            field_id = self.attribute_map.get(field_name.lower())
            if field_id is not None:
                field_value_str = str(field_value) if field_value is not None else ""
                attributes[field_id] = field_value_str

        return attributes

    def row_count(self) -> int:
        """Return the total number of rows in the Parquet file."""
        return self.total_rows

    def close(self) -> None:
        """Close the Parquet reader and release resources."""
        self.closed = True
        # PyArrow handles resource cleanup automatically
        # No explicit file handle to close

    def _build_column_to_field_id_map(self) -> Dict[str, str]:
        """Build lowercase alias-to-field-id mapping from AttributeLoader."""
        field_id_map: Dict[str, str] = {}
        attributes: Set[Attribute] = AttributeLoader.load()
        for attribute in attributes:
            for alias in attribute.get_aliases():
                field_id_map[alias.lower()] = attribute.get_name()
        return field_id_map
