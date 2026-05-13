"""
Copyright (c) Truveta. All rights reserved.
"""

from openlinktoken_cli.io import FileExtension
from openlinktoken_cli.io.file_extension import FileExtension as FileExtensionDirect


class TestFileExtension:
    def test_csv_value(self):
        assert FileExtension.CSV == ".csv"

    def test_parquet_value(self):
        assert FileExtension.PARQUET == ".parquet"

    def test_zip_value(self):
        assert FileExtension.ZIP == ".zip"

    def test_is_str(self):
        for member in FileExtension:
            assert isinstance(member, str)

    def test_all_members_present(self):
        members = {e.name for e in FileExtension}
        assert members == {"CSV", "PARQUET", "ZIP"}

    def test_importable_from_io_package(self):
        assert FileExtension is FileExtensionDirect

    def test_string_comparison(self):
        assert FileExtension.CSV == ".csv"
        assert ".parquet" == FileExtension.PARQUET

    def test_use_in_set(self):
        extensions = {FileExtension.CSV, FileExtension.PARQUET, FileExtension.ZIP}
        assert ".csv" in extensions
