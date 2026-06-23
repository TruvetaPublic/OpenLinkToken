# SPDX-License-Identifier: MIT

import os
import tempfile

import pytest

from openlinktoken.attributes.general.record_id_attribute import RecordIdAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
from openlinktoken_cli.io.csv.person_attributes_csv_reader import PersonAttributesCSVReader


class TestPersonAttributesCSVReader:
    """Test cases for PersonAttributesCSVReader."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()

    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_file_path):
            os.unlink(self.temp_file_path)

    def test_read_valid_csv(self):
        """Test reading a valid CSV file."""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("RecordId,SocialSecurityNumber,FirstName,LastName\n")
            f.write("1,123-45-6789,John,Doe\n")
            f.write("2,987-65-4321,Jane,Smith\n")

        with PersonAttributesCSVReader(self.temp_file_path) as reader:
            # Test first record
            first_record = next(reader)
            assert first_record[RecordIdAttribute] == "1"
            assert first_record[SocialSecurityNumberAttribute] == "123-45-6789"
            assert first_record[FirstNameAttribute] == "John"
            assert first_record[LastNameAttribute] == "Doe"

            # Test second record
            second_record = next(reader)
            assert second_record[RecordIdAttribute] == "2"
            assert second_record[SocialSecurityNumberAttribute] == "987-65-4321"
            assert second_record[FirstNameAttribute] == "Jane"
            assert second_record[LastNameAttribute] == "Smith"

            # Test no more records
            with pytest.raises(StopIteration):
                next(reader)

    def test_read_empty_csv(self):
        """Test reading an empty CSV file."""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("RecordId,SocialSecurityNumber,Name\n")

        with PersonAttributesCSVReader(self.temp_file_path) as reader:
            with pytest.raises(StopIteration):
                next(reader)

    def test_iterator_protocol(self):
        """Test iterator protocol."""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("RecordId,SocialSecurityNumber,FirstName,LastName\n")
            f.write("1,123-45-6789,John,Doe\n")

        with PersonAttributesCSVReader(self.temp_file_path) as reader:
            # Test that we can iterate
            for record in reader:
                assert record[RecordIdAttribute] == "1"
                assert record[SocialSecurityNumberAttribute] == "123-45-6789"
                assert record[FirstNameAttribute] == "John"
                assert record[LastNameAttribute] == "Doe"
                break

    def test_next(self):
        """Test next method."""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("RecordId,SocialSecurityNumber,FirstName,LastName\n")
            f.write("1,123-45-6789,John,Doe\n")

        with PersonAttributesCSVReader(self.temp_file_path) as reader:
            record = next(reader)
            assert record is not None
            assert record[RecordIdAttribute] == "1"
            assert record[SocialSecurityNumberAttribute] == "123-45-6789"
            assert record[FirstNameAttribute] == "John"
            assert record[LastNameAttribute] == "Doe"

    def test_close(self):
        """Test close method."""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("RecordId,SocialSecurityNumber,Name\n")
            f.write("1,123-45-6789,John Doe\n")

        reader = PersonAttributesCSVReader(self.temp_file_path)
        reader.close()

        # After closing, next should raise StopIteration
        with pytest.raises(ValueError):
            next(reader)

    def test_constructor_throws_io_exception(self):
        """Test constructor throws IOError for non-existent file."""
        invalid_file_path = "non_existent_file.csv"
        with pytest.raises(IOError):
            PersonAttributesCSVReader(invalid_file_path)

    def test_row_count_preserves_iteration(self):
        """Counting rows should not prevent subsequent iteration."""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("RecordId,SocialSecurityNumber,FirstName,LastName\n")
            f.write("1,123-45-6789,John,Doe\n")
            f.write("2,987-65-4321,Jane,Smith\n")

        with PersonAttributesCSVReader(self.temp_file_path) as reader:
            assert reader.row_count() == 2

            first_record = next(reader)
            second_record = next(reader)

            assert first_record[RecordIdAttribute] == "1"
            assert second_record[RecordIdAttribute] == "2"
