"""
Copyright (c) Truveta. All rights reserved.
"""

import os
import tempfile

import pytest

from opentoken.tokens.config.dynamic_attribute_factory import DynamicAttributeFactory
from opentoken.tokens.config.tokenization_config import AttributeMappingEntry, TokenizationConfig
from opentoken_cli.io.csv.configured_person_attributes_csv_reader import ConfiguredPersonAttributesCSVReader


class TestConfiguredPersonAttributesCSVReader:
    """Test cases for ConfiguredPersonAttributesCSVReader."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()

        self.config = TokenizationConfig(
            attributes={
                "given_nm": AttributeMappingEntry(field="GivenName", type="GivenName"),
                "family_nm": AttributeMappingEntry(field="FamilyName", type="LastName"),
            },
            token_rules={},
        )
        self.factory = DynamicAttributeFactory(self.config)

    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_file_path):
            os.unlink(self.temp_file_path)

    def test_read_valid_csv_with_configured_columns(self):
        """Reads configured columns into their corresponding dynamic attribute classes."""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("given_nm,family_nm,ignored\n")
            f.write("Maria,Garcia,something\n")

        given_name_class = self.factory.get_class_for_csv_column("given_nm")
        family_name_class = self.factory.get_class_for_csv_column("family_nm")

        with ConfiguredPersonAttributesCSVReader(self.temp_file_path, self.config, self.factory) as reader:
            record = next(reader)

        assert record[given_name_class] == "Maria"
        assert record[family_name_class] == "Garcia"
        assert len(record) == 2

    def test_missing_configured_column_is_skipped(self):
        """Skips configured columns that are absent from the CSV header."""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("given_nm\n")
            f.write("Maria\n")

        family_name_class = self.factory.get_class_for_csv_column("family_nm")

        with ConfiguredPersonAttributesCSVReader(self.temp_file_path, self.config, self.factory) as reader:
            record = next(reader)

        assert family_name_class not in record

    def test_constructor_throws_io_exception(self):
        """Raises IOError for a missing CSV file path."""
        with pytest.raises(IOError):
            ConfiguredPersonAttributesCSVReader("non_existent_file.csv", self.config, self.factory)
