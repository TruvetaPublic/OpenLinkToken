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

    def __init__(self, file_path: str, attribute_map: Dict[str, object] | None = None):
        """
        Initialize the class with the input file in CSV format.

        Args:
            file_path: The input file path.
            attribute_map: Optional explicit mapping from CSV column name to output key
                (attribute class or logical field id). When omitted, mapping is discovered
                via attribute aliases.

        Raises:
            IOError: If an I/O error occurs.
        """
        try:
            self.file_path = file_path
            self.file_handle = open(file_path, "r", encoding="utf-8")
            self.csv_reader = csv.DictReader(self.file_handle)
            self.iterator = iter(self.csv_reader)
            if attribute_map is not None:
                self.attribute_map = attribute_map.copy()
            else:
                self.attribute_map = self._build_attribute_map_from_aliases()

        except IOError as e:
            logger.error(f"Error in reading CSV file: {e}")
            raise

    def row_count(self) -> int:
        """Return the total number of rows in the CSV file.

        Counts rows on first call and caches the result. After counting,
        seeks back to the beginning and rebuilds the iterator so downstream
        iteration (for / __next__) works correctly.
        """
        if hasattr(self, "_cached_row_count"):
            return self._cached_row_count

        count = 0
        self.file_handle.seek(0)
        next(self.file_handle, None)
        for _ in self.file_handle:
            count += 1

        self._cached_row_count = count
        self.file_handle.seek(0)
        self.csv_reader = csv.DictReader(self.file_handle)
        self.iterator = iter(self.csv_reader)
        return count

    def __iter__(self):
        """Return the iterator object."""
        return self

    def __next__(self) -> Dict[object, str]:
        """
        Get the next record from the CSV file.

        Returns:
            A person attributes map.
        """
        record = next(self.iterator)

        person_attributes: Dict[object, str] = {}
        for key, value in record.items():
            mapped_key = self.attribute_map.get(key)
            if mapped_key is not None:
                person_attributes[mapped_key] = value
            # else ignore attribute as it's not supported

        return person_attributes

    def close(self) -> None:
        """Close the CSV reader and file handle."""
        if self.file_handle:
            self.file_handle.close()

    def _build_attribute_map_from_aliases(self) -> Dict[str, Type[Attribute]]:
        """Build column-to-attribute mapping using AttributeLoader aliases."""
        alias_map: Dict[str, Type[Attribute]] = {}
        attributes: Set[Attribute] = AttributeLoader.load()
        for header_name in self.csv_reader.fieldnames or []:
            for attribute in attributes:
                for alias in attribute.get_aliases():
                    if header_name.lower() == alias.lower():
                        alias_map[header_name] = type(attribute)
                        break
        return alias_map
