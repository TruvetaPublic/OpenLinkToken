"""
Tests for BirthYearAttribute.
"""

import pickle
import threading
from datetime import date

import pytest

from opentoken.attributes.person.birth_year_attribute import BirthYearAttribute


class TestBirthYearAttribute:
    """Test cases for BirthYearAttribute."""

    @pytest.fixture
    def birth_year_attribute(self):
        """Create a default BirthYearAttribute."""
        return BirthYearAttribute()

    def test_get_name_should_return_birth_year(self, birth_year_attribute):
        """Test that getName returns 'BirthYear'."""
        assert birth_year_attribute.get_name() == "BirthYear"

    def test_get_aliases_should_return_birth_year_and_year_of_birth_aliases(self, birth_year_attribute):
        """Test that getAliases returns ['BirthYear', 'YearOfBirth']."""
        assert birth_year_attribute.get_aliases() == ["BirthYear", "YearOfBirth"]

    def test_normalize_valid_year_should_normalize_to_integer(self, birth_year_attribute):
        """Test normalization of valid year values."""
        assert birth_year_attribute.normalize("1990") == "1990"
        assert birth_year_attribute.normalize("2000") == "2000"
        assert birth_year_attribute.normalize("  1950  ") == "1950"
        assert birth_year_attribute.normalize("2020") == "2020"

    def test_normalize_invalid_year_format_should_raise_exception(self, birth_year_attribute):
        """Test that invalid year formats raise exceptions."""
        with pytest.raises(ValueError):
            birth_year_attribute.normalize("90")
        with pytest.raises(ValueError):
            birth_year_attribute.normalize("abc")
        with pytest.raises(ValueError):
            birth_year_attribute.normalize("")
        with pytest.raises(ValueError):
            birth_year_attribute.normalize(None)

    def test_validate_valid_year_should_return_true(self, birth_year_attribute):
        """Test validation of valid year values."""
        assert birth_year_attribute.validate("1910") is True
        assert birth_year_attribute.validate("1990") is True
        assert birth_year_attribute.validate("2000") is True
        assert birth_year_attribute.validate(str(date.today().year)) is True
        assert birth_year_attribute.validate("  1980  ") is True

    def test_validate_invalid_year_should_return_false(self, birth_year_attribute):
        """Test validation of invalid year values."""
        # Out of range
        assert birth_year_attribute.validate("1899") is False
        assert birth_year_attribute.validate(str(date.today().year + 1)) is False
        assert birth_year_attribute.validate("2100") is False

        # Invalid format
        assert birth_year_attribute.validate("90") is False
        assert birth_year_attribute.validate("abc") is False
        assert birth_year_attribute.validate("19a0") is False
        assert birth_year_attribute.validate("") is False
        assert birth_year_attribute.validate(None) is False

    def test_normalize_thread_safety(self, birth_year_attribute):
        """Test thread safety of normalize method with barrier-style synchronization."""
        thread_count = 100
        test_year = "  1990  "
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
                result = birth_year_attribute.normalize(test_year)
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
            assert result == "1990"

    def test_serialization(self, birth_year_attribute):
        """Test serialization and deserialization of the attribute."""
        # Serialize the attribute
        serialized_data = pickle.dumps(birth_year_attribute)

        # Deserialize the attribute
        deserialized_attribute = pickle.loads(serialized_data)

        # Test various year values with both original and deserialized attributes
        test_values = ["1910", "1950", "1990", "2000", "2020", "  1980  "]

        for value in test_values:
            assert birth_year_attribute.get_name() == deserialized_attribute.get_name(), "Attribute names should match"

            assert birth_year_attribute.get_aliases() == deserialized_attribute.get_aliases(), (
                "Attribute aliases should match"
            )

            assert birth_year_attribute.normalize(value) == deserialized_attribute.normalize(value), (
                f"Normalization should be identical for value: {value}"
            )

            assert birth_year_attribute.validate(value) == deserialized_attribute.validate(value), (
                f"Validation should be identical for value: {value}"
            )

    def test_validate_boundary_values_should_validate_correctly(self, birth_year_attribute):
        """Test boundary value validation."""
        current_year = date.today().year

        # Lower boundary
        assert birth_year_attribute.validate("1910") is True
        assert birth_year_attribute.validate("1909") is False

        # Upper boundary (current year)
        assert birth_year_attribute.validate(str(current_year)) is True
        assert birth_year_attribute.validate(str(current_year + 1)) is False
