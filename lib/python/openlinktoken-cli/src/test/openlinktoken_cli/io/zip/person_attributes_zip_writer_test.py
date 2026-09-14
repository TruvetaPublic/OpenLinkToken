# SPDX-License-Identifier: MIT

import json
import zipfile
from pathlib import Path

import pytest

from openlinktoken_cli.io.zip.person_attributes_zip_writer import PersonAttributesZipWriter


class TestPersonAttributesZipWriter:
    """Unit tests for PersonAttributesZipWriter."""

    ROW_1 = {"RecordId": "001", "RuleId": "T1", "Token": "aabbcc"}
    ROW_2 = {"RecordId": "002", "RuleId": "T2", "Token": "ddeeff"}
    METADATA = {"Version": "1.0", "TotalRows": 2}

    def test_build_zip_creates_file(self, tmp_path: Path):
        """build_zip must create a ZIP file at the specified path."""
        zip_path = str(tmp_path / "output.zip")
        with PersonAttributesZipWriter(zip_path) as writer:
            writer.write_attributes(self.ROW_1)
            writer.build_zip(self.METADATA)

        assert Path(zip_path).exists()

    def test_zip_contains_csv_entry(self, tmp_path: Path):
        """The ZIP must contain a CSV entry named after the stem of the zip path."""
        zip_path = str(tmp_path / "output.zip")
        with PersonAttributesZipWriter(zip_path) as writer:
            writer.write_attributes(self.ROW_1)
            writer.write_attributes(self.ROW_2)
            writer.build_zip(self.METADATA)

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        assert "output.csv" in names

    def test_zip_contains_metadata_entry(self, tmp_path: Path):
        """The ZIP must contain a metadata JSON entry named after the stem of the zip path."""
        zip_path = str(tmp_path / "output.zip")
        with PersonAttributesZipWriter(zip_path) as writer:
            writer.write_attributes(self.ROW_1)
            writer.build_zip(self.METADATA)

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
        assert "output.metadata.json" in names

    def test_csv_content_has_header_and_rows(self, tmp_path: Path):
        """The CSV entry must have a header row followed by data rows."""
        zip_path = str(tmp_path / "output.zip")
        with PersonAttributesZipWriter(zip_path) as writer:
            writer.write_attributes(self.ROW_1)
            writer.write_attributes(self.ROW_2)
            writer.build_zip(self.METADATA)

        with zipfile.ZipFile(zip_path) as zf:
            lines = zf.read("output.csv").decode("utf-8").splitlines()

        assert lines[0] == "RecordId,RuleId,Token"
        assert lines[1] == "001,T1,aabbcc"
        assert lines[2] == "002,T2,ddeeff"

    def test_metadata_json_is_valid_and_matches(self, tmp_path: Path):
        """The metadata JSON entry must round-trip back to the original dict."""
        zip_path = str(tmp_path / "output.zip")
        with PersonAttributesZipWriter(zip_path) as writer:
            writer.write_attributes(self.ROW_1)
            writer.build_zip(self.METADATA)

        with zipfile.ZipFile(zip_path) as zf:
            loaded = json.loads(zf.read("output.metadata.json").decode("utf-8"))

        assert loaded == self.METADATA

    def test_build_zip_returns_zip_path(self, tmp_path: Path):
        """build_zip must return the path of the created ZIP file."""
        zip_path = str(tmp_path / "output.zip")
        with PersonAttributesZipWriter(zip_path) as writer:
            writer.write_attributes(self.ROW_1)
            returned = writer.build_zip(self.METADATA)

        assert returned == zip_path

    def test_header_written_only_once(self, tmp_path: Path):
        """Multiple rows must share a single header line."""
        zip_path = str(tmp_path / "output.zip")
        rows = [{"A": "1", "B": "2"}, {"A": "3", "B": "4"}, {"A": "5", "B": "6"}]
        with PersonAttributesZipWriter(zip_path) as writer:
            for row in rows:
                writer.write_attributes(row)
            writer.build_zip({})

        with zipfile.ZipFile(zip_path) as zf:
            lines = zf.read("output.csv").decode("utf-8").splitlines()

        header_lines = [ln for ln in lines if ln == "A,B"]
        assert len(header_lines) == 1, "Header must appear exactly once"
        assert len(lines) == 4  # 1 header + 3 data rows

    def test_write_after_build_zip_raises(self, tmp_path: Path):
        """write_attributes after build_zip must raise RuntimeError."""
        zip_path = str(tmp_path / "output.zip")
        with PersonAttributesZipWriter(zip_path) as writer:
            writer.write_attributes(self.ROW_1)
            writer.build_zip(self.METADATA)
            with pytest.raises(RuntimeError):
                writer.write_attributes(self.ROW_2)

    def test_zip_stem_used_for_inner_filenames(self, tmp_path: Path):
        """Inner filenames derive from the ZIP stem, not the directory name."""
        zip_path = str(tmp_path / "my_tokens.zip")
        with PersonAttributesZipWriter(zip_path) as writer:
            writer.write_attributes(self.ROW_1)
            writer.build_zip(self.METADATA)

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()

        assert "my_tokens.csv" in names
        assert "my_tokens.metadata.json" in names

    def test_no_file_written_without_build_zip(self, tmp_path: Path):
        """Closing without calling build_zip must not create a ZIP file."""
        zip_path = str(tmp_path / "output.zip")
        with PersonAttributesZipWriter(zip_path) as writer:
            writer.write_attributes(self.ROW_1)
            # build_zip intentionally not called

        assert not Path(zip_path).exists()

    def test_creates_parent_directories(self, tmp_path: Path):
        """build_zip must create missing parent directories."""
        zip_path = str(tmp_path / "subdir" / "nested" / "output.zip")
        with PersonAttributesZipWriter(zip_path) as writer:
            writer.write_attributes(self.ROW_1)
            writer.build_zip(self.METADATA)

        assert Path(zip_path).exists()
