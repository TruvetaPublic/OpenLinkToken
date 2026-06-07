"""
Copyright (c) Truveta. All rights reserved.

Integration tests for the main module.
"""

import os
import pytest
import tempfile
from pathlib import Path

from opentoken_cli.main import (
    main,
    _load_command_line_arguments,
    _mask_string,
    _resolve_output_path,
    _create_person_attributes_reader,
    _create_person_attributes_writer,
    _create_token_reader,
    _create_token_writer,
)
from opentoken_cli.command_line_arguments import CommandLineArguments
from unittest.mock import patch


class TestMainHelperFunctions:
    """Unit tests for main module helper functions."""

    def test_mask_string_with_long_string(self):
        """Test masking a long string shows first 3 chars."""
        result = _mask_string("TestSecretValue")
        assert result == "Tes************"

    def test_mask_string_with_short_string(self):
        """Test masking a short string returns unchanged."""
        result = _mask_string("abc")
        assert result == "abc"

    def test_mask_string_with_none(self):
        """Test masking None returns None."""
        result = _mask_string(None)
        assert result is None

    def test_load_command_line_arguments(self):
        """Test loading command line arguments."""
        args = ["-i", "input.csv", "-t", "csv"]
        result = _load_command_line_arguments(args)
        
        assert isinstance(result, CommandLineArguments)
        assert result.input_path == "input.csv"
        assert result.input_type == "csv"
        assert result.output_path == ""

    def test_resolve_output_path_tokenized_csv_default(self):
        """Test deriving default output path for token generation."""
        result = _resolve_output_path("/tmp/input.csv", "", "csv", False)
        assert result == "/tmp/input_tokenized.csv"

    def test_resolve_output_path_decrypted_parquet_override(self):
        """Test deriving default output path for decryption with parquet output."""
        result = _resolve_output_path("/tmp/input.csv", "", "parquet", True)
        assert result == "/tmp/input_decrypted.parquet"


class TestReaderWriterFactories:
    """Tests for reader/writer factory functions."""

    def test_create_person_attributes_reader_csv(self, tmp_path):
        """Test creating CSV person attributes reader."""
        # Create test CSV file
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("RecordId,FirstName,LastName\nrec-1,John,Doe\n")
        
        reader = _create_person_attributes_reader(str(csv_file), "csv")
        assert reader is not None
        reader.close()

    def test_create_person_attributes_reader_invalid_type(self, tmp_path):
        """Test that invalid type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported input type"):
            _create_person_attributes_reader("/path/to/file", "invalid")

    def test_create_person_attributes_writer_csv(self, tmp_path):
        """Test creating CSV person attributes writer."""
        output_file = tmp_path / "output.csv"
        
        writer = _create_person_attributes_writer(str(output_file), "csv")
        assert writer is not None
        writer.close()

    def test_create_person_attributes_writer_invalid_type(self):
        """Test that invalid output type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported output type"):
            _create_person_attributes_writer("/path/to/file", "invalid")

    def test_create_token_reader_csv(self, tmp_path):
        """Test creating CSV token reader."""
        # Create test CSV file with token format
        csv_file = tmp_path / "tokens.csv"
        csv_file.write_text("RuleId,Token,RecordId\nT1,token123,rec-1\n")
        
        reader = _create_token_reader(str(csv_file), "csv")
        assert reader is not None
        reader.close()

    def test_create_token_reader_invalid_type(self):
        """Test that invalid input type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported input type"):
            _create_token_reader("/path/to/file", "invalid")

    def test_create_token_writer_csv(self, tmp_path):
        """Test creating CSV token writer."""
        output_file = tmp_path / "output_tokens.csv"
        
        writer = _create_token_writer(str(output_file), "csv")
        assert writer is not None
        writer.close()

    def test_create_token_writer_invalid_type(self):
        """Test that invalid output type raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported output type"):
            _create_token_writer("/path/to/file", "invalid")


