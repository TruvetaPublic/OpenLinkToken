# SPDX-License-Identifier: MIT

from openlinktoken_cli.io import FileExtension
from openlinktoken_cli.io.file_extension import FileExtension as FileExtensionDirect


def test_file_extension_values():
    assert FileExtension.CSV == ".csv"
    assert FileExtension.PARQUET == ".parquet"
    assert FileExtension.ZIP == ".zip"


def test_file_extension_is_str():
    assert isinstance(FileExtension.CSV, str)
    assert isinstance(FileExtension.PARQUET, str)
    assert isinstance(FileExtension.ZIP, str)


def test_file_extension_importable_from_io_package():
    assert FileExtension is FileExtensionDirect


def test_file_extension_all_members():
    members = {e.value for e in FileExtension}
    assert members == {".csv", ".parquet", ".zip"}
