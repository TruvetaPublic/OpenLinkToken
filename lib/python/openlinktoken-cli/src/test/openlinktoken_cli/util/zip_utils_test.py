# SPDX-License-Identifier: MIT

import zipfile

import pytest

from openlinktoken_cli.util.zip_utils import bundle_into_zip


class TestBundleIntoZip:
    """Unit tests for bundle_into_zip."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        return tmp_path

    def test_creates_zip_with_all_files(self, temp_dir):
        """All provided files appear in the archive."""
        file_a = temp_dir / "tokens.csv"
        file_b = temp_dir / "tokens.metadata.json"
        file_c = temp_dir / "exchange.json"
        file_a.write_text("a")
        file_b.write_text("b")
        file_c.write_text("c")

        output_zip = temp_dir / "output.zip"
        bundle_into_zip(str(output_zip), str(file_a), str(file_b), str(file_c))

        with zipfile.ZipFile(output_zip) as archive:
            assert sorted(archive.namelist()) == sorted(["tokens.csv", "tokens.metadata.json", "exchange.json"])

    def test_archive_entries_use_basename(self, temp_dir):
        """Entry names are basenames only — no directory path components."""
        sub = temp_dir / "subdir"
        sub.mkdir()
        file_a = sub / "deep_file.csv"
        file_a.write_text("data")

        output_zip = temp_dir / "output.zip"
        bundle_into_zip(str(output_zip), str(file_a))

        with zipfile.ZipFile(output_zip) as archive:
            assert archive.namelist() == ["deep_file.csv"]

    def test_file_contents_preserved(self, temp_dir):
        """Contents of each file are preserved inside the archive."""
        file_a = temp_dir / "data.csv"
        file_a.write_text("row1,row2")

        output_zip = temp_dir / "output.zip"
        bundle_into_zip(str(output_zip), str(file_a))

        with zipfile.ZipFile(output_zip) as archive:
            assert archive.read("data.csv") == b"row1,row2"

    def test_creates_parent_directories(self, temp_dir):
        """Parent directories of the zip path are created if they do not exist."""
        file_a = temp_dir / "tokens.csv"
        file_a.write_text("x")

        output_zip = temp_dir / "nested" / "deep" / "output.zip"
        bundle_into_zip(str(output_zip), str(file_a))

        assert output_zip.exists()

    def test_uses_deflate_compression(self, temp_dir):
        """Archive uses ZIP_DEFLATED compression."""
        file_a = temp_dir / "tokens.csv"
        file_a.write_text("a" * 1000)

        output_zip = temp_dir / "output.zip"
        bundle_into_zip(str(output_zip), str(file_a))

        with zipfile.ZipFile(output_zip) as archive:
            info = archive.getinfo("tokens.csv")
            assert info.compress_type == zipfile.ZIP_DEFLATED
