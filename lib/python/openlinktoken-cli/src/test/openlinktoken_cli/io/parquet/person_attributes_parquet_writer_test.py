# SPDX-License-Identifier: MIT

import os
import tempfile

from openlinktoken_cli.io.parquet.person_attributes_parquet_reader import PersonAttributesParquetReader
from openlinktoken_cli.io.parquet.person_attributes_parquet_writer import PersonAttributesParquetWriter


class TestPersonAttributesParquetWriter:
    """Test cases for PersonAttributesParquetWriter."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()
        self.writer = PersonAttributesParquetWriter(self.temp_file_path)

    def teardown_method(self):
        """Clean up after each test method."""
        if self.writer:
            self.writer.close()
        if os.path.exists(self.temp_file_path):
            os.unlink(self.temp_file_path)

    def test_write_single_record(self):
        """Test writing a single record to Parquet."""
        data = {"RecordId": "123", "FirstName": "John", "SocialSecurityNumber": "123-45-6789"}

        self.writer.write_attributes(data)
        self.writer.close()

        with PersonAttributesParquetReader(self.temp_file_path) as reader:
            record = next(reader)
            assert record is not None
            assert record["RecordId"] == "123"
            assert record["SocialSecurityNumber"] == "123-45-6789"
            assert record["FirstName"] == "John"

    def test_write_multiple_records(self):
        """Test writing multiple records to Parquet."""
        data1 = {"RecordId": "123", "FirstName": "John", "SocialSecurityNumber": "123-45-6789"}
        data2 = {"RecordId": "456", "FirstName": "Jane", "SocialSecurityNumber": "987-65-4321"}

        self.writer.write_attributes(data1)
        self.writer.write_attributes(data2)
        self.writer.close()

        with PersonAttributesParquetReader(self.temp_file_path) as reader:
            # Test first record
            record = next(reader)
            assert record is not None
            assert record["RecordId"] == "123"
            assert record["SocialSecurityNumber"] == "123-45-6789"
            assert record["FirstName"] == "John"

            # Test second record
            record = next(reader)
            assert record is not None
            assert record["RecordId"] == "456"
            assert record["SocialSecurityNumber"] == "987-65-4321"
            assert record["FirstName"] == "Jane"

    def test_write_basename_output_path_in_current_directory(self, tmp_path, monkeypatch):
        """Test that a basename-only output path writes to the current directory."""
        monkeypatch.chdir(tmp_path)
        writer = PersonAttributesParquetWriter("output.parquet")

        try:
            writer.write_attributes({"RecordId": "123", "FirstName": "John"})
        finally:
            writer.close()

        output_path = tmp_path / "output.parquet"
        assert output_path.exists()
