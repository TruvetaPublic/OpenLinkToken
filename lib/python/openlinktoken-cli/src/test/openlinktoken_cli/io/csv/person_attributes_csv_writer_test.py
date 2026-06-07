# SPDX-License-Identifier: MIT

import os
import tempfile

from openlinktoken_cli.io.csv.person_attributes_csv_writer import PersonAttributesCSVWriter


class TestPersonAttributesCSVWriter:
    """Test cases for PersonAttributesCSVWriter."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()
        self.writer = PersonAttributesCSVWriter(self.temp_file_path)

    def teardown_method(self):
        """Clean up after each test method."""
        if self.writer:
            self.writer.close()
        if os.path.exists(self.temp_file_path):
            os.unlink(self.temp_file_path)

    def test_write_single_record(self):
        """Test writing a single record to CSV."""
        data = {"RecordId": "123", "Name": "John Doe", "SocialSecurityNumber": "123-45-6789"}

        self.writer.write_attributes(data)
        self.writer.close()

        with open(self.temp_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            header = lines[0].strip()
            assert header == "RecordId,Name,SocialSecurityNumber"

            record = lines[1].strip()
            assert record == "123,John Doe,123-45-6789"

    def test_write_multiple_records(self):
        """Test writing multiple records to CSV."""
        data1 = {"RecordId": "123", "Name": "John Doe", "SocialSecurityNumber": "123-45-6789"}

        data2 = {"RecordId": "456", "Name": "Jane Smith", "SocialSecurityNumber": "987-65-4321"}

        self.writer.write_attributes(data1)
        self.writer.write_attributes(data2)
        self.writer.close()

        with open(self.temp_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            header = lines[0].strip()
            assert header == "RecordId,Name,SocialSecurityNumber"

            record1 = lines[1].strip()
            assert record1 == "123,John Doe,123-45-6789"

            record2 = lines[2].strip()
            assert record2 == "456,Jane Smith,987-65-4321"

    def test_header_written_only_once(self):
        """Test that header is written only once."""
        data1 = {"RecordId": "123", "Name": "John Doe"}

        data2 = {"RecordId": "456", "Name": "Jane Smith"}

        self.writer.write_attributes(data1)
        self.writer.write_attributes(data2)
        self.writer.close()

        with open(self.temp_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            header = lines[0].strip()
            assert header == "RecordId,Name"

            record1 = lines[1].strip()
            assert record1 == "123,John Doe"

            record2 = lines[2].strip()
            assert record2 == "456,Jane Smith"

    def test_write_basename_output_path_in_current_directory(self, tmp_path, monkeypatch):
        """Test that a basename-only output path writes to the current directory."""
        monkeypatch.chdir(tmp_path)
        writer = PersonAttributesCSVWriter("output.csv")

        try:
            writer.write_attributes({"RecordId": "123", "Name": "John Doe"})
        finally:
            writer.close()

        output_path = tmp_path / "output.csv"
        assert output_path.exists()
