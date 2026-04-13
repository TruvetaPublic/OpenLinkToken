"""
Copyright (c) Truveta. All rights reserved.
"""

import os
import tempfile

import pytest

from openlinktoken_cli.io.csv.token_csv_reader import TokenCSVReader
from openlinktoken_cli.processor.token_constants import TokenConstants


class TestTokenCSVReader:
    """Test cases for TokenCSVReader."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
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
        """Test reading a single token from CSV."""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("RuleId,Token,RecordId\n")
            f.write("T1,abc123token,rec-001\n")

        self.reader = TokenCSVReader(self.temp_file_path)

        data = next(self.reader)

        assert data[TokenConstants.RULE_ID] == "T1"
        assert data[TokenConstants.TOKEN] == "abc123token"
        assert data[TokenConstants.RECORD_ID] == "rec-001"

        with pytest.raises(StopIteration):
            next(self.reader)

    def test_read_multiple_tokens(self):
        """Test reading multiple tokens from CSV."""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("RuleId,Token,RecordId\n")
            f.write("T1,token1,rec-001\n")
            f.write("T2,token2,rec-002\n")

        self.reader = TokenCSVReader(self.temp_file_path)

        data1 = next(self.reader)
        assert data1[TokenConstants.RULE_ID] == "T1"
        assert data1[TokenConstants.TOKEN] == "token1"
        assert data1[TokenConstants.RECORD_ID] == "rec-001"

        data2 = next(self.reader)
        assert data2[TokenConstants.RULE_ID] == "T2"
        assert data2[TokenConstants.TOKEN] == "token2"
        assert data2[TokenConstants.RECORD_ID] == "rec-002"

        with pytest.raises(StopIteration):
            next(self.reader)

    def test_read_empty_token(self):
        """Test reading a token with empty value."""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("RuleId,Token,RecordId\n")
            f.write("T1,,rec-001\n")

        self.reader = TokenCSVReader(self.temp_file_path)

        data = next(self.reader)

        assert data[TokenConstants.RULE_ID] == "T1"
        assert data[TokenConstants.TOKEN] == ""
        assert data[TokenConstants.RECORD_ID] == "rec-001"

    def test_missing_required_column(self):
        """Test that missing required column raises error."""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("RuleId,Token\n")
            f.write("T1,token1\n")

        with pytest.raises(ValueError, match="Missing required columns"):
            TokenCSVReader(self.temp_file_path)

    def test_empty_file(self):
        """Test that empty file raises error."""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("")

        with pytest.raises(ValueError, match="Missing required columns"):
            TokenCSVReader(self.temp_file_path)

    def test_iterator_interface(self):
        """Test that reader works as an iterator."""
        with open(self.temp_file_path, "w", encoding="utf-8") as f:
            f.write("RuleId,Token,RecordId\n")
            f.write("T1,token1,rec-001\n")
            f.write("T2,token2,rec-002\n")

        self.reader = TokenCSVReader(self.temp_file_path)

        count = 0
        for data in self.reader:
            count += 1
            assert TokenConstants.RULE_ID in data
            assert TokenConstants.TOKEN in data
            assert TokenConstants.RECORD_ID in data

        assert count == 2
