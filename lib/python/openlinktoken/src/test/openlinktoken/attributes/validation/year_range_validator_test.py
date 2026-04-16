"""
Tests for YearRangeValidator.
"""

import pickle
from datetime import date

import pytest

from openlinktoken.attributes.validation.year_range_validator import YearRangeValidator


class TestYearRangeValidator:
    """Test cases for YearRangeValidator."""

    @pytest.fixture
    def validator(self):
        """Create a default YearRangeValidator."""
        return YearRangeValidator()

    def test_eval_valid_years_should_return_true(self, validator):
        """Test valid year values."""
        current_year = date.today().year

        assert validator.eval("1910") is True, "Year 1910 should be valid"
        assert validator.eval("1950") is True, "Year 1950 should be valid"
        assert validator.eval("1990") is True, "Year 1990 should be valid"
        assert validator.eval("2000") is True, "Year 2000 should be valid"
        assert validator.eval(str(current_year)) is True, "Current year should be valid"
        assert validator.eval("  1980  ") is True, "Year with whitespace should be valid"

    def test_eval_invalid_years_should_return_false(self, validator):
        """Test invalid year values."""
        current_year = date.today().year

        # Out of range
        assert validator.eval("1909") is False, "Year 1909 should be invalid"
        assert validator.eval(str(current_year + 1)) is False, "Future year should be invalid"
        assert validator.eval("2100") is False, "Far future year should be invalid"
        assert validator.eval("1900") is False, "Year before 1910 should be invalid"

        # Invalid format
        assert validator.eval("90") is False, "2-digit year should be invalid"
        assert validator.eval("abc") is False, "Non-numeric year should be invalid"
        assert validator.eval("19a0") is False, "Year with letters should be invalid"
        assert validator.eval("") is False, "Empty string should be invalid"
        assert validator.eval(None) is False, "Null should be invalid"
        assert validator.eval("   ") is False, "Whitespace only should be invalid"

    def test_eval_boundary_values_should_validate_correctly(self, validator):
        """Test boundary values."""
        current_year = date.today().year

        # Lower boundary
        assert validator.eval("1910") is True, "Lower boundary (1910) should be valid"
        assert validator.eval("1909") is False, "Below lower boundary (1909) should be invalid"

        # Upper boundary (current year)
        assert validator.eval(str(current_year)) is True, "Upper boundary (current year) should be valid"
        assert validator.eval(str(current_year + 1)) is False, "Above upper boundary should be invalid"

    def test_serialization(self, validator):
        """Test serialization and deserialization of the validator."""
        # Serialize the validator
        serialized_data = pickle.dumps(validator)

        # Deserialize the validator
        deserialized_validator = pickle.loads(serialized_data)

        # Test that both validators work the same
        test_values = ["1910", "1990", "2000", "1909", str(date.today().year + 1), "abc", ""]

        for value in test_values:
            assert validator.eval(value) == deserialized_validator.eval(value), (
                f"Validation should be identical for value: {value}"
            )
