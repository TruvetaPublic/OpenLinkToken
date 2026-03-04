"""
Copyright (c) Truveta. All rights reserved.
"""

import os
import tempfile

import pytest

from opentoken_cli.io.parquet.token_parquet_reader import TokenParquetReader
from opentoken_cli.io.parquet.token_parquet_writer import TokenParquetWriter
from opentoken_cli.processor.token_constants import TokenConstants


class TestTokenParquetWriter:
    """Test cases for TokenParquetWriter."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".parquet", delete=False)
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()
        self.writer = TokenParquetWriter(self.temp_file_path)

    def teardown_method(self):
        """Clean up after each test method."""
        if self.writer:
            self.writer.close()
        if os.path.exists(self.temp_file_path):
            os.unlink(self.temp_file_path)

    def test_write_single_token(self):
        """Test writing a single token to Parquet."""
        data = {TokenConstants.RULE_ID: "T1", TokenConstants.TOKEN: "abc123token", TokenConstants.RECORD_ID: "rec-001"}

        self.writer.write_token(data)
        self.writer.close()

        reader = TokenParquetReader(self.temp_file_path)
        record = next(reader)

        assert record[TokenConstants.RULE_ID] == "T1"
        assert record[TokenConstants.TOKEN] == "abc123token"
        assert record[TokenConstants.RECORD_ID] == "rec-001"

        with pytest.raises(StopIteration):
            next(reader)

        reader.close()

    def test_write_multiple_tokens(self):
        """Test writing multiple tokens to Parquet."""
        data1 = {TokenConstants.RULE_ID: "T1", TokenConstants.TOKEN: "token1", TokenConstants.RECORD_ID: "rec-001"}

        data2 = {TokenConstants.RULE_ID: "T2", TokenConstants.TOKEN: "token2", TokenConstants.RECORD_ID: "rec-002"}

        self.writer.write_token(data1)
        self.writer.write_token(data2)
        self.writer.close()

        reader = TokenParquetReader(self.temp_file_path)

        record1 = next(reader)
        assert record1[TokenConstants.RULE_ID] == "T1"
        assert record1[TokenConstants.TOKEN] == "token1"
        assert record1[TokenConstants.RECORD_ID] == "rec-001"

        record2 = next(reader)
        assert record2[TokenConstants.RULE_ID] == "T2"
        assert record2[TokenConstants.TOKEN] == "token2"
        assert record2[TokenConstants.RECORD_ID] == "rec-002"

        with pytest.raises(StopIteration):
            next(reader)

        reader.close()

    def test_write_token_with_blank_value(self):
        """Test writing a token with blank value."""
        data = {TokenConstants.RULE_ID: "T1", TokenConstants.TOKEN: "", TokenConstants.RECORD_ID: "rec-001"}

        self.writer.write_token(data)
        self.writer.close()

        reader = TokenParquetReader(self.temp_file_path)
        record = next(reader)

        assert record[TokenConstants.RULE_ID] == "T1"
        assert record[TokenConstants.TOKEN] == ""
        assert record[TokenConstants.RECORD_ID] == "rec-001"

        reader.close()
