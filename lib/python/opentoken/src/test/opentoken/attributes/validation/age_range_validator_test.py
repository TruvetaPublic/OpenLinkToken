"""
Tests for AgeRangeValidator.
"""

import pickle

import pytest

from opentoken.attributes.validation.age_range_validator import AgeRangeValidator


class TestAgeRangeValidator:
    """Test cases for AgeRangeValidator."""

    @pytest.fixture
    def validator(self):
        """Create a default AgeRangeValidator."""
        return AgeRangeValidator()

    def test_eval_valid_ages_should_return_true(self, validator):
        """Test valid age values."""
        assert validator.eval("0") is True, "Age 0 should be valid"
        assert validator.eval("25") is True, "Age 25 should be valid"
        assert validator.eval("120") is True, "Age 120 should be valid"
        assert validator.eval("100") is True, "Age 100 should be valid"
        assert validator.eval("  42  ") is True, "Age with whitespace should be valid"

    def test_eval_invalid_ages_should_return_false(self, validator):
        """Test invalid age values."""
        # Out of range
        assert validator.eval("-1") is False, "Negative age should be invalid"
        assert validator.eval("121") is False, "Age 121 should be invalid"
        assert validator.eval("200") is False, "Age 200 should be invalid"
        assert validator.eval("1000") is False, "Age 1000 should be invalid"

        # Invalid format
        assert validator.eval("25.5") is False, "Decimal age should be invalid"
        assert validator.eval("abc") is False, "Non-numeric age should be invalid"
        assert validator.eval("25a") is False, "Age with letters should be invalid"
        assert validator.eval("") is False, "Empty string should be invalid"
        assert validator.eval(None) is False, "Null should be invalid"
        assert validator.eval("   ") is False, "Whitespace only should be invalid"

    def test_eval_boundary_values_should_validate_correctly(self, validator):
        """Test boundary values."""
        # Lower boundary
        assert validator.eval("0") is True, "Lower boundary (0) should be valid"
        assert validator.eval("-1") is False, "Below lower boundary (-1) should be invalid"

        # Upper boundary
        assert validator.eval("120") is True, "Upper boundary (120) should be valid"
        assert validator.eval("121") is False, "Above upper boundary (121) should be invalid"

    def test_serialization(self, validator):
        """Test serialization and deserialization of the validator."""
        # Serialize the validator
        serialized_data = pickle.dumps(validator)

        # Deserialize the validator
        deserialized_validator = pickle.loads(serialized_data)

        # Test that both validators work the same
        test_values = ["0", "25", "120", "-1", "121", "abc", ""]

        for value in test_values:
            assert validator.eval(value) == deserialized_validator.eval(value), (
                f"Validation should be identical for value: {value}"
            )
