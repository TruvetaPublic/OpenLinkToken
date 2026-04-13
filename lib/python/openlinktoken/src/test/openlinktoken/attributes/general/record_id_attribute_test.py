"""
Copyright (c) Truveta. All rights reserved.
"""

import pickle

import pytest

from openlinktoken.attributes.general.record_id_attribute import RecordIdAttribute


class TestRecordIdAttribute:
    """Test cases for RecordIdAttribute class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.record_id_attribute = RecordIdAttribute()

    def test_get_name_should_return_record_id(self):
        """Test that getName returns 'RecordId'."""
        assert self.record_id_attribute.get_name() == "RecordId"

    def test_get_aliases_should_return_record_id_and_id(self):
        """Test that getAliases returns RecordId and Id."""
        expected_aliases = ["RecordId", "Id"]
        assert self.record_id_attribute.get_aliases() == expected_aliases

    def test_normalize_should_return_unchanged_value(self):
        """Test that normalize returns the input value unchanged."""
        input_value = "test123"
        assert self.record_id_attribute.normalize(input_value) == input_value

    def test_validate_should_not_allow_null_or_empty(self):
        """Test validation rules for null and empty values."""
        # Null value should not be allowed
        assert not self.record_id_attribute.validate(None), "Null value should not be allowed"

        # Empty value should not be allowed
        assert not self.record_id_attribute.validate(""), "Empty value should not be allowed"

        # Whitespace-only value should not be allowed
        assert not self.record_id_attribute.validate("   "), "Whitespace-only value should not be allowed"

        # Non-empty value should be allowed
        assert self.record_id_attribute.validate("test123"), "Non-empty value should be allowed"

    def test_serialization(self):
        """Test serialization and deserialization of RecordIdAttribute."""
        # Serialize the attribute using pickle
        serialized_data = pickle.dumps(self.record_id_attribute)

        # Deserialize the attribute
        deserialized_attribute = pickle.loads(serialized_data)

        # Test various record ID values with both original and deserialized attributes
        test_values = ["test123", "record_001", "ID-12345", "user@domain.com", "a1b2c3d4", "RECORD123", "123abc"]

        for value in test_values:
            # Test that attribute names match
            assert self.record_id_attribute.get_name() == deserialized_attribute.get_name(), (
                "Attribute names should match"
            )

            # Test that attribute aliases match
            assert self.record_id_attribute.get_aliases() == deserialized_attribute.get_aliases(), (
                "Attribute aliases should match"
            )

            # Test that normalization is identical
            assert self.record_id_attribute.normalize(value) == deserialized_attribute.normalize(value), (
                f"Normalization should be identical for value: {value}"
            )

            # Test that validation is identical
            assert self.record_id_attribute.validate(value) == deserialized_attribute.validate(value), (
                f"Validation should be identical for value: {value}"
            )

    @pytest.mark.parametrize(
        "test_value,expected_valid",
        [
            ("test123", True),
            ("record_001", True),
            ("ID-12345", True),
            ("user@domain.com", True),
            ("a1b2c3d4", True),
            ("RECORD123", True),
            ("123abc", True),
            ("", False),
            ("   ", False),
            (None, False),
            ("single_char_id", True),
            ("very_long_record_identifier_with_many_characters", True),
            ("123", True),
            ("abc", True),
        ],
    )
    def test_validate_parametrized(self, test_value, expected_valid):
        """Parametrized test for validation with various inputs."""
        assert self.record_id_attribute.validate(test_value) == expected_valid

    @pytest.mark.parametrize(
        "test_value,expected_normalized",
        [
            ("test123", "test123"),
            ("record_001", "record_001"),
            ("ID-12345", "ID-12345"),
            ("user@domain.com", "user@domain.com"),
            ("a1b2c3d4", "a1b2c3d4"),
            ("RECORD123", "RECORD123"),
            ("123abc", "123abc"),
            ("", ""),
            ("   leading_and_trailing_spaces   ", "leading_and_trailing_spaces"),
        ],
    )
    def test_normalize_parametrized(self, test_value, expected_normalized):
        """Parametrized test for normalization with various inputs."""
        assert self.record_id_attribute.normalize(test_value) == expected_normalized

    def test_aliases_immutability(self):
        """Test that modifying returned aliases doesn't affect the original."""
        aliases = self.record_id_attribute.get_aliases()
        original_length = len(aliases)

        # Try to modify the returned list
        aliases.append("ModifiedAlias")

        # Verify the original aliases are unchanged
        new_aliases = self.record_id_attribute.get_aliases()
        assert len(new_aliases) == original_length
        assert "ModifiedAlias" not in new_aliases

    def test_edge_cases(self):
        """Test edge cases for record ID attribute."""
        # Test with various special characters
        special_cases = [
            "id_with_underscore",
            "id-with-dash",
            "id.with.dot",
            "id@with@at",
            "id with space",
            "id\twith\ttab",
            "id\nwith\nnewline",
            "123456789",
            "ABCDEFGHIJK",
            "MixedCASE123",
        ]

        for case in special_cases:
            # All should be valid (non-empty)
            assert self.record_id_attribute.validate(case), f"Should validate: {case}"
            # All should normalize to themselves
            assert self.record_id_attribute.normalize(case) == case, f"Should normalize to self: {case}"
