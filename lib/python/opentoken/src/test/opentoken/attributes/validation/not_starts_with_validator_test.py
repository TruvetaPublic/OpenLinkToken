"""
Tests for NotStartsWithValidator.
"""

import pickle

from opentoken.attributes.validation.not_starts_with_validator import NotStartsWithValidator


class TestNotStartsWithValidator:
    """Test cases for NotStartsWithValidator."""

    def test_null_value(self):
        """Test that null (None) values are not allowed."""
        validator = NotStartsWithValidator({"invalid"})
        assert validator.eval(None) is False, "Null value should not be allowed"

    def test_empty_invalid_prefixes(self):
        """Test that an empty set allows any value."""
        validator = NotStartsWithValidator(set())
        assert validator.eval("anyvalue") is True, "Empty prefix sets should allow any value"

    def test_value_not_starting_with_invalid_prefix(self):
        """Test that values not starting with invalid prefixes are allowed."""
        validator = NotStartsWithValidator({"bad"})
        assert validator.eval("goodvalue") is True, "Values not starting with invalid prefixes should be allowed"

    def test_value_starting_with_invalid_prefix(self):
        """Test that values starting with invalid prefixes are not allowed."""
        validator = NotStartsWithValidator({"bad"})
        assert validator.eval("badvalue") is False, "Values starting with invalid prefixes should not be allowed"

    def test_exact_match(self):
        """Test that values exactly matching invalid prefixes are not allowed."""
        validator = NotStartsWithValidator({"bad"})
        assert validator.eval("bad") is False, "Values that exactly match invalid prefixes should not be allowed"

    def test_multiple_invalid_prefixes(self):
        """Test that multiple invalid prefixes are handled correctly."""
        validator = NotStartsWithValidator({"bad", "evil", "wrong"})
        assert validator.eval("goodvalue") is True, "Valid values should be allowed"
        assert validator.eval("badvalue") is False, "Values starting with 'bad' should not be allowed"
        assert validator.eval("evilplan") is False, "Values starting with 'evil' should not be allowed"
        assert validator.eval("wrongway") is False, "Values starting with 'wrong' should not be allowed"
        assert validator.eval("rightway") is True, "Values not starting with any invalid prefix should be allowed"

    def test_case_sensitive(self):
        """Test that validation is case-sensitive."""
        validator = NotStartsWithValidator({"Bad"})
        assert validator.eval("badvalue") is True, "Validation should be case-sensitive"
        assert validator.eval("Badvalue") is False, "Values starting with exact case match should not be allowed"

    def test_empty_string_value(self):
        """Test that empty string values are allowed if they don't start with invalid prefixes."""
        validator = NotStartsWithValidator({"bad"})
        assert validator.eval("") is True, "Empty string should be allowed if it doesn't start with invalid prefix"

    def test_empty_string_prefix(self):
        """Test that empty string as a prefix invalidates all values."""
        validator = NotStartsWithValidator({""})
        assert validator.eval("anyvalue") is False, "Any value should be invalid if empty string is an invalid prefix"
        assert validator.eval("") is False, "Empty string should be invalid if empty string is an invalid prefix"

    def test_serialization(self):
        """Test serialization and deserialization of the validator."""
        validator = NotStartsWithValidator({"bad", "evil"})

        # Serialize the validator using pickle
        serialized_data = pickle.dumps(validator)

        # Deserialize the validator
        deserialized_validator = pickle.loads(serialized_data)

        # Test that both validators behave the same way
        test_values = ["goodvalue", "badvalue", "evilplan", "rightway", "", None]

        for value in test_values:
            original_result = validator.eval(value)
            deserialized_result = deserialized_validator.eval(value)

            assert original_result == deserialized_result, (
                f"Validators should behave identically for value: {value} "
                f"(original: {original_result}, deserialized: {deserialized_result})"
            )

        # Additional specific tests on deserialized validator
        assert deserialized_validator.eval("goodvalue") is True
        assert deserialized_validator.eval("badvalue") is False
        assert deserialized_validator.eval("evilplan") is False
