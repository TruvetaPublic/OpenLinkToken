"""
Tests for DateRangeValidator.
"""

import pickle
from datetime import date

import pytest

from openlinktoken.attributes.validation.date_range_validator import DateRangeValidator


class TestDateRangeValidator:
    """Test cases for DateRangeValidator."""

    @pytest.fixture
    def validator(self):
        """Create a validator with minimum date set to 1910-01-01."""
        return DateRangeValidator(min_date=date(1910, 1, 1), use_current_as_max=True)

    def test_eval_valid_dates_within_range_should_return_true(self, validator):
        """Test boundary dates that should be valid."""
        # Minimum valid date
        assert validator.eval("1910-01-01") is True
        assert validator.eval("01/01/1910") is True

        # Today's date should be valid
        today = date.today()
        assert validator.eval(today.isoformat()) is True

        # Dates within acceptable range
        assert validator.eval("1950-06-15") is True
        assert validator.eval("12/25/1990") is True
        assert validator.eval("29.02.2000") is True  # Leap year
        assert validator.eval("2000-12-31") is True
        assert validator.eval("01-01-2020") is True

    def test_eval_dates_before_minimum_should_return_false(self, validator):
        """Test dates before 1910-01-01."""
        assert validator.eval("1909-12-31") is False
        assert validator.eval("12/31/1909") is False
        assert validator.eval("1900-01-01") is False
        assert validator.eval("01/01/1900") is False
        assert validator.eval("31.12.1909") is False
        assert validator.eval("1850-06-15") is False

    def test_eval_dates_after_today_should_return_false(self, validator):
        """Test dates after today."""
        from datetime import timedelta

        tomorrow = date.today() + timedelta(days=1)
        next_year = date.today() + timedelta(days=365)

        assert validator.eval(tomorrow.isoformat()) is False
        assert validator.eval(next_year.isoformat()) is False
        assert validator.eval("2030-01-01") is False
        assert validator.eval("01/01/2030") is False
        assert validator.eval("2050-12-25") is False

    def test_eval_invalid_date_formats_should_return_false(self, validator):
        """Test invalid date formats."""
        assert validator.eval("20231026") is False  # No separators
        assert validator.eval("2023-13-01") is False  # Invalid month
        assert validator.eval("2023-02-30") is False  # Invalid day for February
        assert validator.eval("invalid-date") is False
        assert validator.eval("2023/15/45") is False  # Invalid month and day
        assert validator.eval("abc-def-ghi") is False

    def test_eval_null_and_empty_values_should_return_false(self, validator):
        """Test null and empty values."""
        assert validator.eval(None) is False
        assert validator.eval("") is False
        assert validator.eval("   ") is False  # Whitespace only
        assert validator.eval("\t\n") is False

    def test_eval_various_date_formats_should_work_correctly(self, validator):
        """Test all supported formats for the same date."""
        assert validator.eval("1995-07-15") is True  # yyyy-MM-dd
        assert validator.eval("1995/07/15") is True  # yyyy/MM/dd
        assert validator.eval("07/15/1995") is True  # MM/dd/yyyy
        assert validator.eval("07-15-1995") is True  # MM-dd-yyyy
        assert validator.eval("15.07.1995") is True  # dd.MM.yyyy

    def test_eval_leap_year_dates_should_work_correctly(self, validator):
        """Test leap year validation."""
        # Valid leap year dates
        assert validator.eval("2000-02-29") is True  # Year 2000 is a leap year
        assert validator.eval("1996-02-29") is True  # 1996 is a leap year

        # Invalid leap year dates
        assert validator.eval("1900-02-29") is False  # 1900 is not a leap year
        assert validator.eval("2001-02-29") is False  # 2001 is not a leap year

    def test_serialization_should_preserve_validation_behavior(self, validator):
        """Test serialization and deserialization of the validator."""
        # Serialize the validator
        serialized_data = pickle.dumps(validator)

        # Deserialize the validator
        deserialized_validator = pickle.loads(serialized_data)

        # Test that both validators behave identically
        test_values = [
            "1910-01-01",  # Valid boundary
            "1909-12-31",  # Invalid (too old)
            "2030-01-01",  # Invalid (future)
            "1990-06-15",  # Valid middle range
            "invalid-date",  # Invalid format
            None,  # Null value
        ]

        for value in test_values:
            original_result = validator.eval(value)
            deserialized_result = deserialized_validator.eval(value)

            assert original_result == deserialized_result, (
                f"Validation results should match for value: {value} "
                f"(original: {original_result}, deserialized: {deserialized_result})"
            )

    def test_eval_edge_case_dates_should_work_correctly(self, validator):
        """Test edge cases around boundaries."""
        today = date.today()
        from datetime import timedelta

        yesterday = today - timedelta(days=1)
        min_date = date(1910, 1, 1)
        day_before_min_date = min_date - timedelta(days=1)

        # Test edge cases around boundaries
        assert validator.eval(today.isoformat()) is True  # Today should be valid
        assert validator.eval(yesterday.isoformat()) is True  # Yesterday should be valid
        assert validator.eval(min_date.isoformat()) is True  # Minimum date should be valid
        assert validator.eval(day_before_min_date.isoformat()) is False  # Day before minimum should be invalid

    def test_custom_range_with_fixed_min_and_max_should_validate_correctly(self):
        """Test with a fixed date range."""
        min_date = date(2020, 1, 1)
        max_date = date(2023, 12, 31)
        custom_validator = DateRangeValidator(min_date=min_date, max_date=max_date)

        # Valid dates within range
        assert custom_validator.eval("2020-01-01") is True
        assert custom_validator.eval("2021-06-15") is True
        assert custom_validator.eval("2023-12-31") is True

        # Invalid dates outside range
        assert custom_validator.eval("2019-12-31") is False
        assert custom_validator.eval("2024-01-01") is False

    def test_custom_range_with_only_min_date_should_validate_correctly(self):
        """Test with only a minimum date (no maximum)."""
        min_date = date(2000, 1, 1)
        custom_validator = DateRangeValidator(min_date=min_date, max_date=None)

        # Valid dates after minimum
        assert custom_validator.eval("2000-01-01") is True
        assert custom_validator.eval("2020-06-15") is True
        assert custom_validator.eval("2030-12-31") is True  # Future dates should be valid

        # Invalid dates before minimum
        assert custom_validator.eval("1999-12-31") is False

    def test_custom_range_with_only_max_date_should_validate_correctly(self):
        """Test with only a maximum date (no minimum)."""
        max_date = date(2020, 12, 31)
        custom_validator = DateRangeValidator(min_date=None, max_date=max_date)

        # Valid dates before maximum
        assert custom_validator.eval("1900-01-01") is True  # Very old dates should be valid
        assert custom_validator.eval("2020-06-15") is True
        assert custom_validator.eval("2020-12-31") is True

        # Invalid dates after maximum
        assert custom_validator.eval("2021-01-01") is False

    def test_custom_range_with_no_bounds_should_only_validate_parseable(self):
        """Test with no bounds (only validates parseability)."""
        custom_validator = DateRangeValidator(min_date=None, max_date=None)

        # Valid parseable dates (any date)
        assert custom_validator.eval("1800-01-01") is True
        assert custom_validator.eval("2050-12-31") is True
        assert custom_validator.eval("1950-06-15") is True

        # Invalid unparseable dates
        assert custom_validator.eval("invalid-date") is False
        assert custom_validator.eval("2023-13-01") is False
        assert custom_validator.eval(None) is False