class TestMainIntegration:
    """Integration tests for the main function."""

    HASHING_SECRET = "TestHashingSecret"
    ENCRYPTION_KEY = "TestEncryptionKeyValue1234567890"  # Must be 32 chars

    @pytest.fixture
    def temp_input_csv(self, tmp_path):
        """Create a temporary input CSV file."""
        csv_file = tmp_path / "input.csv"
        csv_content = "RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber\n"
        csv_content += "test-001,John,Doe,98004,Male,2000-01-01,123-45-6789\n"
        csv_content += "test-002,Jane,Smith,12345,Female,1990-05-15,234-56-7890\n"
        csv_file.write_text(csv_content)
        return csv_file

    def test_main_token_generation_csv_to_csv(self, temp_input_csv, tmp_path):
        """Test token generation from CSV to CSV."""
        output_file = tmp_path / "output.csv"
        
        with patch('sys.argv', [
            'main.py',
            '-i', str(temp_input_csv),
            '-t', 'csv',
            '-o', str(output_file),
            '-h', self.HASHING_SECRET,
            '-e', self.ENCRYPTION_KEY
        ]):
            main()
        
        assert output_file.exists()
        assert output_file.stat().st_size > 0
        
        # Check metadata file
        metadata_file = tmp_path / "output.metadata.json"
        assert metadata_file.exists()

    def test_main_hash_only_mode(self, temp_input_csv, tmp_path):
        """Test hash-only mode generates tokens without encryption."""
        output_file = tmp_path / "output.csv"
        
        with patch('sys.argv', [
            'main.py',
            '-i', str(temp_input_csv),
            '-t', 'csv',
            '-o', str(output_file),
            '-h', self.HASHING_SECRET,
            '--hash-only'
        ]):
            main()
        
        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_main_invalid_input_type(self, temp_input_csv, tmp_path, caplog):
        """Test that invalid input type logs error."""
        output_file = tmp_path / "output.csv"
        
        with patch('sys.argv', [
            'main.py',
            '-i', str(temp_input_csv),
            '-t', 'invalid',
            '-o', str(output_file),
            '-h', self.HASHING_SECRET,
            '-e', self.ENCRYPTION_KEY
        ]):
            main()
        
        # Should not create output file
        assert not output_file.exists()

    def test_main_invalid_output_type(self, temp_input_csv, tmp_path, caplog):
        """Test that invalid output type logs error."""
        output_file = tmp_path / "output.csv"
        
        with patch('sys.argv', [
            'main.py',
            '-i', str(temp_input_csv),
            '-t', 'csv',
            '-o', str(output_file),
            '-ot', 'invalid',
            '-h', self.HASHING_SECRET,
            '-e', self.ENCRYPTION_KEY
        ]):
            main()
        
        # Should not create output file  
        assert not output_file.exists()

    def test_main_missing_hashing_secret(self, temp_input_csv, tmp_path, caplog):
        """Test that missing hashing secret logs error."""
        output_file = tmp_path / "output.csv"
        
        with patch('sys.argv', [
            'main.py',
            '-i', str(temp_input_csv),
            '-t', 'csv',
            '-o', str(output_file),
            '-e', self.ENCRYPTION_KEY
        ]):
            main()
        
        # Should not create output file
        assert not output_file.exists()

    def test_main_missing_encryption_key_without_hash_only(self, temp_input_csv, tmp_path, caplog):
        """Test that missing encryption key without hash-only logs error."""
        output_file = tmp_path / "output.csv"
        
        with patch('sys.argv', [
            'main.py',
            '-i', str(temp_input_csv),
            '-t', 'csv',
            '-o', str(output_file),
            '-h', self.HASHING_SECRET
        ]):
            main()
        
        # Should not create output file
        assert not output_file.exists()

    def test_main_decrypt_mode(self, tmp_path):
        """Test decrypt mode with encrypted tokens."""
        # First generate encrypted tokens
        input_file = tmp_path / "input.csv"
        input_file.write_text(
            "RecordId,FirstName,LastName,BirthDate,SocialSecurityNumber\n"
            "rec-1,John,Doe,2000-01-01,123-45-6789\n"
        )
        encrypted_output = tmp_path / "encrypted.csv"
        
        with patch('sys.argv', [
            'main.py',
            '-i', str(input_file),
            '-t', 'csv',
            '-o', str(encrypted_output),
            '-h', self.HASHING_SECRET,
            '-e', self.ENCRYPTION_KEY
        ]):
            main()
        
        assert encrypted_output.exists()
        
        # Now decrypt the tokens
        decrypted_output = tmp_path / "decrypted.csv"
        
        with patch('sys.argv', [
            'main.py',
            '-i', str(encrypted_output),
            '-t', 'csv',
            '-o', str(decrypted_output),
            '-d',
            '-e', self.ENCRYPTION_KEY
        ]):
            main()
        
        assert decrypted_output.exists()
        assert decrypted_output.stat().st_size > 0

    def test_main_decrypt_mode_missing_encryption_key(self, tmp_path, caplog):
        """Test that decrypt mode without encryption key logs error."""
        # Create dummy encrypted tokens file
        tokens_file = tmp_path / "tokens.csv"
        tokens_file.write_text("RuleId,Token,RecordId\nT1,token123,rec-1\n")
        output_file = tmp_path / "output.csv"
        
        with patch('sys.argv', [
            'main.py',
            '-i', str(tokens_file),
            '-t', 'csv',
            '-o', str(output_file),
            '-d'
        ]):
            main()
        
        # Should not create output file
        assert not output_file.exists()

    def test_main_output_type_defaults_to_input_type(self, temp_input_csv, tmp_path):
        """Test that output type defaults to input type when not specified."""
        output_file = tmp_path / "output.csv"
        
        with patch('sys.argv', [
            'main.py',
            '-i', str(temp_input_csv),
            '-t', 'csv',
            '-o', str(output_file),
            # No -ot specified, should default to csv
            '-h', self.HASHING_SECRET,
            '-e', self.ENCRYPTION_KEY
        ]):
            main()
        
        assert output_file.exists()

    def test_main_token_generation_defaults_output_path(self, temp_input_csv):
        """Test token generation derives a default output path when omitted."""
        default_output = temp_input_csv.with_name("input_tokenized.csv")

        with patch('sys.argv', [
            'main.py',
            '-i', str(temp_input_csv),
            '-t', 'csv',
            '-h', self.HASHING_SECRET,
            '-e', self.ENCRYPTION_KEY
        ]):
            main()

        assert default_output.exists()
        assert default_output.stat().st_size > 0
        assert temp_input_csv.with_name("input_tokenized.metadata.json").exists()

    def test_main_token_generation_defaults_output_path_with_output_type_override(self, temp_input_csv):
        """Test derived output path uses the requested output type extension."""
        default_output = temp_input_csv.with_name("input_tokenized.parquet")

        with patch('sys.argv', [
            'main.py',
            '-i', str(temp_input_csv),
            '-t', 'csv',
            '-ot', 'parquet',
            '-h', self.HASHING_SECRET,
            '-e', self.ENCRYPTION_KEY
        ]):
            main()

        assert default_output.exists()

    def test_main_decrypt_mode_defaults_output_path(self, tmp_path):
        """Test decrypt mode derives a default output path when omitted."""
        input_file = tmp_path / "input.csv"
        input_file.write_text(
            "RecordId,FirstName,LastName,BirthDate,SocialSecurityNumber\n"
            "rec-1,John,Doe,2000-01-01,123-45-6789\n"
        )
        encrypted_output = tmp_path / "encrypted.csv"

        with patch('sys.argv', [
            'main.py',
            '-i', str(input_file),
            '-t', 'csv',
            '-o', str(encrypted_output),
            '-h', self.HASHING_SECRET,
            '-e', self.ENCRYPTION_KEY
        ]):
            main()

        with patch('sys.argv', [
            'main.py',
            '-i', str(encrypted_output),
            '-t', 'csv',
            '-d',
            '-e', self.ENCRYPTION_KEY
        ]):
            main()

        decrypted_output = tmp_path / "encrypted_decrypted.csv"
        assert decrypted_output.exists()
