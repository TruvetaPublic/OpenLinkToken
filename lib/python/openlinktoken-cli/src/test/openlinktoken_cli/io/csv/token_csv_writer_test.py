"""
Copyright (c) Truveta. All rights reserved.
"""

import os
import tempfile

from openlinktoken_cli.io.csv.token_csv_writer import TokenCSVWriter
from openlinktoken_cli.processor.token_constants import TokenConstants


class TestTokenCSVWriter:
    """Test cases for TokenCSVWriter."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        self.temp_file_path = self.temp_file.name
        self.temp_file.close()
        self.writer = TokenCSVWriter(self.temp_file_path)

    def teardown_method(self):
        """Clean up after each test method."""
        if self.writer:
            self.writer.close()
        if os.path.exists(self.temp_file_path):
            os.unlink(self.temp_file_path)

    def test_write_single_token(self):
        """Test writing a single token to CSV."""
        data = {TokenConstants.RULE_ID: "T1", TokenConstants.TOKEN: "abc123token", TokenConstants.RECORD_ID: "rec-001"}

        self.writer.write_token(data)
        self.writer.close()

        with open(self.temp_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            header = lines[0].strip()
            assert header == "RuleId,Token,RecordId"

            record = lines[1].strip()
            assert record == "T1,abc123token,rec-001"

    def test_write_multiple_tokens(self):
        """Test writing multiple tokens to CSV."""
        data1 = {TokenConstants.RULE_ID: "T1", TokenConstants.TOKEN: "token1", TokenConstants.RECORD_ID: "rec-001"}

        data2 = {TokenConstants.RULE_ID: "T2", TokenConstants.TOKEN: "token2", TokenConstants.RECORD_ID: "rec-002"}

        self.writer.write_token(data1)
        self.writer.write_token(data2)
        self.writer.close()

        with open(self.temp_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            header = lines[0].strip()
            assert header == "RuleId,Token,RecordId"

            record1 = lines[1].strip()
            assert record1 == "T1,token1,rec-001"

            record2 = lines[2].strip()
            assert record2 == "T2,token2,rec-002"

    def test_header_written_only_once(self):
        """Test that header is written only once."""
        data1 = {TokenConstants.RULE_ID: "T1", TokenConstants.TOKEN: "token1", TokenConstants.RECORD_ID: "rec-001"}

        data2 = {TokenConstants.RULE_ID: "T2", TokenConstants.TOKEN: "token2", TokenConstants.RECORD_ID: "rec-002"}

        self.writer.write_token(data1)
        self.writer.write_token(data2)
        self.writer.close()

        with open(self.temp_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            header = lines[0].strip()
            assert header == "RuleId,Token,RecordId"

            record1 = lines[1].strip()
            assert record1 == "T1,token1,rec-001"

            record2 = lines[2].strip()
            assert record2 == "T2,token2,rec-002"

            # Ensure there are only 3 lines (header + 2 records)
            assert len(lines) == 3

    def test_write_token_with_blank_value(self):
        """Test writing a token with blank value."""
        data = {TokenConstants.RULE_ID: "T1", TokenConstants.TOKEN: "", TokenConstants.RECORD_ID: "rec-001"}

        self.writer.write_token(data)
        self.writer.close()

        with open(self.temp_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            header = lines[0].strip()
            assert header == "RuleId,Token,RecordId"

            record = lines[1].strip()
            assert record == "T1,,rec-001"
