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

from opentoken.attributes.general.record_id_attribute import RecordIdAttribute
from opentoken.attributes.person.first_name_attribute import FirstNameAttribute
from opentoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
from opentoken_cli.io.parquet.person_attributes_parquet_reader import PersonAttributesParquetReader
from opentoken_cli.io.parquet.person_attributes_parquet_writer import PersonAttributesParquetWriter


class TestPersonAttributesParquetReader:
    """Test cases for PersonAttributesParquetReader."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()

    def teardown_method(self):
        """Clean up after each test method."""
        if os.path.exists(self.temp_file_path):
            os.unlink(self.temp_file_path)

    def test_read_parquet(self):
        """Test reading a Parquet file."""
        with PersonAttributesParquetWriter(self.temp_file_path) as writer:
            record1 = {"RecordId": "1", "SocialSecurityNumber": "123-45-6789", "FirstName": "John"}
            writer.write_attributes(record1)

            record2 = {"RecordId": "2", "SocialSecurityNumber": "987-65-4321", "FirstName": "Jane"}
            writer.write_attributes(record2)

        with PersonAttributesParquetReader(self.temp_file_path) as reader:
            # Test first record
            first_record = next(reader)
            assert first_record[RecordIdAttribute] == "1"
            assert first_record[SocialSecurityNumberAttribute] == "123-45-6789"
            assert first_record[FirstNameAttribute] == "John"

            # Test second record
            second_record = next(reader)
            assert second_record[RecordIdAttribute] == "2"
            assert second_record[SocialSecurityNumberAttribute] == "987-65-4321"
            assert second_record[FirstNameAttribute] == "Jane"

            # Test no more records
            with pytest.raises(StopIteration):
                next(reader)

    def test_read_empty_parquet(self):
        """Test reading an empty Parquet file."""
        # Create an empty Parquet file
        schema = pa.schema(
            [
                ("BirthDate", pa.string()),
                ("Gender", pa.string()),
                ("FirstName", pa.string()),
                ("SocialSecurityNumber", pa.string()),
                ("RecordId", pa.string()),
                ("PostalCode", pa.string()),
                ("LastName", pa.string()),
            ]
        )

        empty_arrays = [pa.array([], type=field.type) for field in schema]
        table = pa.table(empty_arrays, schema=schema)
        pq.write_table(table, self.temp_file_path)

        with PersonAttributesParquetReader(self.temp_file_path) as reader:
            with pytest.raises(StopIteration):
                next(reader)

    def test_iterator_protocol(self):
        """Test iterator protocol."""
        with PersonAttributesParquetWriter(self.temp_file_path) as writer:
            record1 = {"RecordId": "1", "SocialSecurityNumber": "123-45-6789", "FirstName": "John"}
            writer.write_attributes(record1)

        with PersonAttributesParquetReader(self.temp_file_path) as reader:
            # Test that we can iterate
            for record in reader:
                assert record[RecordIdAttribute] == "1"
                assert record[SocialSecurityNumberAttribute] == "123-45-6789"
                assert record[FirstNameAttribute] == "John"
                break

    def test_next(self):
        """Test next method."""
        with PersonAttributesParquetWriter(self.temp_file_path) as writer:
            record1 = {"RecordId": "1", "SocialSecurityNumber": "123-45-6789", "FirstName": "John"}
            writer.write_attributes(record1)

        with PersonAttributesParquetReader(self.temp_file_path) as reader:
            record = next(reader)
            assert record is not None
            assert record[RecordIdAttribute] == "1"
            assert record[SocialSecurityNumberAttribute] == "123-45-6789"
            assert record[FirstNameAttribute] == "John"

    def test_close(self):
        """Test close method."""
        with PersonAttributesParquetWriter(self.temp_file_path) as writer:
            record1 = {"RecordId": "1", "SocialSecurityNumber": "123-45-6789", "FirstName": "John Doe"}
            writer.write_attributes(record1)

        reader = PersonAttributesParquetReader(self.temp_file_path)
        reader.close()

        # After closing, next should raise StopIteration
        with pytest.raises(StopIteration):
            next(reader)

    def test_constructor_throws_io_exception(self):
        """Test constructor throws IOError for non-existent file."""
        invalid_file_path = "non_existent_file.parquet"
        with pytest.raises(IOError):
            PersonAttributesParquetReader(invalid_file_path)
