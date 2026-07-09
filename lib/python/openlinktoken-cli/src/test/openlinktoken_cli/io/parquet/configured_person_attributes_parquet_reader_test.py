"""
Copyright (c) Truveta. All rights reserved.
"""

import os
import tempfile

import pytest

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    pytest.skip("PyArrow required for Parquet tests", allow_module_level=True)

from openlinktoken_cli.io.parquet.person_attributes_parquet_reader import PersonAttributesParquetReader
from openlinktoken_cli.tokens.config.configured_attribute_resolver import ConfiguredAttributeResolver
from openlinktoken_cli.tokens.config.tokenization_config import AttributeMappingEntry, TokenizationConfig


class TestConfiguredAttributeMappingInPersonAttributesParquetReader:
    """Test config-driven column mapping through the unified Parquet reader."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()

        self.config = TokenizationConfig(
            attributes={
                "given_nm": AttributeMappingEntry(field="FirstName", type="GivenName"),
                "family_nm": AttributeMappingEntry(field="FamilyName", type="LastName"),
            },
            token_rules={},
        )
        self.resolver = ConfiguredAttributeResolver(self.config)

    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_file_path):
            os.unlink(self.temp_file_path)

    def test_read_valid_parquet_with_configured_columns(self):
        """Reads configured columns into their corresponding field ids."""
        table = pa.table(
            {
                "given_nm": ["Maria"],
                "family_nm": ["Garcia"],
                "ignored": ["something"],
            }
        )
        pq.write_table(table, self.temp_file_path)

        attribute_map = {
            "given_nm": self.resolver.get_field_for_column("given_nm"),
            "family_nm": self.resolver.get_field_for_column("family_nm"),
        }

        with PersonAttributesParquetReader(self.temp_file_path, attribute_map=attribute_map) as reader:
            record = next(reader)

        assert record["FirstName"] == "Maria"
        assert record["FamilyName"] == "Garcia"
        assert len(record) == 2

    def test_parquet_mapping_is_case_insensitive(self):
        """Matches configured mappings even when Parquet column casing differs."""
        table = pa.table(
            {
                "Given_Nm": ["Maria"],
                "FAMILY_NM": ["Garcia"],
            }
        )
        pq.write_table(table, self.temp_file_path)

        attribute_map = {
            "given_nm": self.resolver.get_field_for_column("given_nm"),
            "family_nm": self.resolver.get_field_for_column("family_nm"),
        }

        with PersonAttributesParquetReader(self.temp_file_path, attribute_map=attribute_map) as reader:
            record = next(reader)

        assert record["FirstName"] == "Maria"
        assert record["FamilyName"] == "Garcia"

    def test_missing_configured_column_is_skipped(self):
        """Skips configured columns that are absent from the Parquet schema."""
        table = pa.table({"given_nm": ["Maria"]})
        pq.write_table(table, self.temp_file_path)

        attribute_map = {
            "given_nm": self.resolver.get_field_for_column("given_nm"),
            "family_nm": self.resolver.get_field_for_column("family_nm"),
        }

        with PersonAttributesParquetReader(self.temp_file_path, attribute_map=attribute_map) as reader:
            record = next(reader)

        assert record["FirstName"] == "Maria"
        assert "FamilyName" not in record
