"""
Copyright (c) Truveta. All rights reserved.
"""

import csv
import logging
from typing import Dict, Type

from opentoken.attributes.attribute import Attribute
from opentoken.tokens.config.dynamic_attribute_factory import DynamicAttributeFactory
from opentoken.tokens.config.tokenization_config import TokenizationConfig
from opentoken_cli.io.person_attributes_reader import PersonAttributesReader


logger = logging.getLogger(__name__)


class ConfiguredPersonAttributesCSVReader(PersonAttributesReader):
    """Reads person attributes from a CSV file using a custom tokenization configuration.

    Unlike PersonAttributesCSVReader (which discovers column-to-attribute mappings via
    hardcoded aliases), this reader maps CSV columns to dynamic attribute classes
    explicitly defined in the tokenization config. This allows arbitrary CSV column
    names to be used without modifying any core attribute code.
    """

    def __init__(self, file_path: str, config: TokenizationConfig, factory: DynamicAttributeFactory):
        """Initialize the reader with the input CSV file and config-driven column mapping.

        Args:
            file_path: The input CSV file path.
            config: The parsed tokenization configuration.
            factory: The factory holding dynamic attribute classes keyed by CSV column name.

        Raises:
            IOError: If an I/O error occurs opening the file.
        """
        try:
            self.file_path = file_path
            self.file_handle = open(file_path, "r", encoding="utf-8")
            self.csv_reader = csv.DictReader(self.file_handle)
            self.iterator = iter(self.csv_reader)

            # Build the column → dynamic attribute class mapping from config
            self.attribute_map: Dict[str, Type[Attribute]] = {}
            for csv_column in config.attributes:
                try:
                    self.attribute_map[csv_column] = factory.get_class_for_csv_column(csv_column)
                except KeyError:
                    logger.warning(f"CSV column '{csv_column}' is in config but has no dynamic class registered.")

        except IOError as e:
            logger.error(f"Error opening CSV file: {e}")
            raise

    def __iter__(self):
        """Return the iterator object."""
        return self

    def __next__(self) -> Dict[Type[Attribute], str]:
        """Get the next record from the CSV file as a person attributes map.

        Returns:
            A dict mapping dynamic attribute classes to their raw string values from the row.
        """
        record = next(self.iterator)

        person_attributes: Dict[Type[Attribute], str] = {}
        for csv_column, attribute_class in self.attribute_map.items():
            value = record.get(csv_column)
            if value is not None:
                person_attributes[attribute_class] = value

        return person_attributes

    def close(self) -> None:
        """Close the CSV reader and file handle."""
        if self.file_handle:
            self.file_handle.close()
