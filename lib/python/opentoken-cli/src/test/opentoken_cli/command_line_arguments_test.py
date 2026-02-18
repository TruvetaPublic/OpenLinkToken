"""
Copyright (c) Truveta. All rights reserved.

Tests for the CommandLineArguments class.
"""

import pytest
from opentoken_cli.command_line_arguments import CommandLineArguments


class TestCommandLineArguments:
    """Unit tests for CommandLineArguments parsing."""

    def test_parse_required_args(self):
        """Test parsing with only required arguments."""
        args = [
            "-i", "/path/to/input.csv",
            "-t", "csv",
            "-o", "/path/to/output.csv"
        ]
        
        result = CommandLineArguments.parse_args(args)
        
        assert result.input_path == "/path/to/input.csv"
        assert result.input_type == "csv"
        assert result.output_path == "/path/to/output.csv"
        assert result.hashing_secret is None
        assert result.encryption_key is None
        assert result.output_type == ""
        assert result.decrypt is False
        assert result.hash_only is False
        # ring_id should have a default value (UUID)
        assert result.ring_id is not None and len(result.ring_id) > 0

    def test_parse_all_args(self):
        """Test parsing with all arguments provided."""
        args = [
            "-i", "/path/to/input.csv",
            "-t", "csv",
            "-o", "/path/to/output.parquet",
            "-ot", "parquet",
            "-h", "TestHashingSecret",
            "-e", "TestEncryptionKeyValue1234567890"
        ]
        
        result = CommandLineArguments.parse_args(args)
        
        assert result.input_path == "/path/to/input.csv"
        assert result.input_type == "csv"
        assert result.output_path == "/path/to/output.parquet"
        assert result.output_type == "parquet"
        assert result.hashing_secret == "TestHashingSecret"
        assert result.encryption_key == "TestEncryptionKeyValue1234567890"
        assert result.decrypt is False
        assert result.hash_only is False

    def test_parse_long_names(self):
        """Test parsing with long argument names."""
        args = [
            "--input", "/path/to/input.parquet",
            "--type", "parquet",
            "--output", "/path/to/output.csv",
            "--output-type", "csv",
            "--hashingsecret", "HashSecret",
            "--encryptionkey", "EncryptionKeyValue123456789012"
        ]
        
        result = CommandLineArguments.parse_args(args)
        
        assert result.input_path == "/path/to/input.parquet"
        assert result.input_type == "parquet"
        assert result.output_path == "/path/to/output.csv"
        assert result.output_type == "csv"
        assert result.hashing_secret == "HashSecret"
        assert result.encryption_key == "EncryptionKeyValue123456789012"

    def test_parse_decrypt_mode(self):
        """Test parsing with decrypt mode enabled."""
        args = [
            "-i", "/path/to/input.csv",
            "-t", "csv",
            "-o", "/path/to/output.csv",
            "-d",
            "-e", "TestEncryptionKeyValue1234567890"
        ]
        
        result = CommandLineArguments.parse_args(args)
        
        assert result.decrypt is True
        assert result.encryption_key == "TestEncryptionKeyValue1234567890"

    def test_parse_hash_only_mode(self):
        """Test parsing with hash-only mode enabled."""
        args = [
            "-i", "/path/to/input.csv",
            "-t", "csv",
            "-o", "/path/to/output.csv",
            "--hash-only",
            "-h", "TestHashingSecret"
        ]
        
        result = CommandLineArguments.parse_args(args)
        
        assert result.hash_only is True
        assert result.hashing_secret == "TestHashingSecret"
        assert result.encryption_key is None

    def test_missing_required_arg(self):
        """Test that missing required arguments raises error."""
        args = [
            "-i", "/path/to/input.csv",
            "-t", "csv"
            # Missing -o output path
        ]
        
        with pytest.raises(SystemExit):
            CommandLineArguments.parse_args(args)

    def test_type_constants(self):
        """Test the type constants are defined correctly."""
        assert CommandLineArguments.TYPE_CSV == "csv"
        assert CommandLineArguments.TYPE_PARQUET == "parquet"

    def test_java_style_property_accessors(self):
        """Test Java-style property accessors for compatibility."""
        args = [
            "-i", "/path/input.csv",
            "-t", "csv",
            "-o", "/path/output.csv",
            "-ot", "parquet",
            "-h", "hash_secret",
            "-e", "encryption_key_value_32_chars!"
        ]
        
        result = CommandLineArguments.parse_args(args)
        
        # Test Java-style getters (camelCase properties)
        assert result.hashingSecret == "hash_secret"
        assert result.encryptionKey == "encryption_key_value_32_chars!"
        assert result.inputPath == "/path/input.csv"
        assert result.inputType == "csv"
        assert result.outputPath == "/path/output.csv"
        assert result.outputType == "parquet"

    def test_str_representation(self):
        """Test string representation hides secrets."""
        args = [
            "-i", "/path/input.csv",
            "-t", "csv",
            "-o", "/path/output.csv",
            "-h", "my_secret_hash",
            "-e", "my_secret_encryption_key_32char"
        ]
        
        result = CommandLineArguments.parse_args(args)
        result_str = str(result)
        
        # Secrets should be masked as '<set>'
        assert "my_secret_hash" not in result_str
        assert "my_secret_encryption_key_32char" not in result_str
        assert "<set>" in result_str
        assert "/path/input.csv" in result_str

    def test_repr_representation(self):
        """Test repr uses same format as str."""
        args = [
            "-i", "/path/input.csv",
            "-t", "csv",
            "-o", "/path/output.csv"
        ]
        
        result = CommandLineArguments.parse_args(args)
        
        assert repr(result) == str(result)

    def test_default_values(self):
        """Test that default values are set correctly."""
        instance = CommandLineArguments()
        
        assert instance.hashing_secret is None
        assert instance.encryption_key is None
        assert instance.input_type == ""
        assert instance.output_path == ""
        assert instance.output_type == ""
        assert instance.decrypt is False
        assert instance.hash_only is False
        # ring_id should have a default UUID value
        assert instance.ring_id is not None and len(instance.ring_id) > 0

    def test_ring_id_parameter(self):
        """Test parsing with ring-id parameter."""
        args = [
            "-i", "/path/to/input.csv",
            "-t", "csv",
            "-o", "/path/to/output.csv",
            "--ring-id", "test-ring-2026-q1"
        ]
        
        result = CommandLineArguments.parse_args(args)
        
        assert result.ring_id == "test-ring-2026-q1"
        # Test Java-style property accessor
        assert result.ringId == "test-ring-2026-q1"

    def test_parquet_input_type(self):
        """Test parsing with parquet input type."""
        args = [
            "-i", "/path/to/input.parquet",
            "-t", "parquet",
            "-o", "/path/to/output.parquet"
        ]
        
        result = CommandLineArguments.parse_args(args)
        
        assert result.input_type == "parquet"
