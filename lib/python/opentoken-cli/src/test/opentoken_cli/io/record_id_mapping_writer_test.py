"""
Copyright (c) Truveta. All rights reserved.
"""

from pathlib import Path

import pytest

from opentoken_cli.io.record_id_mapping_writer import RecordIdMappingWriter


class TestRecordIdMappingWriter:
    """Unit tests for RecordIdMappingWriter."""

    def test_creates_file_with_header(self, tmp_path: Path):
        """Mapping file must be created with the expected CSV header."""
        mapping_file = tmp_path / "output.record-id-mapping.csv"
        with RecordIdMappingWriter(str(mapping_file)) as writer:
            writer.write_mapping("original-001", "hashed-001")

        assert mapping_file.exists()
        lines = mapping_file.read_text().splitlines()
        assert lines[0] == "original_record_id,hashed_record_id"

    def test_contains_mapping_rows(self, tmp_path: Path):
        """Written rows must appear verbatim in the CSV file."""
        mapping_file = tmp_path / "output.record-id-mapping.csv"
        with RecordIdMappingWriter(str(mapping_file)) as writer:
            writer.write_mapping("record-001", "abc123")
            writer.write_mapping("record-002", "def456")

        lines = mapping_file.read_text().splitlines()
        assert len(lines) == 3, "File should have header + 2 data rows"
        assert lines[1] == "record-001,abc123"
        assert lines[2] == "record-002,def456"

    def test_build_mapping_file_path_strips_extension(self):
        """build_mapping_file_path must strip the file extension and append the suffix."""
        assert RecordIdMappingWriter.build_mapping_file_path("/path/to/output.csv") == \
            "/path/to/output.record-id-mapping.csv"
        assert RecordIdMappingWriter.build_mapping_file_path("/path/to/output.parquet") == \
            "/path/to/output.record-id-mapping.csv"

    def test_build_mapping_file_path_no_extension(self):
        """Files without an extension should still get the suffix appended."""
        result = RecordIdMappingWriter.build_mapping_file_path("noextension")
        assert result == "noextension.record-id-mapping.csv"

    def test_multiple_rows(self, tmp_path: Path):
        """Writing many rows should produce the correct number of lines."""
        mapping_file = tmp_path / "multi.record-id-mapping.csv"
        num_rows = 50
        with RecordIdMappingWriter(str(mapping_file)) as writer:
            for i in range(num_rows):
                writer.write_mapping(f"original-{i}", f"hashed-{i}")

        lines = mapping_file.read_text().splitlines()
        assert len(lines) == num_rows + 1, f"File should have header + {num_rows} rows"

    def test_context_manager_closes_file(self, tmp_path: Path):
        """The context manager must close the file after the with block."""
        mapping_file = tmp_path / "test.record-id-mapping.csv"
        with RecordIdMappingWriter(str(mapping_file)) as writer:
            writer.write_mapping("a", "b")
        # File handle should be closed; re-reading should succeed
        content = mapping_file.read_text()
        assert "a,b" in content
