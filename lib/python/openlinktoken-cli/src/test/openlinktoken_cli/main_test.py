# SPDX-License-Identifier: MIT
"""
Integration tests for the main module.
Tests the end-to-end workflows for token generation and decryption using new subcommand interface.
"""

import os
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from openlinktoken_cli.commands.open_link_token_command import OpenLinkTokenCommand
from openlinktoken_cli.util.ec_key_utils import generate_key_pair


class TestOpenLinkTokenCommand:
    """Integration tests for Open Link Token CLI with new subcommand interface."""

    HASHING_SECRET = "TestHashingSecret"
    ENCRYPTION_KEY = "TestEncryptionKeyValue1234567890"  # Must be exactly 32 chars

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory with test input CSV."""
        input_csv = tmp_path / "input.csv"
        csv_content = (
            "RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber\n"
            "test-001,John,Doe,98004,Male,2000-01-01,123-45-6789\n"
            "test-002,Jane,Smith,12345,Female,1990-05-15,234-56-7890\n"
        )
        input_csv.write_text(csv_content)
        return tmp_path

    def _create_exchange_config(self, temp_dir: Path, name: str = "test-exchange") -> tuple[Path, Path]:
        """Create an exchange config and return ``(exchange_config_path, private_key_path)``."""
        _, partner_public_pem = generate_key_pair("P-256")
        partner_public_key_path = temp_dir / f"{name}.partner.public.pem"
        partner_public_key_path.write_bytes(partner_public_pem)
        exchange_config_path = temp_dir / f"{name}.exchange.json"

        with patch("pathlib.Path.home", return_value=temp_dir):
            exit_code = OpenLinkTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    name,
                    "--public-key",
                    str(partner_public_key_path),
                    "--output",
                    str(exchange_config_path),
                    "--hashingsecret",
                    self.HASHING_SECRET,
                ]
            )

        assert exit_code == 0
        private_key_path = temp_dir / ".openlinktoken" / f"{name}.private.pem"
        return exchange_config_path, private_key_path

    def test_package_command_csv_to_csv(self, temp_dir):
        """Test package command (tokenize + encrypt) with CSV input/output."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "package-csv")

        args = [
            "package",
            "-i",
            str(input_csv),
            "-o",
            str(output_csv),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)

        assert exit_code == 0, "Command should execute successfully"
        assert output_csv.exists(), "Output CSV should be created"
        assert output_csv.stat().st_size > 0, "Output CSV should not be empty"

        # Check metadata file
        metadata_path = temp_dir / "output.metadata.json"
        assert metadata_path.exists(), "Metadata file should be created"

    def test_package_command_csv_to_parquet(self, temp_dir):
        """Test package command with CSV input and Parquet output."""
        input_csv = temp_dir / "input.csv"
        output_parquet = temp_dir / "output.parquet"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "package-parquet")

        args = [
            "package",
            "-i",
            str(input_csv),
            "-o",
            str(output_parquet),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)

        assert exit_code == 0, "Command should execute successfully"
        assert output_parquet.exists(), "Output Parquet should be created"
        assert output_parquet.stat().st_size > 0, "Output Parquet should not be empty"

    def test_package_command_csv_to_zip(self, temp_dir):
        """Test package command with ZIP output bundles tokens, metadata, and exchange config."""
        input_csv = temp_dir / "input.csv"
        output_zip = temp_dir / "output.zip"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "package-zip")

        args = [
            "package",
            "-i",
            str(input_csv),
            "-o",
            str(output_zip),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)

        assert exit_code == 0, "Command should execute successfully"
        assert output_zip.exists(), "Output ZIP should be created"
        assert output_zip.stat().st_size > 0, "Output ZIP should not be empty"

        with zipfile.ZipFile(output_zip) as archive:
            names = archive.namelist()

        assert "output.csv" in names, "ZIP should contain the tokens CSV"
        assert "output.metadata.json" in names, "ZIP should contain the metadata JSON"
        assert "package-zip.exchange.json" in names, "ZIP should contain the exchange config JSON"
        assert len(names) == 3, f"ZIP should contain exactly 3 files, got: {names}"

        with zipfile.ZipFile(output_zip) as archive:
            assert len(archive.read("output.csv")) > 0, "Tokens CSV inside ZIP should not be empty"
            assert len(archive.read("output.metadata.json")) > 0, "Metadata JSON inside ZIP should not be empty"
            assert len(archive.read("package-zip.exchange.json")) > 0, "Exchange config inside ZIP should not be empty"

        # Metadata must NOT appear next to the zip — it is bundled inside
        assert not (temp_dir / "output.metadata.json").exists(), "Metadata should not appear next to the zip"

    def test_tokenize_command(self, temp_dir):
        """Test tokenize command (hash-only, no encryption)."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "tokenize")

        args = [
            "tokenize",
            "-i",
            str(input_csv),
            "-o",
            str(output_csv),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)

        assert exit_code == 0, "Command should execute successfully"
        assert output_csv.exists(), "Output CSV should be created"
        assert output_csv.stat().st_size > 0, "Output CSV should not be empty"

    def test_encrypt_command_csv_to_zip(self, temp_dir):
        """Test encrypt command with ZIP output bundles encrypted tokens and exchange config."""
        input_csv = temp_dir / "input.csv"
        hashed_csv = temp_dir / "hashed.csv"
        output_zip = temp_dir / "output.zip"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "encrypt-zip")

        # First tokenize (hash-only) to produce hashed tokens for encrypt to consume
        OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(input_csv),
                "-o",
                str(hashed_csv),
                "--exchange-config",
                str(exchange_config),
                "--private-key",
                str(private_key),
            ]
        )

        args = [
            "encrypt",
            "-i",
            str(hashed_csv),
            "-o",
            str(output_zip),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)

        assert exit_code == 0, "Command should execute successfully"
        assert output_zip.exists(), "Output ZIP should be created"
        assert output_zip.stat().st_size > 0, "Output ZIP should not be empty"

        with zipfile.ZipFile(output_zip) as archive:
            names = archive.namelist()

        assert "output.csv" in names, "ZIP should contain the encrypted tokens CSV"
        assert "encrypt-zip.exchange.json" in names, "ZIP should contain the exchange config JSON"
        assert len(names) == 2, f"ZIP should contain exactly 2 files, got: {names}"

        with zipfile.ZipFile(output_zip) as archive:
            assert len(archive.read("output.csv")) > 0, "Tokens CSV inside ZIP should not be empty"
            assert len(archive.read("encrypt-zip.exchange.json")) > 0, "Exchange config inside ZIP should not be empty"

    def test_decrypt_command(self, temp_dir):
        """Test decrypt command."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        decrypted_csv = temp_dir / "decrypted.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "decrypt")

        # First, generate encrypted tokens
        encrypt_args = [
            "package",
            "-i",
            str(input_csv),
            "-o",
            str(output_csv),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]
        OpenLinkTokenCommand.execute(encrypt_args)

        # Now decrypt them
        decrypt_args = [
            "decrypt",
            "-i",
            str(output_csv),
            "-o",
            str(decrypted_csv),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(decrypt_args)

        assert exit_code == 0, "Command should execute successfully"
        assert decrypted_csv.exists(), "Decrypted CSV should be created"
        assert decrypted_csv.stat().st_size > 0, "Decrypted CSV should not be empty"

    def test_output_type_defaults_to_input_type(self, temp_dir):
        """Test that output type defaults to input type when not specified."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "default-output-type")

        args = [
            "package",
            "-i",
            str(input_csv),
            "-o",
            str(output_csv),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)

        assert exit_code == 0, "Command should execute successfully"
        assert output_csv.exists(), "Output CSV should be created"

        # Verify CSV output was created (same as input type)
        content = output_csv.read_text()
        assert "RecordId" in content, "Output should contain CSV headers"

    def test_parquet_input_to_parquet_output(self, temp_dir):
        """Test Parquet input to Parquet output."""
        input_csv = temp_dir / "input.csv"
        temp_parquet = temp_dir / "temp.parquet"
        output_parquet = temp_dir / "output2.parquet"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "parquet-to-parquet")

        # First create a parquet file from CSV
        create_args = [
            "package",
            "-i",
            str(input_csv),
            "-o",
            str(temp_parquet),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]
        OpenLinkTokenCommand.execute(create_args)

        # Now use parquet as input
        args = [
            "decrypt",
            "-i",
            str(temp_parquet),
            "-o",
            str(output_parquet),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code == 0, "Command should execute successfully"

    def test_decrypt_csv_to_parquet(self, temp_dir):
        """Test decrypting CSV to Parquet format."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        decrypted_parquet = temp_dir / "decrypted.parquet"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "decrypt-parquet")

        # First generate encrypted tokens
        encrypt_args = [
            "package",
            "-i",
            str(input_csv),
            "-o",
            str(output_csv),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]
        OpenLinkTokenCommand.execute(encrypt_args)

        # Decrypt CSV to Parquet
        decrypt_args = [
            "decrypt",
            "-i",
            str(output_csv),
            "-o",
            str(decrypted_parquet),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(decrypt_args)
        assert exit_code == 0, "Command should execute successfully"
        assert decrypted_parquet.exists(), "Decrypted Parquet should be created"

    # ===== Negative Test Cases =====

    def test_missing_required_parameter_exchange_config(self, temp_dir):
        """Test that missing exchange-config input is caught."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        original_cwd = Path.cwd()

        try:
            os.chdir(temp_dir)
            args = [
                "tokenize",
                "-i",
                str(input_csv),
                "-o",
                str(output_csv),
                # Missing --exchange-config
            ]

            exit_code = OpenLinkTokenCommand.execute(args)
        finally:
            os.chdir(original_cwd)
        assert exit_code != 0, "Command should fail with missing required parameter"

    def test_missing_required_parameter_exchange_config_for_encrypt(self, temp_dir):
        """Test that encrypt fails when no exchange config can be resolved."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"

        args = [
            "encrypt",
            "-i",
            str(input_csv),
            "-o",
            str(output_csv),
            # Missing --exchange-config
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with missing required parameter"

    def test_missing_required_parameter_input(self, temp_dir):
        """Test that missing input parameter is caught."""
        output_csv = temp_dir / "output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "missing-input")

        args = [
            "tokenize",
            # Missing -i/--input
            "-o",
            str(output_csv),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with missing required parameter"

    def test_auto_output_path_tokenize_csv(self, temp_dir):
        """Omitting --output on tokenize should auto-generate <stem>_tokenized.csv."""
        input_csv = temp_dir / "input.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "auto-output-tokenize")

        args = [
            "tokenize",
            "-i",
            str(input_csv),
            # --output intentionally omitted
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)

        assert exit_code == 0, "Command should succeed when --output is omitted"
        auto_output = temp_dir / "input_tokenized.csv"
        assert auto_output.exists(), f"Auto-generated output {auto_output} should exist"
        assert auto_output.stat().st_size > 0, "Auto-generated output should not be empty"

    def test_auto_output_path_tokenize_parquet(self, temp_dir):
        """Omitting --output on tokenize with parquet input should auto-generate <stem>_tokenized.parquet."""
        input_csv = temp_dir / "input.csv"
        input_parquet = temp_dir / "input.parquet"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "auto-output-tokenize-parquet")

        # Create parquet from CSV using tokenize
        OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(input_csv),
                "-o",
                str(input_parquet),
                "--exchange-config",
                str(exchange_config),
                "--private-key",
                str(private_key),
            ]
        )
        assert input_parquet.exists(), "Parquet input fixture should be created"

        # Now re-tokenize using the parquet file without --output
        exchange_config2, private_key2 = self._create_exchange_config(temp_dir, "auto-output-tokenize-parquet-2")
        args = [
            "tokenize",
            "-i",
            str(input_parquet),
            # --output intentionally omitted
            "--exchange-config",
            str(exchange_config2),
            "--private-key",
            str(private_key2),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)

        assert exit_code == 0, "Command should succeed for parquet input without --output"
        auto_output = temp_dir / "input_tokenized.parquet"
        assert auto_output.exists(), f"Auto-generated parquet output {auto_output} should exist"

    def test_auto_output_path_package_defaults_to_zip(self, temp_dir):
        """Omitting --output on package should auto-generate <stem>_packaged.zip regardless of input type."""
        input_csv = temp_dir / "input.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "auto-output-package")

        args = [
            "package",
            "-i",
            str(input_csv),
            # --output intentionally omitted → should default to input_packaged.zip
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)

        assert exit_code == 0, "Package command should succeed when --output is omitted"
        auto_output = temp_dir / "input_packaged.zip"
        assert auto_output.exists(), f"Auto-generated zip output {auto_output} should exist"
        assert auto_output.stat().st_size > 0, "Auto-generated zip should not be empty"

    def test_auto_output_path_decrypt(self, temp_dir):
        """Omitting --output on decrypt should auto-generate <stem>_decrypted<ext>."""
        input_csv = temp_dir / "input.csv"
        packaged_csv = temp_dir / "packaged.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "auto-output-decrypt")

        # Package first to produce encrypted tokens
        OpenLinkTokenCommand.execute(
            [
                "package",
                "-i",
                str(input_csv),
                "-o",
                str(packaged_csv),
                "--exchange-config",
                str(exchange_config),
                "--private-key",
                str(private_key),
            ]
        )
        assert packaged_csv.exists()

        args = [
            "decrypt",
            "-i",
            str(packaged_csv),
            # --output intentionally omitted
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)

        assert exit_code == 0, "Decrypt command should succeed when --output is omitted"
        auto_output = temp_dir / "packaged_decrypted.csv"
        assert auto_output.exists(), f"Auto-generated decrypted output {auto_output} should exist"

    def test_explicit_output_overrides_auto_generated(self, temp_dir):
        """Providing an explicit --output should override the auto-generated path."""
        input_csv = temp_dir / "input.csv"
        explicit_output = temp_dir / "my_custom_output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "explicit-output-override")

        args = [
            "tokenize",
            "-i",
            str(input_csv),
            "-o",
            str(explicit_output),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)

        assert exit_code == 0, "Command should succeed with explicit output"
        assert explicit_output.exists(), "Explicit output path should be used"
        assert not (temp_dir / "input_tokenized.csv").exists(), "Auto-generated path should NOT be created"

    def test_invalid_input_type(self, temp_dir):
        """Test that unsupported input file extension is caught."""
        unsupported_file = temp_dir / "input.txt"  # .txt is not supported
        unsupported_file.write_text("some data")
        output_csv = temp_dir / "output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "invalid-input-type")

        args = [
            "tokenize",
            "-i",
            str(unsupported_file),
            "-o",
            str(output_csv),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with unsupported input extension"

    def test_invalid_output_type(self, temp_dir):
        """Test that unsupported output file extension is caught."""
        input_csv = temp_dir / "input.csv"
        unsupported_output = temp_dir / "output.txt"  # .txt is not supported
        exchange_config, private_key = self._create_exchange_config(temp_dir, "invalid-output-type")

        args = [
            "tokenize",
            "-i",
            str(input_csv),
            "-o",
            str(unsupported_output),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with unsupported output extension"

    def test_non_existent_input_file(self, temp_dir):
        """Test that non-existent input file is caught."""
        nonexistent_file = temp_dir / "nonexistent.csv"
        output_csv = temp_dir / "output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "missing-input-file")

        args = [
            "tokenize",
            "-i",
            str(nonexistent_file),
            "-o",
            str(output_csv),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with non-existent input file"

    def test_package_command_missing_exchange_config(self, temp_dir):
        """Test that package command fails when no exchange config can be resolved."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        original_cwd = Path.cwd()

        try:
            os.chdir(temp_dir)
            args = [
                "package",
                "-i",
                str(input_csv),
                "-o",
                str(output_csv),
                # Missing --exchange-config
            ]

            exit_code = OpenLinkTokenCommand.execute(args)
        finally:
            os.chdir(original_cwd)
        assert exit_code != 0, "Command should fail with missing required parameters"

    def test_invalid_subcommand(self, temp_dir):
        """Test that invalid subcommand is caught."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"

        args = [
            "invalid_command",  # Invalid subcommand
            "-i",
            str(input_csv),
            "-o",
            str(output_csv),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with invalid subcommand"

    def test_unexpected_command_error_writes_reference_log(self, tmp_path, capsys, monkeypatch):
        """Unexpected command failures should write a referenceable traceback log."""
        monkeypatch.setattr("sys.stderr.isatty", lambda: True)
        with patch(
            "openlinktoken_cli.commands.tokenize_command.TokenizeCommand.execute",
            side_effect=RuntimeError("boom"),
        ):
            with patch("pathlib.Path.home", return_value=tmp_path):
                exit_code = OpenLinkTokenCommand.execute(
                    [
                        "--no-update-check",
                        "tokenize",
                        "-i",
                        "input.csv",
                        "-o",
                        "output.csv",
                    ]
                )

        captured = capsys.readouterr()
        log_dir = tmp_path / ".openlinktoken" / "logs"
        log_files = list(log_dir.glob("*.log"))

        assert exit_code != 0
        assert "Traceback" not in captured.err
        assert "Reference:" not in captured.err
        assert "\x1b[90mStack trace:" in captured.err
        assert len(log_files) == 1
        assert str(log_files[0]) in captured.err
        assert "Traceback" in log_files[0].read_text()
        assert "RuntimeError: boom" in log_files[0].read_text()

    def test_package_command_success_summary_references_run_log(self, temp_dir, capsys, monkeypatch):
        """Successful package runs should print a summary and point at the detailed log."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "package-summary")
        monkeypatch.setattr("sys.stderr.isatty", lambda: False)

        with patch("pathlib.Path.home", return_value=temp_dir):
            exit_code = OpenLinkTokenCommand.execute(
                [
                    "--no-update-check",
                    "package",
                    "-i",
                    str(input_csv),
                    "-o",
                    str(output_csv),
                    "--exchange-config",
                    str(exchange_config),
                    "--private-key",
                    str(private_key),
                ]
            )

        captured = capsys.readouterr()
        log_dir = temp_dir / ".openlinktoken" / "logs"
        log_files = list(log_dir.glob("*.log"))

        assert exit_code == 0
        assert "Package complete" in captured.err
        assert f"Output: {output_csv}" in captured.err
        assert "Rows processed: 2" in captured.err
        assert len(log_files) == 1
        assert f"Detailed log: {log_files[0]}" in captured.err
        assert "Running package command (tokenize + encrypt)" not in captured.err
        assert "Running package command (tokenize + encrypt)" in log_files[0].read_text()
        assert "Processed a total of 2 records" in log_files[0].read_text()

    def test_tokenize_command_allows_basename_output_path_in_current_directory(self, tmp_path, monkeypatch):
        """Tokenize should support basename-only output paths in the current directory."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber\n"
            "test-001,John,Doe,98004,Male,2000-01-01,123-45-6789\n",
            encoding="utf-8",
        )

        monkeypatch.chdir(tmp_path)

        exit_code = OpenLinkTokenCommand.execute(
            [
                "--no-update-check",
                "tokenize",
                "-i",
                "input.csv",
                "-o",
                "output.csv",
                "--mode",
                "demo",
            ]
        )

        assert exit_code == 0
        assert (tmp_path / "output.csv").exists()
        assert (tmp_path / "output.metadata.json").exists()

    def test_tokenize_unexpected_processing_error_writes_reference_log(self, tmp_path, capsys, monkeypatch):
        """Unexpected tokenize failures should archive the traceback and print a reference."""
        monkeypatch.setattr("sys.stderr.isatty", lambda: True)
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber\n"
            "test-001,John,Doe,98004,Male,2000-01-01,123-45-6789\n",
            encoding="utf-8",
        )

        with patch(
            "openlinktoken_cli.commands.tokenize_command.TokenizeCommand._process_tokens_demo",
            side_effect=RuntimeError("boom"),
        ):
            with patch("pathlib.Path.home", return_value=tmp_path):
                exit_code = OpenLinkTokenCommand.execute(
                    [
                        "--no-update-check",
                        "tokenize",
                        "-i",
                        str(input_csv),
                        "-o",
                        "output.csv",
                        "--mode",
                        "demo",
                    ]
                )

        captured = capsys.readouterr()
        log_dir = tmp_path / ".openlinktoken" / "logs"
        log_files = list(log_dir.glob("*.log"))

        assert exit_code != 0
        assert "Traceback" not in captured.err
        assert "Reference:" not in captured.err
        assert "\x1b[90mStack trace:" in captured.err
        assert len(log_files) == 1
        assert str(log_files[0]) in captured.err
        assert "Traceback" in log_files[0].read_text()
        assert "RuntimeError: boom" in log_files[0].read_text()

    def test_tokenize_unexpected_processing_error_reuses_run_log(self, tmp_path, capsys, monkeypatch):
        """Processing failures should append the traceback to the same per-run log file."""
        monkeypatch.setattr("sys.stderr.isatty", lambda: True)
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber\n"
            "test-001,John,Doe,98004,Male,2000-01-01,123-45-6789\n",
            encoding="utf-8",
        )

        with patch(
            "openlinktoken_cli.commands.tokenize_command.TokenizeCommand._process_tokens_demo",
            side_effect=RuntimeError("boom"),
        ):
            with patch("pathlib.Path.home", return_value=tmp_path):
                exit_code = OpenLinkTokenCommand.execute(
                    [
                        "--no-update-check",
                        "tokenize",
                        "-i",
                        str(input_csv),
                        "-o",
                        "output.csv",
                        "--mode",
                        "demo",
                    ]
                )

        captured = capsys.readouterr()
        log_dir = tmp_path / ".openlinktoken" / "logs"
        log_files = list(log_dir.glob("*.log"))

        assert exit_code != 0
        assert "Error: boom" in captured.err
        assert "\x1b[90mStack trace:" in captured.err
        assert len(log_files) == 1
        assert str(log_files[0]) in captured.err
        assert "Running in DEMO MODE" in log_files[0].read_text()
        assert "RuntimeError: boom" in log_files[0].read_text()

    def test_package_missing_exchange_config_writes_reference_log(self, tmp_path, monkeypatch, capsys):
        """Handled package errors should still print the archived traceback location."""
        monkeypatch.setattr("sys.stderr.isatty", lambda: True)
        input_csv = tmp_path / "sample.csv"
        input_csv.write_text(
            "RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber\n"
            "test-001,John,Doe,98004,Male,2000-01-01,123-45-6789\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenLinkTokenCommand.execute(
                [
                    "--no-update-check",
                    "package",
                    "-i",
                    str(input_csv),
                    "-o",
                    "output.csv",
                ]
            )

        captured = capsys.readouterr()
        log_dir = tmp_path / ".openlinktoken" / "logs"
        log_files = list(log_dir.glob("*.log"))

        assert exit_code != 0
        assert "Reference:" not in captured.err
        assert "\x1b[90mStack trace:" in captured.err
        assert len(log_files) == 1
        assert str(log_files[0]) in captured.err
        assert "Traceback" in log_files[0].read_text()
        assert "FileNotFoundError" in log_files[0].read_text()

    def test_help_shows_banner_for_interactive_runs(self, monkeypatch, capsys):
        """Interactive help output should include the Open Link Token banner."""
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)

        exit_code = OpenLinkTokenCommand.execute(["--help"])

        captured = capsys.readouterr()
        assert exit_code == 0, "Help should exit successfully"
        assert "Privacy-Preserving Record Linkage v" in captured.out
        assert "usage: olt" in captured.out

    def test_bare_invocation_shows_banner_for_interactive_runs(self, monkeypatch, capsys):
        """Interactive top-level invocation should include the banner before help output."""
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)

        with patch("openlinktoken_cli.commands.open_link_token_command.start_version_check") as mock_version_check:
            exit_code = OpenLinkTokenCommand.execute([])

        captured = capsys.readouterr()
        assert exit_code == 0, "Bare invocation should exit successfully"
        assert "Privacy-Preserving Record Linkage v" in captured.out
        assert "usage: olt" in captured.out
        mock_version_check.return_value.wait_and_notify.assert_called_once()

    def test_help_subcommand_shows_banner_for_interactive_runs(self, monkeypatch, capsys):
        """Interactive help subcommand output should include the Open Link Token banner."""
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)

        exit_code = OpenLinkTokenCommand.execute(["help"])

        captured = capsys.readouterr()
        assert exit_code == 0, "Help subcommand should exit successfully"
        assert "Privacy-Preserving Record Linkage v" in captured.out
        assert "usage: olt" in captured.out

    def test_version_does_not_show_banner_for_interactive_runs(self, monkeypatch, capsys):
        """Interactive non-help output should not include the Open Link Token banner."""
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)

        exit_code = OpenLinkTokenCommand.execute(["--version"])

        captured = capsys.readouterr()
        assert exit_code == 0, "Version output should exit successfully"
        assert "Open Link Token" in captured.out
        assert "Privacy-Preserving Record Linkage v" not in captured.out

    # ===== Hash Record IDs Tests =====

    def test_tokenize_command_hash_record_ids_output_contains_hashed_ids(self, temp_dir):
        """Output token file must contain hashed (not original) RecordId values."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "tokenize-hash-record-ids")

        args = [
            "tokenize",
            "-i",
            str(input_csv),
            "-o",
            str(output_csv),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
            "--hash-record-ids",
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code == 0, "Command should execute successfully"
        assert output_csv.exists(), "Output CSV should be created"

        content = output_csv.read_text()
        assert "test-001" not in content, "Output must not contain original record IDs"
        assert "test-002" not in content, "Output must not contain original record IDs"

        # All RecordId values should be 64-char hex strings (SHA-256)
        lines = content.strip().splitlines()
        headers = lines[0].split(",")
        record_id_col = headers.index("RecordId")
        for line in lines[1:]:
            cols = line.split(",")
            record_id = cols[record_id_col].strip()
            assert len(record_id) == 64, f"Hashed record ID must be 64 chars, got: {record_id!r}"

    def test_tokenize_command_without_hash_record_ids_output_contains_original_ids(self, temp_dir):
        """Without --hash-record-ids the output must contain the original record IDs."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "tokenize-record-ids-original")

        args = [
            "tokenize",
            "-i",
            str(input_csv),
            "-o",
            str(output_csv),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        OpenLinkTokenCommand.execute(args)

        content = output_csv.read_text()
        assert "test-001" in content, "Output should contain original record IDs"
        assert "test-002" in content, "Output should contain original record IDs"

    def test_package_command_hash_record_ids_output_contains_hashed_ids(self, temp_dir):
        """--hash-record-ids on package must produce hashed (not original) RecordId values."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "package-hash-record-ids")

        args = [
            "package",
            "-i",
            str(input_csv),
            "-o",
            str(output_csv),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
            "--hash-record-ids",
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code == 0, "Command should execute successfully"

        content = output_csv.read_text()
        assert "test-001" not in content, "Output must not contain original record IDs"
        assert "test-002" not in content, "Output must not contain original record IDs"


class TestInitiateExchangeViaMain:
    """Smoke tests for initiate-exchange wired through OpenLinkTokenCommand.execute."""

    @pytest.mark.parametrize("command", ["tokenize", "package", "encrypt", "decrypt"])
    def test_consumer_help_uses_exchange_config_contract(self, command, capsys):
        """Consumer command help should advertise exchange-config inputs instead of plaintext secrets."""
        exit_code = OpenLinkTokenCommand.execute([command, "--help"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "--exchange-config" in captured.out
        assert "--private-key" in captured.out
        assert "--private-key-env" in captured.out
        assert "openlinktoken-YYYY-MM-DD.exchange.json" in captured.out
        assert "--hashingsecret" not in captured.out
        assert "--encryptionkey" not in captured.out

    def test_initiate_exchange_appears_in_help(self, capsys):
        """initiate-exchange is listed in the top-level help output."""
        OpenLinkTokenCommand.execute(["--help"])
        captured = capsys.readouterr()
        assert "initiate-exchange" in captured.out

    def test_initiate_exchange_help_describes_sender_private_key_without_embedding(self, capsys):
        """Subcommand help should prefer --sender-private-key without implying embedding."""
        exit_code = OpenLinkTokenCommand.execute(["initiate-exchange", "--help"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "--sender-private-key" in captured.out
        assert "--local-private-key" not in captured.out
        assert "Reuse an existing sender private key PEM" in captured.out
        assert "embed" not in captured.out.lower()

    def test_initiate_exchange_help_lists_public_key_stdin(self, capsys):
        """Subcommand help should advertise --public-key-stdin as an input alternative."""
        exit_code = OpenLinkTokenCommand.execute(["initiate-exchange", "--help"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "--public-key-stdin" in captured.out

    def test_initiate_exchange_help_lists_env_key_references(self, capsys):
        """Subcommand help should advertise env-var references for both partner and sender keys."""
        exit_code = OpenLinkTokenCommand.execute(["initiate-exchange", "--help"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "--public-key-env" in captured.out
        assert "--sender-private-key-env" in captured.out

    def test_initiate_exchange_help_lists_safe_hashing_secret_inputs(self, capsys):
        """Subcommand help should advertise non-argv hashing-secret input modes."""
        exit_code = OpenLinkTokenCommand.execute(["initiate-exchange", "--help"])

        captured = capsys.readouterr()
        assert exit_code == 0
        assert "--hashingsecret-env" in captured.out
        assert "--hashingsecret-stdin" in captured.out

    def test_initiate_exchange_succeeds_with_valid_inputs(self, tmp_path):
        """initiate-exchange returns 0 for a complete valid invocation."""
        from unittest.mock import patch

        from openlinktoken_cli.util.ec_key_utils import generate_key_pair

        _, partner_public_pem = generate_key_pair("P-256")
        partner_pem_path = tmp_path / "partner.public.pem"
        partner_pem_path.write_bytes(partner_public_pem)
        output_path = tmp_path / "smoke.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenLinkTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "smoke",
                    "--public-key",
                    str(partner_pem_path),
                    "--output",
                    str(output_path),
                ]
            )

        assert exit_code == 0
        assert output_path.exists()

    def test_initiate_exchange_missing_public_key_fails(self, tmp_path):
        """initiate-exchange exits non-zero when --public-key is omitted."""
        from unittest.mock import patch

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenLinkTokenCommand.execute(["initiate-exchange", "--name", "no-pk"])

        assert exit_code != 0


class TestStartupVersionCheckPolicy:
    """Tests for startup version-check behavior by parsed subcommand."""

    def test_should_start_version_check_false_for_update_command(self):
        parsed_args = type("ParsedArgs", (), {"command": "update"})
        assert not OpenLinkTokenCommand._should_start_version_check(parsed_args)

    def test_should_start_version_check_true_for_non_update_command(self):
        parsed_args = type("ParsedArgs", (), {"command": "tokenize"})
        assert OpenLinkTokenCommand._should_start_version_check(parsed_args)
