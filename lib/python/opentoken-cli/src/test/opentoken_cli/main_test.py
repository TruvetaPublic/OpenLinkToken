"""
Copyright (c) Truveta. All rights reserved.

Integration tests for the main module.
Tests the end-to-end workflows for token generation and decryption using new subcommand interface.
"""

import os
import pytest
import tempfile
from pathlib import Path

from opentoken_cli.commands.open_token_command import OpenTokenCommand


class TestOpenTokenCommand:
    """Integration tests for OpenToken CLI with new subcommand interface."""

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

    def test_package_command_csv_to_csv(self, temp_dir):
        """Test package command (tokenize + encrypt) with CSV input/output."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"

        args = [
            "package",
            "-i", str(input_csv),
            "-t", "csv",
            "-o", str(output_csv),
            "--hashingsecret", self.HASHING_SECRET,
            "--encryptionkey", self.ENCRYPTION_KEY
        ]

        exit_code = OpenTokenCommand.execute(args)

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

        args = [
            "package",
            "-i", str(input_csv),
            "-t", "csv",
            "-o", str(output_parquet),
            "-ot", "parquet",
            "--hashingsecret", self.HASHING_SECRET,
            "--encryptionkey", self.ENCRYPTION_KEY
        ]

        exit_code = OpenTokenCommand.execute(args)

        assert exit_code == 0, "Command should execute successfully"
        assert output_parquet.exists(), "Output Parquet should be created"
        assert output_parquet.stat().st_size > 0, "Output Parquet should not be empty"

    def test_tokenize_command(self, temp_dir):
        """Test tokenize command (hash-only, no encryption)."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"

        args = [
            "tokenize",
            "-i", str(input_csv),
            "-t", "csv",
            "-o", str(output_csv),
            "--hashingsecret", self.HASHING_SECRET
        ]

        exit_code = OpenTokenCommand.execute(args)

        assert exit_code == 0, "Command should execute successfully"
        assert output_csv.exists(), "Output CSV should be created"
        assert output_csv.stat().st_size > 0, "Output CSV should not be empty"

    def test_decrypt_command(self, temp_dir):
        """Test decrypt command."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        decrypted_csv = temp_dir / "decrypted.csv"

        # First, generate encrypted tokens
        encrypt_args = [
            "package",
            "-i", str(input_csv),
            "-t", "csv",
            "-o", str(output_csv),
            "--hashingsecret", self.HASHING_SECRET,
            "--encryptionkey", self.ENCRYPTION_KEY
        ]
        OpenTokenCommand.execute(encrypt_args)

        # Now decrypt them
        decrypt_args = [
            "decrypt",
            "-i", str(output_csv),
            "-t", "csv",
            "-o", str(decrypted_csv),
            "--encryptionkey", self.ENCRYPTION_KEY
        ]

        exit_code = OpenTokenCommand.execute(decrypt_args)

        assert exit_code == 0, "Command should execute successfully"
        assert decrypted_csv.exists(), "Decrypted CSV should be created"
        assert decrypted_csv.stat().st_size > 0, "Decrypted CSV should not be empty"

    def test_output_type_defaults_to_input_type(self, temp_dir):
        """Test that output type defaults to input type when not specified."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"

        args = [
            "package",
            "-i", str(input_csv),
            "-t", "csv",
            "-o", str(output_csv),
            "--hashingsecret", self.HASHING_SECRET,
            "--encryptionkey", self.ENCRYPTION_KEY
        ]

        exit_code = OpenTokenCommand.execute(args)

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

        # First create a parquet file from CSV
        create_args = [
            "package",
            "-i", str(input_csv),
            "-t", "csv",
            "-o", str(temp_parquet),
            "-ot", "parquet",
            "--hashingsecret", self.HASHING_SECRET,
            "--encryptionkey", self.ENCRYPTION_KEY
        ]
        OpenTokenCommand.execute(create_args)

        # Now use parquet as input
        args = [
            "decrypt",
            "-i", str(temp_parquet),
            "-t", "parquet",
            "-o", str(output_parquet),
            "--encryptionkey", self.ENCRYPTION_KEY
        ]

        exit_code = OpenTokenCommand.execute(args)
        assert exit_code == 0, "Command should execute successfully"

    def test_decrypt_csv_to_parquet(self, temp_dir):
        """Test decrypting CSV to Parquet format."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"
        decrypted_parquet = temp_dir / "decrypted.parquet"

        # First generate encrypted tokens
        encrypt_args = [
            "package",
            "-i", str(input_csv),
            "-t", "csv",
            "-o", str(output_csv),
            "--hashingsecret", self.HASHING_SECRET,
            "--encryptionkey", self.ENCRYPTION_KEY
        ]
        OpenTokenCommand.execute(encrypt_args)

        # Decrypt CSV to Parquet
        decrypt_args = [
            "decrypt",
            "-i", str(output_csv),
            "-t", "csv",
            "-o", str(decrypted_parquet),
            "-ot", "parquet",
            "--encryptionkey", self.ENCRYPTION_KEY
        ]

        exit_code = OpenTokenCommand.execute(decrypt_args)
        assert exit_code == 0, "Command should execute successfully"
        assert decrypted_parquet.exists(), "Decrypted Parquet should be created"

    # ===== Negative Test Cases =====

    def test_missing_required_parameter_hashing_secret(self, temp_dir):
        """Test that missing hashingsecret parameter is caught."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"

        args = [
            "tokenize",
            "-i", str(input_csv),
            "-t", "csv",
            "-o", str(output_csv)
            # Missing --hashingsecret
        ]

        exit_code = OpenTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with missing required parameter"

    def test_missing_required_parameter_encryption_key(self, temp_dir):
        """Test that missing encryptionkey parameter is caught."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"

        args = [
            "encrypt",
            "-i", str(input_csv),
            "-t", "csv",
            "-o", str(output_csv)
            # Missing --encryptionkey
        ]

        exit_code = OpenTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with missing required parameter"

    def test_missing_required_parameter_input(self, temp_dir):
        """Test that missing input parameter is caught."""
        output_csv = temp_dir / "output.csv"

        args = [
            "tokenize",
            # Missing -i/--input
            "-t", "csv",
            "-o", str(output_csv),
            "--hashingsecret", self.HASHING_SECRET
        ]

        exit_code = OpenTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with missing required parameter"

    def test_missing_required_parameter_output(self, temp_dir):
        """Test that missing output parameter is caught."""
        input_csv = temp_dir / "input.csv"

        args = [
            "tokenize",
            "-i", str(input_csv),
            "-t", "csv",
            # Missing -o/--output
            "--hashingsecret", self.HASHING_SECRET
        ]

        exit_code = OpenTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with missing required parameter"

    def test_invalid_input_type(self, temp_dir):
        """Test that invalid input type is caught."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"

        args = [
            "tokenize",
            "-i", str(input_csv),
            "-t", "invalid_type",  # Invalid input type
            "-o", str(output_csv),
            "--hashingsecret", self.HASHING_SECRET
        ]

        exit_code = OpenTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with invalid input type"

    def test_invalid_output_type(self, temp_dir):
        """Test that invalid output type is caught."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"

        args = [
            "tokenize",
            "-i", str(input_csv),
            "-t", "csv",
            "-o", str(output_csv),
            "-ot", "invalid_type",  # Invalid output type
            "--hashingsecret", self.HASHING_SECRET
        ]

        exit_code = OpenTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with invalid output type"

    def test_non_existent_input_file(self, temp_dir):
        """Test that non-existent input file is caught."""
        nonexistent_file = temp_dir / "nonexistent.csv"
        output_csv = temp_dir / "output.csv"

        args = [
            "tokenize",
            "-i", str(nonexistent_file),
            "-t", "csv",
            "-o", str(output_csv),
            "--hashingsecret", self.HASHING_SECRET
        ]

        exit_code = OpenTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with non-existent input file"

    def test_package_command_missing_both_secrets(self, temp_dir):
        """Test that package command fails when both secrets are missing."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"

        args = [
            "package",
            "-i", str(input_csv),
            "-t", "csv",
            "-o", str(output_csv)
            # Missing both --hashingsecret and --encryptionkey
        ]

        exit_code = OpenTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with missing required parameters"

    def test_invalid_subcommand(self, temp_dir):
        """Test that invalid subcommand is caught."""
        input_csv = temp_dir / "input.csv"
        output_csv = temp_dir / "output.csv"

        args = [
            "invalid_command",  # Invalid subcommand
            "-i", str(input_csv),
            "-t", "csv",
            "-o", str(output_csv)
        ]

        exit_code = OpenTokenCommand.execute(args)
        assert exit_code != 0, "Command should fail with invalid subcommand"

