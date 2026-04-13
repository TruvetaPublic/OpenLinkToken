# SPDX-License-Identifier: MIT
"""
Integration tests for the main module.
Tests the end-to-end workflows for token generation and decryption using new subcommand interface.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from openlinktoken_cli.commands.open_token_command import OpenLinkTokenCommand
from openlinktoken_cli.util.ec_key_utils import generate_key_pair


class TestOpenLinkTokenCommand:
    """Integration tests for OpenLinkToken CLI with new subcommand interface."""

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
            "-t",
            "csv",
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
            "-t",
            "csv",
            "-o",
            str(output_parquet),
            "-ot",
            "parquet",
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)

        assert exit_code == 0, "Command should execute successfully"
        assert output_parquet.exists(), "Output Parquet should be created"
        assert output_parquet.stat().st_size > 0, "Output Parquet should not be empty"

    def test_tokenize_command(self, temp_dir):
        """Test tokenize command (hash-only, no encryption)."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "tokenize")

        args = [
            "tokenize",
            "-i",
            str(input_csv),
            "-t",
            "csv",
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
            "-t",
            "csv",
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
            "-t",
            "csv",
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
            "-t",
            "csv",
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
            "-t",
            "csv",
            "-o",
            str(temp_parquet),
            "-ot",
            "parquet",
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
            "-t",
            "parquet",
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
            "-t",
            "csv",
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
            "-t",
            "csv",
            "-o",
            str(decrypted_parquet),
            "-ot",
            "parquet",
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

        args = [
            "tokenize",
            "-i",
            str(input_csv),
            "-t",
            "csv",
            "-o",
            str(output_csv),
            # Missing --exchange-config
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with missing required parameter"

    def test_missing_required_parameter_exchange_config_for_encrypt(self, temp_dir):
        """Test that encrypt fails when no exchange config can be resolved."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"

        args = [
            "encrypt",
            "-i",
            str(input_csv),
            "-t",
            "csv",
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
            "-t",
            "csv",
            "-o",
            str(output_csv),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with missing required parameter"

    def test_missing_required_parameter_output(self, temp_dir):
        """Test that missing output parameter is caught."""
        input_csv = temp_dir / "input.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "missing-output")

        args = [
            "tokenize",
            "-i",
            str(input_csv),
            "-t",
            "csv",
            # Missing -o/--output
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with missing required parameter"

    def test_invalid_input_type(self, temp_dir):
        """Test that invalid input type is caught."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "invalid-input-type")

        args = [
            "tokenize",
            "-i",
            str(input_csv),
            "-t",
            "invalid_type",  # Invalid input type
            "-o",
            str(output_csv),
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with invalid input type"

    def test_invalid_output_type(self, temp_dir):
        """Test that invalid output type is caught."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "invalid-output-type")

        args = [
            "tokenize",
            "-i",
            str(input_csv),
            "-t",
            "csv",
            "-o",
            str(output_csv),
            "-ot",
            "invalid_type",  # Invalid output type
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with invalid output type"

    def test_non_existent_input_file(self, temp_dir):
        """Test that non-existent input file is caught."""
        nonexistent_file = temp_dir / "nonexistent.csv"
        output_csv = temp_dir / "output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "missing-input-file")

        args = [
            "tokenize",
            "-i",
            str(nonexistent_file),
            "-t",
            "csv",
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

        args = [
            "package",
            "-i",
            str(input_csv),
            "-t",
            "csv",
            "-o",
            str(output_csv),
            # Missing --exchange-config
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with missing required parameters"

    def test_invalid_subcommand(self, temp_dir):
        """Test that invalid subcommand is caught."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"

        args = [
            "invalid_command",  # Invalid subcommand
            "-i",
            str(input_csv),
            "-t",
            "csv",
            "-o",
            str(output_csv),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with invalid subcommand"

    def test_help_shows_banner_for_interactive_runs(self, monkeypatch, capsys):
        """Interactive help output should include the OpenLinkToken banner."""
        monkeypatch.setattr("sys.stdout.isatty", lambda: True)

        exit_code = OpenLinkTokenCommand.execute(["--help"])

        captured = capsys.readouterr()
        assert exit_code == 0, "Help should exit successfully"
        assert "Privacy-Preserving Record Linkage v" in captured.out
        assert "usage: olt" in captured.out

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
            "-t",
            "csv",
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
            "-t",
            "csv",
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
            "-t",
            "csv",
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
