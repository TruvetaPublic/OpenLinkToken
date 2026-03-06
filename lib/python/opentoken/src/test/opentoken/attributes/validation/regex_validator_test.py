"""
Tests for RegexValidator.
"""

import pickle

from opentoken.attributes.validation.regex_validator import RegexValidator


class TestRegexValidator:
    """Test cases for RegexValidator."""

    def test_eval_should_return_true_for_matching_pattern(self):
        """Test that eval returns True for matching patterns."""
        validator = RegexValidator(r"^[A-Z]+$")
        assert validator.eval("ABC") is True, "All uppercase letters should match"

    def test_eval_should_return_false_for_non_matching_pattern(self):
        """Test that eval returns False for non-matching patterns."""
        validator = RegexValidator(r"^[A-Z]+$")
        assert validator.eval("abc") is False, "Lowercase letters should not match"
        assert validator.eval("123") is False, "Numbers should not match"

    def test_eval_should_return_false_for_null_value(self):
        """Test that eval returns False for null (None) values."""
        validator = RegexValidator(r".*")
        assert validator.eval(None) is False, "Null value should not match"

    def test_eval_should_return_true_for_empty_string_with_matching_pattern(self):
        """Test that eval returns True for empty strings with matching patterns."""
        validator = RegexValidator(r"^$")
        assert validator.eval("") is True, "Empty string should match"

    def test_eval_should_return_true_for_complex_pattern(self):
        """Test that eval works for complex patterns."""
        validator = RegexValidator(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}$")
        assert validator.eval("test@email.com") is True, "Valid email should match"
        assert validator.eval("invalid-email") is False, "Invalid email should not match"

    def test_constructor_should_compile_pattern(self):
        """Test that the constructor compiles the pattern."""
        validator = RegexValidator(r"test")
        assert validator.compiled_pattern is not None, "Pattern should be compiled"
        assert validator.compiled_pattern.pattern == "test", "Pattern should be the same as input"

    def test_serialization_should_preserve_state(self):
        """Test serialization and deserialization of the validator."""
        original_validator = RegexValidator(r"^[A-Z]+$")

        # Serialize the validator using pickle
        serialized_data = pickle.dumps(original_validator)

        # Deserialize the validator
        deserialized_validator = pickle.loads(serialized_data)

        # Test that both validators behave identically
        assert original_validator.compiled_pattern.pattern == deserialized_validator.compiled_pattern.pattern, (
            "Compiled patterns should match after deserialization"
        )
