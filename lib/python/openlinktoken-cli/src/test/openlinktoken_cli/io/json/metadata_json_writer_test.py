"""
Copyright (c) Truveta. All rights reserved.
"""

import json
import os
import tempfile
from typing import Any, Dict

from openlinktoken.metadata import Metadata
from openlinktoken_cli.io.json.metadata_json_writer import MetadataJsonWriter
from openlinktoken_cli.io.metadata_writer import MetadataWriter


class TestMetadataJsonWriter:
    """
    Tests for the MetadataJsonWriter class.
    This test verifies that the JSON implementation of the MetadataWriter
    correctly writes metadata to a JSON file with the expected format.
    """

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()

        # Initialize default writer and path
        self.default_output_path = os.path.join(self.temp_dir, "default_output.csv")
        self.default_writer = MetadataJsonWriter(self.default_output_path)
        self.default_metadata_file_path = os.path.join(
            self.temp_dir, "default_output" + Metadata.METADATA_FILE_EXTENSION
        )

        # Create a custom output path for testing
        self.custom_output_path = os.path.join(self.temp_dir, "custom_output.csv")
        self.custom_writer = MetadataJsonWriter(self.custom_output_path)
        self.custom_metadata_file_path = os.path.join(self.temp_dir, "custom_output" + Metadata.METADATA_FILE_EXTENSION)

    def teardown_method(self):
        """Clean up test files after each test method."""
        # Delete the test output files if they exist
        if os.path.exists(self.default_metadata_file_path):
            os.remove(self.default_metadata_file_path)
        if os.path.exists(self.custom_metadata_file_path):
            os.remove(self.custom_metadata_file_path)

        # Clean up temp directory
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_metadata_simple_key_values(self):
        """Test writing metadata with simple key-value pairs."""
        # Create a sample metadata map
        metadata_map: Dict[str, Any] = {"key1": "value1", "key2": "value2", "key3": "value3"}

        self.default_writer.write(metadata_map)

        assert os.path.exists(self.default_metadata_file_path), "Metadata file should have been created"

        # Read the JSON file and verify its contents
        with open(self.default_metadata_file_path, "r", encoding="utf-8") as f:
            root = json.load(f)

        # Verify all keys and values were correctly written
        assert root["key1"] == "value1"
        assert root["key2"] == "value2"
        assert root["key3"] == "value3"

    def test_write_metadata_nested_json_values(self):
        """Test writing metadata with nested dictionary values."""
        metadata_map: Dict[str, Any] = {"simpleKey": "simpleValue"}

        # Create a nested dictionary object
        invalid_attributes_map = {"attr1": 10, "attr2": 20}
        metadata_map["InvalidAttributesByType"] = invalid_attributes_map

        self.default_writer.write(metadata_map)

        assert os.path.exists(self.default_metadata_file_path), "Metadata file should have been created"

        # Read the JSON file and verify its contents
        with open(self.default_metadata_file_path, "r", encoding="utf-8") as f:
            root = json.load(f)

        # Verify simple key-value was correctly written
        assert root["simpleKey"] == "simpleValue"

        # Verify nested dictionary was written as a proper JSON object
        nested_json = root["InvalidAttributesByType"]
        assert isinstance(nested_json, dict), "Dictionary should be stored as JSON object"
        assert nested_json["attr1"] == 10, "attr1 should be 10"
        assert nested_json["attr2"] == 20, "attr2 should be 20"

    def test_write_metadata_map_object_value(self):
        """Test writing metadata with dictionary object values."""
        # Create a metadata map with a dictionary object value
        nested_map = {"validAttribute": 5, "anotherAttribute": 15}

        metadata_map: Dict[str, Any] = {"InvalidAttributesByType": nested_map, "TotalRows": 100}

        # Write the metadata - should not raise exception
        self.default_writer.write(metadata_map)

        # Verify the file was created
        assert os.path.exists(self.default_metadata_file_path), "Metadata file should have been created"

        # Read the JSON file and verify the dictionary was handled correctly
        with open(self.default_metadata_file_path, "r", encoding="utf-8") as f:
            root = json.load(f)

        # Verify the dictionary was stored as a proper JSON object
        assert "InvalidAttributesByType" in root, "The dictionary key should exist in the output"
        invalid_attrs = root["InvalidAttributesByType"]
        assert isinstance(invalid_attrs, dict), "Dictionary should be stored as JSON object"
        assert invalid_attrs["validAttribute"] == 5
        assert invalid_attrs["anotherAttribute"] == 15
        assert root["TotalRows"] == 100

    def test_write_metadata_custom_output_path(self):
        """Test writing metadata to a custom output path."""
        # Create a sample metadata map
        metadata_map: Dict[str, Any] = {"key1": "value1", "key2": "value2"}

        # Write metadata using the custom writer
        self.custom_writer.write(metadata_map)

        # Verify the file was created at the custom location
        assert os.path.exists(self.custom_metadata_file_path), (
            "Metadata file should have been created at the custom location"
        )

        # Read and verify the contents
        with open(self.custom_metadata_file_path, "r", encoding="utf-8") as f:
            root = json.load(f)

        assert root["key1"] == "value1"
        assert root["key2"] == "value2"

    def test_write_metadata_creates_directory_if_not_exists(self):
        """Test that the writer creates the output directory if it doesn't exist."""
        # Create a path with a non-existent directory
        nested_output_path = os.path.join(self.temp_dir, "nested", "deeper", "output.csv")
        nested_writer = MetadataJsonWriter(nested_output_path)
        expected_metadata_path = os.path.join(
            self.temp_dir, "nested", "deeper", "output" + Metadata.METADATA_FILE_EXTENSION
        )

        metadata_map: Dict[str, Any] = {"test_key": "test_value"}

        # Write should create the directory structure
        nested_writer.write(metadata_map)

        # Verify the file was created
        assert os.path.exists(expected_metadata_path), "Metadata file should have been created in the nested directory"

        # Clean up
        if os.path.exists(expected_metadata_path):
            os.remove(expected_metadata_path)

    def test_write_metadata_with_special_characters(self):
        """Test writing metadata with special characters and unicode."""
        metadata_map: Dict[str, Any] = {
            "unicode_key": "测试数据",
            "special_chars": "!@#$%^&*()",
            "newlines": "line1\nline2\nline3",
            "quotes": "single\"double'mixed",
        }

        self.default_writer.write(metadata_map)

        assert os.path.exists(self.default_metadata_file_path), "Metadata file should have been created"

        # Read the JSON file and verify special characters are preserved
        with open(self.default_metadata_file_path, "r", encoding="utf-8") as f:
            root = json.load(f)

        assert root["unicode_key"] == "测试数据"
        assert root["special_chars"] == "!@#$%^&*()"
        assert root["newlines"] == "line1\nline2\nline3"
        assert root["quotes"] == "single\"double'mixed"

    def test_write_metadata_empty_map(self):
        """Test writing an empty metadata map."""
        metadata_map: Dict[str, Any] = {}

        self.default_writer.write(metadata_map)

        assert os.path.exists(self.default_metadata_file_path), (
            "Metadata file should have been created even for empty map"
        )

        # Read the JSON file and verify it's a valid empty object
        with open(self.default_metadata_file_path, "r", encoding="utf-8") as f:
            root = json.load(f)

        assert root == {}, "Empty metadata map should result in empty JSON object"

    def test_inheritance_from_metadata_writer(self):
        """Test that MetadataJsonWriter properly inherits from MetadataWriter."""
        assert isinstance(self.default_writer, MetadataWriter), "MetadataJsonWriter should inherit from MetadataWriter"
        assert hasattr(self.default_writer, "write"), "MetadataJsonWriter should have write method"
        assert hasattr(self.default_writer, "output_path"), "MetadataJsonWriter should have output_path attribute"
