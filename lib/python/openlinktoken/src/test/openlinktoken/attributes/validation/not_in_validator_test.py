"""
Tests for NotInValidator.
"""

import pickle

from openlinktoken.attributes.validation.not_in_validator import NotInValidator


class TestNotInValidator:
    """Test cases for NotInValidator."""

    def test_null_value(self):
        """Test that null (None) values are not allowed."""
        validator = NotInValidator({"invalid"})
        assert validator.eval(None) is False, "Null value should not be allowed"

    def test_empty_invalid_values(self):
        """Test that an empty set allows any value."""
        validator = NotInValidator(set())
        assert validator.eval("value") is True, "Empty sets should allow any value"

    def test_value_not_in_invalid_list(self):
        """Test that values not in the invalid list are allowed."""
        validator = NotInValidator({"invalid"})
        assert validator.eval("valid") is True, "Values not in the invalid list should be allowed"

    def test_value_in_invalid_list(self):
        """Test that values in the invalid list are not allowed."""
        validator = NotInValidator({"invalid"})
        assert validator.eval("invalid") is False, "Values in the invalid list should not be allowed"

    def test_multiple_invalid_values(self):
        """Test that multiple invalid values are handled correctly."""
        validator = NotInValidator({"invalid1", "invalid2", "invalid3"})
        assert validator.eval("valid") is True, "Values not in the invalid list should be allowed"
        assert validator.eval("invalid1") is False, "Values in the invalid list should not be allowed"
        assert validator.eval("invalid2") is False, "Values in the invalid list should not be allowed"
        assert validator.eval("invalid3") is False, "Values in the invalid list should not be allowed"

    def test_serialization(self):
        """Test serialization and deserialization of the validator."""
        validator = NotInValidator({"invalid1", "invalid2"})

        # Serialize the validator using pickle
        serialized_data = pickle.dumps(validator)

        # Deserialize the validator
        deserialized_validator = pickle.loads(serialized_data)

        # Test that both validators behave identically
        assert validator.eval("valid") == deserialized_validator.eval("valid"), (
            "Validation results should match for 'valid'"
        )
        assert deserialized_validator.eval("invalid1") is False, "Deserialized validator should not allow 'invalid1'"
        assert deserialized_validator.eval("invalid2") is False, "Deserialized validator should not allow 'invalid2'"
