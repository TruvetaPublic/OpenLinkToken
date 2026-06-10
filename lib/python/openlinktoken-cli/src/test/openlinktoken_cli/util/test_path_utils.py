# SPDX-License-Identifier: MIT

from openlinktoken_cli.util.path_utils import get_auto_output_path


class TestGetAutoOutputPath:
    """Unit tests for get_auto_output_path()."""

    def test_tokenize_csv(self):
        assert get_auto_output_path("data.csv", "tokenize") == "data_tokenized.csv"

    def test_encrypt_parquet(self):
        assert get_auto_output_path("records.parquet", "encrypt") == "records_encrypted.parquet"

    def test_decrypt_file_no_extension(self):
        assert get_auto_output_path("myfile", "decrypt") == "myfile_decrypted"

    def test_package_zip(self):
        assert get_auto_output_path("input.csv", "package") == "input_packaged.zip"

    def test_tokenize_no_extension(self):
        assert get_auto_output_path("myfile", "tokenize") == "myfile_tokenized"

    def test_decrypt_known_file(self):
        assert get_auto_output_path("customers.csv", "decrypt") == "customers_decrypted.csv"

    def test_package_nested_path(self):
         # Path.stem returns just the filename ("data"), but with_name() preserves parent dirs
        assert get_auto_output_path("path/to/data.json", "package") == "path/to/data_packaged.zip"

    def test_suffix_unknown_subcommand(self):
        assert get_auto_output_path("file.txt", "mymode") == "file_mymode.txt"

    def test_no_extension_nonstandard_subcommand(self):
        assert get_auto_output_path("README", "custom") == "README_custom"

    def test_package_already_zip(self):
        assert get_auto_output_path("output.zip", "package") == "output_packaged.zip"
