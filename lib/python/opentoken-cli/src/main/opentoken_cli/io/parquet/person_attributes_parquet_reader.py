"""
Copyright (c) Truveta. All rights reserved.
"""

import logging
from typing import Dict, Set, Type

try:
    import pyarrow.parquet as pq
except ImportError:
    raise ImportError("pyarrow is required for Parquet support. Install with: uv pip install pyarrow")

from opentoken.attributes.attribute import Attribute
from opentoken.attributes.attribute_loader import AttributeLoader
from opentoken_cli.io.person_attributes_reader import PersonAttributesReader

logger = logging.getLogger(__name__)


class PersonAttributesParquetReader(PersonAttributesReader):
    """
    Reads person attributes from a Parquet file.
    Implements the PersonAttributesReader interface.
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
            self.closed = False
            self.has_next_called = False
            self.has_next_result = False
            self.attribute_map: Dict[str, Attribute] = {}

            # Load attributes and build the mapping
            attributes: Set[Attribute] = AttributeLoader.load()
            for attribute in attributes:
                for alias in attribute.get_aliases():
                    self.attribute_map[alias.lower()] = attribute

        except Exception as e:
            logger.error(f"Error in reading Parquet file: {e}")
            raise IOError(f"Failed to read Parquet file: {file_path}") from e

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

    def __next__(self) -> Dict[Type[Attribute], str]:
        """
        Get the next record from the Parquet file.

        Returns:
            A person attributes map.

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

        # Map to attribute classes
        attributes: Dict[Type[Attribute], str] = {}
        for field_name, field_value in row_dict.items():
            attribute = self.attribute_map.get(field_name.lower())
            if attribute is not None:
                attribute_class = type(attribute)
                field_value_str = str(field_value) if field_value is not None else None
                attributes[attribute_class] = field_value_str

        return attributes

    def close(self) -> None:
        """Close the Parquet reader and release resources."""
        self.closed = True
        # PyArrow handles resource cleanup automatically
        # No explicit file handle to close
