"""
Tests for StringAttribute.
"""

import pickle
import threading

import pytest

from openlinktoken.attributes.general.string_attribute import StringAttribute


class TestStringAttribute:
    """Test cases for StringAttribute."""

    @pytest.fixture
    def string_attribute(self):
        """Create a default StringAttribute."""
        return StringAttribute()

    def test_get_name_should_return_string(self, string_attribute):
        """Test that getName returns 'String'."""
        assert string_attribute.get_name() == "String"

    def test_get_aliases_should_return_string_and_text_aliases(self, string_attribute):
        """Test that getAliases returns ['String', 'Text']."""
        assert string_attribute.get_aliases() == ["String", "Text"]

    def test_normalize_valid_string_should_trim_whitespace(self, string_attribute):
        """Test normalization of valid string values."""
        assert string_attribute.normalize("hello") == "hello"
        assert string_attribute.normalize("  hello  ") == "hello"
        assert string_attribute.normalize("  hello world  ") == "hello world"
        assert string_attribute.normalize("\t\ntest\n\t") == "test"
        assert string_attribute.normalize("  a b c  ") == "a b c"

    def test_normalize_string_with_internal_whitespace_should_preserve_it(self, string_attribute):
        """Test that internal whitespace is preserved."""
        assert string_attribute.normalize("  hello  world  ") == "hello  world"
        assert string_attribute.normalize("  test\tvalue  ") == "test\tvalue"

    def test_normalize_null_value_should_raise_exception(self, string_attribute):
        """Test that null values raise exceptions."""
        with pytest.raises(ValueError, match="String value cannot be null"):
            string_attribute.normalize(None)

    def test_validate_valid_strings_should_return_true(self, string_attribute):
        """Test validation of valid string values."""
        assert string_attribute.validate("hello") is True
        assert string_attribute.validate("  hello  ") is True
        assert string_attribute.validate("a") is True
        assert string_attribute.validate("123") is True
        assert string_attribute.validate("hello world") is True
        assert string_attribute.validate("test@example.com") is True

    def test_validate_invalid_strings_should_return_false(self, string_attribute):
        """Test validation of invalid string values."""
        assert string_attribute.validate(None) is False
        assert string_attribute.validate("") is False
        assert string_attribute.validate("   ") is False
        assert string_attribute.validate("\t\n") is False

    def test_normalize_thread_safety(self, string_attribute):
        """Test thread safety of normalize method with barrier-style synchronization."""
        thread_count = 100
        test_string = "  hello world  "
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
                result = string_attribute.normalize(test_string)
                with results_lock:
                    results.append(result)
            except Exception as e:
                pytest.fail(f"Worker thread failed: {e}")

        # Create and start threads
        threads = [threading.Thread(target=normalize_value) for _ in range(thread_count)]
        for thread in threads:
            thread.start()
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=15)

        # Verify all threads got the same result
        assert len(results) == thread_count
        for result in results:
            assert result == "hello world"

    def test_serialization(self, string_attribute):
        """Test serialization and deserialization of the attribute."""
        # Serialize the attribute
        serialized_data = pickle.dumps(string_attribute)

        # Deserialize the attribute
        deserialized_attribute = pickle.loads(serialized_data)

        # Test various string values with both original and deserialized attributes
        test_values = ["hello", "  world  ", "test string", "123", "a", "  trimmed  "]

        for value in test_values:
            assert string_attribute.get_name() == deserialized_attribute.get_name(), "Attribute names should match"

            assert string_attribute.get_aliases() == deserialized_attribute.get_aliases(), (
                "Attribute aliases should match"
            )

            assert string_attribute.normalize(value) == deserialized_attribute.normalize(value), (
                f"Normalization should be identical for value: {value}"
            )

            assert string_attribute.validate(value) == deserialized_attribute.validate(value), (
                f"Validation should be identical for value: {value}"
            )

    def test_normalize_empty_string_after_trim_should_return_empty(self, string_attribute):
        """Test that normalization doesn't fail on whitespace-only strings."""
        # This tests that normalization doesn't fail on whitespace-only strings
        # Validation will fail, but normalization should succeed
        assert string_attribute.normalize("   ") == ""
        assert string_attribute.normalize("\t\n") == ""

    def test_validate_special_characters_should_return_true(self, string_attribute):
        """Test that special characters are valid."""
        # StringAttribute should accept any non-empty string
        assert string_attribute.validate("hello@world.com") is True
        assert string_attribute.validate("test-value_123") is True
        assert string_attribute.validate("!@#$%^&*()") is True
        assert string_attribute.validate("unicode: 你好") is True
