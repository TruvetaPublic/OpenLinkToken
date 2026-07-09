# SPDX-License-Identifier: MIT

import os
import tempfile

import pytest

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:
    pytest.skip("PyArrow required for Parquet tests", allow_module_level=True)

from openlinktoken_cli.io.parquet.person_attributes_parquet_reader import PersonAttributesParquetReader
from openlinktoken_cli.io.parquet.person_attributes_parquet_writer import PersonAttributesParquetWriter


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
            assert first_record["RecordId"] == "1"
            assert first_record["SocialSecurityNumber"] == "123-45-6789"
            assert first_record["FirstName"] == "John"

            # Test second record
            second_record = next(reader)
            assert second_record["RecordId"] == "2"
            assert second_record["SocialSecurityNumber"] == "987-65-4321"
            assert second_record["FirstName"] == "Jane"

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
                assert record["RecordId"] == "1"
                assert record["SocialSecurityNumber"] == "123-45-6789"
                assert record["FirstName"] == "John"
                break

    def test_next(self):
        """Test next method."""
        with PersonAttributesParquetWriter(self.temp_file_path) as writer:
            record1 = {"RecordId": "1", "SocialSecurityNumber": "123-45-6789", "FirstName": "John"}
            writer.write_attributes(record1)

        with PersonAttributesParquetReader(self.temp_file_path) as reader:
            record = next(reader)
            assert record is not None
            assert record["RecordId"] == "1"
            assert record["SocialSecurityNumber"] == "123-45-6789"
            assert record["FirstName"] == "John"

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

    def test_read_parquet_with_explicit_attribute_map(self):
        """Supports config-style explicit field id mappings for non-standard Parquet fields."""
        table = pa.table(
            {
                "member_id": ["A-1"],
                "given_nm": ["Ana"],
                "surname_txt": ["Lopez"],
            }
        )
        pq.write_table(table, self.temp_file_path)

        attribute_map = {
            "given_nm": "FirstName",
            "surname_txt": "LastName",
        }

        with PersonAttributesParquetReader(self.temp_file_path, attribute_map=attribute_map) as reader:
            record = next(reader)

        assert record["FirstName"] == "Ana"
        assert record["LastName"] == "Lopez"
        assert len(record) == 2

    def test_row_count_returns_total_rows(self):
        """Row counting should return the Parquet row total without breaking iteration."""
        with PersonAttributesParquetWriter(self.temp_file_path) as writer:
            writer.write_attributes({"RecordId": "1", "SocialSecurityNumber": "123-45-6789", "FirstName": "John"})
            writer.write_attributes({"RecordId": "2", "SocialSecurityNumber": "987-65-4321", "FirstName": "Jane"})

        with PersonAttributesParquetReader(self.temp_file_path) as reader:
            assert reader.row_count() == 2

            first_record = next(reader)
            assert first_record["RecordId"] == "1"
