"""
Tests for DateAttribute.
"""

import pickle
import threading

import pytest

from openlinktoken.attributes.general.date_attribute import DateAttribute


class TestDateAttribute:
    """Test cases for DateAttribute."""

    @pytest.fixture
    def date_attribute(self):
        """Create a default DateAttribute."""
        return DateAttribute()

    def test_get_name_should_return_date(self, date_attribute):
        """Test that getName returns 'Date'."""
        assert date_attribute.get_name() == "Date"

    def test_get_aliases_should_return_date_alias(self, date_attribute):
        """Test that getAliases returns ['Date']."""
        assert date_attribute.get_aliases() == ["Date"]

    def test_normalize_valid_date_formats_should_normalize_to_yyyy_mm_dd(self, date_attribute):
        """Test normalization of valid date formats."""
        assert date_attribute.normalize("2023-10-26") == "2023-10-26"
        assert date_attribute.normalize("2023/10/26") == "2023-10-26"
        assert date_attribute.normalize("10/26/2023") == "2023-10-26"
        assert date_attribute.normalize("10-26-2023") == "2023-10-26"
        assert date_attribute.normalize("26.10.2023") == "2023-10-26"

    def test_normalize_iso8601_timestamps_should_normalize_to_yyyy_mm_dd(self, date_attribute):
        """Test normalization of ISO 8601 timestamp formats."""
        assert date_attribute.normalize("1972-08-18T00:00:00.000Z") == "1972-08-18"
        assert date_attribute.normalize("2023-10-26T12:34:56.789Z") == "2023-10-26"
        assert date_attribute.normalize("2023-10-26T12:34:56Z") == "2023-10-26"
        assert date_attribute.normalize("2023-10-26T12:34:56.789+05:30") == "2023-10-26"
        assert date_attribute.normalize("2023-10-26T12:34:56-08:00") == "2023-10-26"

    def test_normalize_invalid_date_format_should_raise_exception(self, date_attribute):
        """Test that invalid date formats raise exceptions."""
        with pytest.raises(ValueError, match="Invalid date format"):
            date_attribute.normalize("20231026")

    def test_validate_valid_date_should_return_true(self, date_attribute):
        """Test validation of valid date values."""
        assert date_attribute.validate("2023-10-26") is True
        assert date_attribute.validate("2023/10/26") is True
        assert date_attribute.validate("10/26/2023") is True
        assert date_attribute.validate("10-26-2023") is True
        assert date_attribute.validate("26.10.2023") is True

    def test_validate_iso8601_timestamps_should_return_true(self, date_attribute):
        """Test validation of ISO 8601 timestamp values."""
        assert date_attribute.validate("1972-08-18T00:00:00.000Z") is True
        assert date_attribute.validate("2023-10-26T12:34:56.789Z") is True
        assert date_attribute.validate("2023-10-26T12:34:56Z") is True
        assert date_attribute.validate("2023-10-26T12:34:56.789+05:30") is True
        assert date_attribute.validate("2023-10-26T12:34:56-08:00") is True

    def test_validate_invalid_date_should_return_false(self, date_attribute):
        """Test validation of invalid date values."""
        assert date_attribute.validate("20231026") is False
        assert date_attribute.validate("invalid-date") is False
        assert date_attribute.validate("2023") is False
        assert date_attribute.validate(None) is False
        assert date_attribute.validate("") is False

    def test_normalize_thread_safety(self, date_attribute):
        """Test thread safety of normalize method with barrier-style synchronization."""
        thread_count = 100
        test_date = "10/26/2023"
        results = []
        results_lock = threading.Lock()
        barrier = threading.Barrier(thread_count)
        start_event = threading.Event()

        def normalize_value():
            try:
                # Wait for the signal to start
                start_event.wait(timeout=10)
                # Wait for all threads to be ready (synchronize at barrier)
                barrier.wait(timeout=10)
                # Perform normalization
                result = date_attribute.normalize(test_date)
                with results_lock:
                    results.append(result)
            except Exception as e:
                pytest.fail(f"Worker thread failed: {e}")

        # Create and start threads
        threads = [threading.Thread(target=normalize_value) for _ in range(thread_count)]
        for thread in threads:
            thread.start()
        # Start all threads simultaneously
        start_event.set()
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=15)

        # Verify all threads got the same result
        assert len(results) == thread_count
        for result in results:
            assert result == "2023-10-26"

    def test_serialization(self, date_attribute):
        """Test serialization and deserialization of the attribute."""
        # Serialize the attribute
        serialized_data = pickle.dumps(date_attribute)

        # Deserialize the attribute
        deserialized_attribute = pickle.loads(serialized_data)

        # Test various date values with both original and deserialized attributes
        test_values = [
            "2023-10-26",
            "2023/10/26",
            "10/26/2023",
            "10-26-2023",
            "26.10.2023",
            "2000-01-01",
            "1990/12/31",
            "12/31/1999",
        ]

        for value in test_values:
            assert date_attribute.get_name() == deserialized_attribute.get_name(), "Attribute names should match"

            assert date_attribute.get_aliases() == deserialized_attribute.get_aliases(), (
                "Attribute aliases should match"
            )

            assert date_attribute.normalize(value) == deserialized_attribute.normalize(value), (
                f"Normalization should be identical for value: {value}"
            )

            assert date_attribute.validate(value) == deserialized_attribute.validate(value), (
                f"Validation should be identical for value: {value}"
            )

    def test_normalize_future_dates_should_normalize(self, date_attribute):
        """Test that future dates are allowed for generic Date."""
        # Unlike BirthDate, generic Date should allow future dates
        assert date_attribute.normalize("2030-12-31") == "2030-12-31"
        assert date_attribute.normalize("01/01/2050") == "2050-01-01"

    def test_normalize_historical_dates_should_normalize(self, date_attribute):
        """Test that historical dates are allowed for generic Date."""
        # Generic Date should allow any historical dates
        assert date_attribute.normalize("1900-01-01") == "1900-01-01"
        assert date_attribute.normalize("12/31/1800") == "1800-12-31"
