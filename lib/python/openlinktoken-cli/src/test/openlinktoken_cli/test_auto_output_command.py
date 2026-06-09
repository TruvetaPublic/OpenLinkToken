# SPDX-License-Identifier: MIT
"""
Integration tests for auto-generated output filenames.
Tests that omitting the --output flag produces expected filenames and extensions.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from openlinktoken_cli.commands.open_link_token_command import OpenLinkTokenCommand
from openlinktoken_cli.util.ec_key_utils import generate_key_pair


class TestAutoOutputCommands:
    """Integration tests for auto-generated output filenames in CLI commands."""

    HASHING_SECRET = "TestHashingSecret"
    ENCRYPTION_KEY = "TestEncryptionKeyValue1234567890"  # Must be exactly 32 chars

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory with test input CSV."""
        input_csv = tmp_path / "input.csv"
        csv_content = (
            "RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber\n"
            "test-001,John,Doe,98004,Male,2000-01-15,123-45-6789\n"
            "test-002,Jane,Smith,12345,Female,1990-05-20,234-56-7890\n"
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

    # ------------------------------------------------------------------
    # Tokenize Tests
    # ------------------------------------------------------------------

    def test_tokenize_auto_output_csv(self, temp_dir):
        """Test tokenize with auto-generated .csv output (suffix '_tokenized')."""
        input_csv = temp_dir / "input.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "tokenize-auto")

        args = [
            "tokenize",
            "-i",
            str(input_csv),
            "--mode",
            "hash-only",
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code == 0

        expected_output = temp_dir / "input_tokenized.csv"
        assert expected_output.exists()
        assert (temp_dir / "input_tokenized.metadata.json").exists()

    def test_tokenize_explicit_output_override(self, temp_dir):
        """Test that explicit --output override still works for tokenize."""
        input_csv = temp_dir / "input.csv"
        custom_output = temp_dir / "manual_output.parquet"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "tokenize-override")

        args = [
            "tokenize",
            "-i",
            str(input_csv),
            "-o",
            str(custom_output),
            "--mode",
            "hash-only",
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code == 0
        assert custom_output.exists()

    # ------------------------------------------------------------------
    # Encrypt Tests
    # ------------------------------------------------------------------

    def test_encrypt_auto_output_csv(self, temp_dir):
        """Test encrypt with auto-generated .csv output (suffix '_encrypted')."""
        input_csv = temp_dir / "hashed.csv"
        input_csv.write_text("RecordId,Token\ntest-001,abc\n")
        exchange_config, private_key = self._create_exchange_config(temp_dir, "encrypt-auto")

        args = [
            "encrypt",
            "-i",
            str(input_csv),
            # Omitting -o
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code == 0

        expected_output = temp_dir / "hashed_encrypted.csv"
        assert expected_output.exists()

    # ------------------------------------------------------------------
    def test_decrypt_auto_output_csv(self, temp_dir):
        """Test decrypt with auto-generated .csv output (suffix '_decrypted')."""
        input_csv = temp_dir / "encrypted.csv"
        input_csv.write_text("RecordId,Token\ntest-001,abc\n")
        exchange_config, private_key = self._create_exchange_config(temp_dir, "decrypt-auto")

        args = [
            "decrypt",
            "-i",
            str(input_csv),
            # Omitting -o
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code == 0

        expected_output = temp_dir / "encrypted_decrypted.csv"
        assert expected_output.exists()

    # ------------------------------------------------------------------
    # Package Tests
    # ------------------------------------------------------------------

    def test_package_auto_output_zip(self, temp_dir):
        """Test package with auto-generated .zip output (even if input is CSV)."""
        input_csv = temp_dir / "input.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "package-auto")

        args = [
            "package",
            "-i",
            str(input_csv),
            # Omitting -o
            "--exchange-config",
            str(exchange_config),
            "--private-key",
            str(private_key),
        ]

        exit_code = OpenLinkTokenCommand.execute(args)
        assert exit_code == 0

        expected_output = temp_dir / "input.zip"
        assert expected_output.exists()
