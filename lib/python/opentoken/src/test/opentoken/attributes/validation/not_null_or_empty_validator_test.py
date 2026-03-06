"""
Tests for NotNullOrEmptyValidator.
"""

import pickle

from opentoken.attributes.validation.not_null_or_empty_validator import NotNullOrEmptyValidator


class TestNotNullOrEmptyValidator:
    """Test cases for NotNullOrEmptyValidator."""

    def test_valid_values(self):
        """Test valid values."""
        validator = NotNullOrEmptyValidator()

        assert validator.eval("test") is True
        assert validator.eval("123") is True
        assert validator.eval("  test  ") is True
        assert validator.eval("special!@#$") is True
        assert validator.eval("multi\nline") is True

    def test_invalid_values(self):
        """Test invalid values."""
        validator = NotNullOrEmptyValidator()

        assert validator.eval(None) is False, "Null value should not be allowed"
        assert validator.eval("") is False, "Empty value should not be allowed"
        assert validator.eval(" ") is False, "Blank value should not be allowed"
        assert validator.eval("\t") is False, "Tab value should not be allowed"
        assert validator.eval("\n") is False, "Newline value should not be allowed"
        assert validator.eval("\r") is False, "Carriage return value should not be allowed"

    def test_serialization_should_preserve_state(self):
        """Test serialization and deserialization of the validator."""
        original_validator = NotNullOrEmptyValidator()

        # Serialize the validator using pickle
        serialized_data = pickle.dumps(original_validator)

        # Deserialize the validator
        deserialized_validator = pickle.loads(serialized_data)

        # Test that both validators behave the same way
        test_values = ["valid", None, "", " ", "\t", "\n", "test123"]

        for value in test_values:
            original_result = original_validator.eval(value)
            deserialized_result = deserialized_validator.eval(value)

            assert original_result == deserialized_result, (
                f"Validators should behave identically for value: {value} "
                f"(original: {original_result}, deserialized: {deserialized_result})"
            )
