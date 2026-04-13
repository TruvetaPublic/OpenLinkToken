"""
Copyright (c) Truveta. All rights reserved.
"""

import os
import tempfile

import pytest

from openlinktoken_cli.io.parquet.token_parquet_reader import TokenParquetReader
from openlinktoken_cli.io.parquet.token_parquet_writer import TokenParquetWriter
from openlinktoken_cli.processor.token_constants import TokenConstants


class TestTokenParquetReader:
    """Test cases for TokenParquetReader."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".parquet", delete=False)
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()
        self.reader = None

    def teardown_method(self):
        """Clean up after each test method."""
        if self.reader:
            self.reader.close()
        if os.path.exists(self.temp_file_path):
            os.unlink(self.temp_file_path)

    def test_read_single_token(self):
        """Test reading a single token from Parquet."""
        writer = TokenParquetWriter(self.temp_file_path)
        data = {TokenConstants.RULE_ID: "T1", TokenConstants.TOKEN: "abc123token", TokenConstants.RECORD_ID: "rec-001"}
        writer.write_token(data)
        writer.close()

        self.reader = TokenParquetReader(self.temp_file_path)

        record = next(self.reader)

        assert record[TokenConstants.RULE_ID] == "T1"
        assert record[TokenConstants.TOKEN] == "abc123token"
        assert record[TokenConstants.RECORD_ID] == "rec-001"

        with pytest.raises(StopIteration):
            next(self.reader)

    def test_read_multiple_tokens(self):
        """Test reading multiple tokens from Parquet."""
        writer = TokenParquetWriter(self.temp_file_path)
        data1 = {TokenConstants.RULE_ID: "T1", TokenConstants.TOKEN: "token1", TokenConstants.RECORD_ID: "rec-001"}
        data2 = {TokenConstants.RULE_ID: "T2", TokenConstants.TOKEN: "token2", TokenConstants.RECORD_ID: "rec-002"}
        writer.write_token(data1)
        writer.write_token(data2)
        writer.close()

        self.reader = TokenParquetReader(self.temp_file_path)

        record1 = next(self.reader)
        assert record1[TokenConstants.RULE_ID] == "T1"
        assert record1[TokenConstants.TOKEN] == "token1"
        assert record1[TokenConstants.RECORD_ID] == "rec-001"

        record2 = next(self.reader)
        assert record2[TokenConstants.RULE_ID] == "T2"
        assert record2[TokenConstants.TOKEN] == "token2"
        assert record2[TokenConstants.RECORD_ID] == "rec-002"

        with pytest.raises(StopIteration):
            next(self.reader)

    def test_read_empty_token(self):
        """Test reading a token with empty value."""
        writer = TokenParquetWriter(self.temp_file_path)
        data = {TokenConstants.RULE_ID: "T1", TokenConstants.TOKEN: "", TokenConstants.RECORD_ID: "rec-001"}
        writer.write_token(data)
        writer.close()

        self.reader = TokenParquetReader(self.temp_file_path)

        record = next(self.reader)

        assert record[TokenConstants.RULE_ID] == "T1"
        assert record[TokenConstants.TOKEN] == ""
        assert record[TokenConstants.RECORD_ID] == "rec-001"

    def test_iterator_interface(self):
        """Test that reader works as an iterator."""
        writer = TokenParquetWriter(self.temp_file_path)
        data1 = {TokenConstants.RULE_ID: "T1", TokenConstants.TOKEN: "token1", TokenConstants.RECORD_ID: "rec-001"}
        data2 = {TokenConstants.RULE_ID: "T2", TokenConstants.TOKEN: "token2", TokenConstants.RECORD_ID: "rec-002"}
        writer.write_token(data1)
        writer.write_token(data2)
        writer.close()

        self.reader = TokenParquetReader(self.temp_file_path)

        count = 0
        for record in self.reader:
            count += 1
            assert TokenConstants.RULE_ID in record
            assert TokenConstants.TOKEN in record
            assert TokenConstants.RECORD_ID in record

        assert count == 2

    def test_nonexistent_file(self):
        """Test that nonexistent file raises error."""
        with pytest.raises(IOError):
            TokenParquetReader("/nonexistent/path/file.parquet")
