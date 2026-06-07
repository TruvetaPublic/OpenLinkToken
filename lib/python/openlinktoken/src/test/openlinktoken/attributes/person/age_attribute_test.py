"""
Tests for AgeAttribute.
"""

import pickle
import threading

import pytest

from openlinktoken.attributes.person.age_attribute import AgeAttribute


class TestAgeAttribute:
    """Test cases for AgeAttribute."""

    @pytest.fixture
    def age_attribute(self):
        """Create a default AgeAttribute."""
        return AgeAttribute()

    def test_get_name_should_return_age(self, age_attribute):
        """Test that getName returns 'Age'."""
        assert age_attribute.get_name() == "Age"

    def test_get_aliases_should_return_age_alias(self, age_attribute):
        """Test that getAliases returns ['Age']."""
        assert age_attribute.get_aliases() == ["Age"]

    def test_normalize_valid_age_should_normalize_to_integer(self, age_attribute):
        """Test normalization of valid age values."""
        assert age_attribute.normalize("25") == "25"
        assert age_attribute.normalize("0") == "0"
        assert age_attribute.normalize("120") == "120"
        assert age_attribute.normalize("  42  ") == "42"
        assert age_attribute.normalize("100") == "100"

    def test_normalize_invalid_age_format_should_raise_exception(self, age_attribute):
        """Test that invalid age formats raise exceptions."""
        with pytest.raises(ValueError):
            age_attribute.normalize("25.5")
        with pytest.raises(ValueError):
            age_attribute.normalize("abc")
        with pytest.raises(ValueError):
            age_attribute.normalize("")
        with pytest.raises(ValueError):
            age_attribute.normalize(None)

    def test_validate_valid_age_should_return_true(self, age_attribute):
        """Test validation of valid age values."""
        assert age_attribute.validate("0") is True
        assert age_attribute.validate("25") is True
        assert age_attribute.validate("120") is True
        assert age_attribute.validate("100") is True
        assert age_attribute.validate("  50  ") is True

    def test_validate_invalid_age_should_return_false(self, age_attribute):
        """Test validation of invalid age values."""
        # Out of range
        assert age_attribute.validate("-1") is False
        assert age_attribute.validate("121") is False
        assert age_attribute.validate("200") is False

        # Invalid format
        assert age_attribute.validate("25.5") is False
        assert age_attribute.validate("abc") is False
        assert age_attribute.validate("25a") is False
        assert age_attribute.validate("") is False
        assert age_attribute.validate(None) is False

    def test_normalize_thread_safety(self, age_attribute):
        """Test thread safety of normalize method with barrier-style synchronization."""
        thread_count = 100
        test_age = "  42  "
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
                result = age_attribute.normalize(test_age)
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
            assert result == "42"

    def test_serialization(self, age_attribute):
        """Test serialization and deserialization of the attribute."""
        # Serialize the attribute
        serialized_data = pickle.dumps(age_attribute)

        # Deserialize the attribute
        deserialized_attribute = pickle.loads(serialized_data)

        # Test various age values with both original and deserialized attributes
        test_values = ["0", "25", "50", "100", "120", "  42  ", "65"]

        for value in test_values:
            assert age_attribute.get_name() == deserialized_attribute.get_name(), "Attribute names should match"

            assert age_attribute.get_aliases() == deserialized_attribute.get_aliases(), "Attribute aliases should match"

            assert age_attribute.normalize(value) == deserialized_attribute.normalize(value), (
                f"Normalization should be identical for value: {value}"
            )

            assert age_attribute.validate(value) == deserialized_attribute.validate(value), (
                f"Validation should be identical for value: {value}"
            )

    def test_validate_boundary_values_should_validate_correctly(self, age_attribute):
        """Test boundary value validation."""
        # Lower boundary
        assert age_attribute.validate("0") is True
        assert age_attribute.validate("-1") is False

        # Upper boundary
        assert age_attribute.validate("120") is True
        assert age_attribute.validate("121") is False
