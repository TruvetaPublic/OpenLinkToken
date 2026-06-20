# SPDX-License-Identifier: MIT

import csv
import logging
from typing import Dict, Set, Type

from openlinktoken.attributes.attribute import Attribute
from openlinktoken.attributes.attribute_loader import AttributeLoader
from openlinktoken_cli.io.person_attributes_reader import PersonAttributesReader

logger = logging.getLogger(__name__)


class PersonAttributesCSVReader(PersonAttributesReader):
    """
    Reads person attributes from a CSV file.
    Implements the PersonAttributesReader interface.
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
            self.iterator = iter(self.csv_reader)
            self.attribute_map: Dict[str, Attribute] = {}

            # Load attributes and build the mapping
            attributes: Set[Attribute] = AttributeLoader.load()
            for header_name in self.csv_reader.fieldnames or []:
                for attribute in attributes:
                    for alias in attribute.get_aliases():
                        if header_name.lower() == alias.lower():
                            self.attribute_map[header_name] = attribute
                            break

        except IOError as e:
            logger.error(f"Error in reading CSV file: {e}")
            raise

    @property
    def row_count(self) -> int:
        """Return the total number of rows in the CSV file.

        Counts rows on first call and caches the result. After counting,
        seeks back to the beginning and rebuilds the iterator so downstream
        iteration (for / __next__) works correctly.
        """
        if hasattr(self, '_cached_row_count'):
            return self._cached_row_count
        count = 0
        self.file_handle.seek(0)
        header = next(iter(self.file_handle))
        for _ in self.file_handle:
            count += 1
        self._cached_row_count = count
        # Restore state so downstream iteration produces rows
        self.file_handle.seek(0)
        self.csv_reader = csv.DictReader(self.file_handle)
        self.iterator = iter(self.csv_reader)
        return count

    def __iter__(self):
        """Return the iterator object."""
        return self

    def __next__(self) -> Dict[Type[Attribute], str]:
        """
        Get the next record from the CSV file.

        Returns:
            A person attributes map.
        """
        record = next(self.iterator)

        person_attributes: Dict[Type[Attribute], str] = {}
        for key, value in record.items():
            attribute = self.attribute_map.get(key)
            if attribute is not None:
                person_attributes[type(attribute)] = value
            # else ignore attribute as it's not supported

        return person_attributes

    def close(self) -> None:
        """Close the CSV reader and file handle."""
        if self.file_handle:
            self.file_handle.close()
