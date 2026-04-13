"""
Copyright (c) Truveta. All rights reserved.
"""

import pickle
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute


class TestBirthDateAttribute:
    """Test cases for BirthDateAttribute class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.birth_date_attribute = BirthDateAttribute()

    def test_get_name_should_return_birth_date(self):
        """Test that get_name returns 'BirthDate'."""
        assert self.birth_date_attribute.get_name() == "BirthDate"

    def test_get_aliases_should_return_birth_date_alias(self):
        """Test that get_aliases returns BirthDate alias."""
        expected_aliases = ["BirthDate"]
        assert self.birth_date_attribute.get_aliases() == expected_aliases

    def test_normalize_valid_date_formats_should_normalize_to_yyyy_mm_dd(self):
        """Test that normalize converts various date formats to YYYY-MM-DD."""
        # Test various input formats
        assert self.birth_date_attribute.normalize("2023-10-26") == "2023-10-26"
        assert self.birth_date_attribute.normalize("2023/10/26") == "2023-10-26"
        assert self.birth_date_attribute.normalize("10/26/2023") == "2023-10-26"
        assert self.birth_date_attribute.normalize("10-26-2023") == "2023-10-26"
        assert self.birth_date_attribute.normalize("26.10.2023") == "2023-10-26"

    def test_normalize_invalid_date_format_should_raise_value_error(self):
        """Test that normalize raises ValueError for invalid date format."""
        with pytest.raises(ValueError) as exc_info:
            self.birth_date_attribute.normalize("20231026")

        assert "Invalid date format: 20231026" in str(exc_info.value)

    def test_validate_valid_date_should_return_true(self):
        """Test that validate returns True for valid dates."""
        assert self.birth_date_attribute.validate("2023-10-26") is True

    def test_validate_invalid_dates(self):
        """Test validation of various invalid date scenarios."""
        # Test invalid date formats
        assert self.birth_date_attribute.validate("20231026") is False  # Wrong format
        assert self.birth_date_attribute.validate("invalid") is False  # Non-date string
        assert self.birth_date_attribute.validate("") is False  # Empty string
        assert self.birth_date_attribute.validate(None) is False  # None value
        assert self.birth_date_attribute.validate("   ") is False  # Whitespace only

        # Test dates outside reasonable range (if applicable)
        assert self.birth_date_attribute.validate("1800-01-01") is False  # Too old
        assert self.birth_date_attribute.validate("2050-01-01") is False  # Future date

    def test_normalize_thread_safety(self):
        """Test thread safety of normalize method."""
        thread_count = 100
        test_date = "10/26/2023"
        expected_result = "2023-10-26"
        results = []

        def normalize_date():
            """Function to be executed by each thread."""
            try:
                result = self.birth_date_attribute.normalize(test_date)
                return result
            except Exception as e:
                pytest.fail(f"Thread failed with exception: {e}")

        # Use ThreadPoolExecutor for better thread management
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            # Submit all tasks
            futures = [executor.submit(normalize_date) for _ in range(thread_count)]

            # Collect results
            for future in as_completed(futures, timeout=15):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    pytest.fail(f"Thread execution failed: {e}")

        # Verify all threads got the same result
        assert len(results) == thread_count, f"Expected {thread_count} results, got {len(results)}"

        for i, result in enumerate(results):
            assert result == expected_result, f"Thread {i} got unexpected result: {result}"

    def test_normalize_thread_safety_barrier_style(self):
        """Test thread safety using barrier-style synchronization (closer to Java version)."""
        thread_count = 50  # Reduced for faster execution
        test_date = "10/26/2023"
        expected_result = "2023-10-26"
        results = []
        barrier = threading.Barrier(thread_count)
        start_event = threading.Event()

        def worker():
            """Worker function that waits for synchronization."""
            try:
                # Wait for all threads to be ready
                start_event.wait(timeout=10)

                # Synchronize all threads to increase contention
                barrier.wait(timeout=10)

                # Perform normalization
                result = self.birth_date_attribute.normalize(test_date)
                results.append(result)

            except Exception as e:
                pytest.fail(f"Worker thread failed: {e}")

        # Create and start threads
        threads = []
        for i in range(thread_count):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)

        # Start all threads simultaneously
        start_event.set()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=15)
            if thread.is_alive():
                pytest.fail("Thread did not complete in time")

        # Verify results
        assert len(results) == thread_count
        for result in results:
            assert result == expected_result

    def test_serialization(self):
        """Test serialization and deserialization of BirthDateAttribute."""
        # Serialize the attribute using pickle
        serialized_data = pickle.dumps(self.birth_date_attribute)

        # Deserialize the attribute
        deserialized_attribute = pickle.loads(serialized_data)

        # Test various date formats with both original and deserialized attributes
        test_values = [
            "2023-10-26",
            "2023/10/26",
            "10/26/2023",
            "10-26-2023",
            "26.10.2023",
            "1990-01-01",
            "12/31/1999",
            "01-01-2000",
        ]

        for value in test_values:
            # Test that attribute names match
            assert self.birth_date_attribute.get_name() == deserialized_attribute.get_name(), (
                "Attribute names should match"
            )

            # Test that attribute aliases match
            assert self.birth_date_attribute.get_aliases() == deserialized_attribute.get_aliases(), (
                "Attribute aliases should match"
            )

            # Test that normalization is identical
            original_normalized = self.birth_date_attribute.normalize(value)
            deserialized_normalized = deserialized_attribute.normalize(value)
            assert original_normalized == deserialized_normalized, (
                f"Normalization should be identical for value: {value}"
            )

            # Test that validation is identical
            original_valid = self.birth_date_attribute.validate(value)
            deserialized_valid = deserialized_attribute.validate(value)
            assert original_valid == deserialized_valid, f"Validation should be identical for value: {value}"

    @pytest.mark.parametrize(
        "input_date,expected_output",
        [
            ("2023-10-26", "2023-10-26"),
            ("2023/10/26", "2023-10-26"),
            ("10/26/2023", "2023-10-26"),
            ("10-26-2023", "2023-10-26"),
            ("26.10.2023", "2023-10-26"),
            ("1990-01-01", "1990-01-01"),
            ("12/31/1999", "1999-12-31"),
            ("01-01-2000", "2000-01-01"),
            ("2/29/2020", "2020-02-29"),  # Leap year
            ("1/1/2023", "2023-01-01"),  # Single digit month/day
        ],
    )
    def test_normalize_parametrized(self, input_date, expected_output):
        """Parametrized test for normalization with various date formats."""
        assert self.birth_date_attribute.normalize(input_date) == expected_output

    @pytest.mark.parametrize(
        "invalid_date",
        [
            "20231026",  # No separators
            "invalid",  # Non-date string
            "13/32/2023",  # Invalid month/day
            "2023-13-01",  # Invalid month
            "2023-02-30",  # Invalid day for February
            "99/99/99",  # Invalid format
            "",  # Empty string
            "   ",  # Whitespace only
        ],
    )
    def test_normalize_invalid_dates_parametrized(self, invalid_date):
        """Parametrized test for normalization with invalid dates."""
        with pytest.raises(ValueError):
            self.birth_date_attribute.normalize(invalid_date)

    @pytest.mark.parametrize(
        "valid_date",
        [
            "2023-10-26",
            "2023/10/26",
            "10/26/2023",
            "10-26-2023",
            "26.10.2023",
            "1990-01-01",
            "12/31/1999",
            "01-01-2000",
        ],
    )
    def test_validate_valid_dates_parametrized(self, valid_date):
        """Parametrized test for validation with valid dates."""
        assert self.birth_date_attribute.validate(valid_date) is True

    def test_edge_cases(self):
        """Test edge cases for birth date attribute."""
        # Test leap year dates
        assert self.birth_date_attribute.normalize("02/29/2020") == "2020-02-29"
        assert self.birth_date_attribute.validate("02/29/2020") is True

        # Test boundary dates (if range validation is implemented)
        # These tests depend on the actual validation rules in DateRangeValidator

        # Test whitespace handling
        assert self.birth_date_attribute.normalize("  2023-01-01  ") == "2023-01-01"

        # Test case sensitivity (dates should not be case sensitive)
        # This mainly applies to month names if supported, but not applicable for numeric dates
