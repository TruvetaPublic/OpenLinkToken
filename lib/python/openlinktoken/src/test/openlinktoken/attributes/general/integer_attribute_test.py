# SPDX-License-Identifier: MIT

import pytest

from openlinktoken.attributes.general.integer_attribute import IntegerAttribute


class TestIntegerAttribute:
    """Test cases for IntegerAttribute."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.attribute = IntegerAttribute()

    def test_get_name_should_return_integer(self):
        """Test that get_name returns 'Integer'."""
        assert self.attribute.get_name() == "Integer"

    def test_get_aliases_should_return_integer_alias(self):
        """Test that get_aliases returns list with 'Integer'."""
        aliases = self.attribute.get_aliases()
        assert len(aliases) == 1
        assert "Integer" in aliases

    def test_normalize_valid_integer_should_normalize(self):
        """Test normalization of valid integers."""
        assert self.attribute.normalize("123") == "123"
        assert self.attribute.normalize("0") == "0"
        assert self.attribute.normalize("-456") == "-456"
        assert self.attribute.normalize("  789  ") == "789"
        assert self.attribute.normalize("+123") == "123"

    def test_normalize_null_value_should_raise_error(self):
        """Test that None value raises ValueError."""
        with pytest.raises(ValueError):
            self.attribute.normalize(None)

    def test_normalize_invalid_integer_should_raise_error(self):
        """Test that invalid integers raise ValueError."""
        with pytest.raises(ValueError):
            self.attribute.normalize("abc")
        with pytest.raises(ValueError):
            self.attribute.normalize("12.34")
        with pytest.raises(ValueError):
            self.attribute.normalize("")

    def test_validate_valid_integer_should_return_true(self):
        """Test that valid integers validate successfully."""
        assert self.attribute.validate("123") is True
        assert self.attribute.validate("0") is True
        assert self.attribute.validate("-456") is True
        assert self.attribute.validate("  789  ") is True
        assert self.attribute.validate("+123") is True

    def test_validate_invalid_integer_should_return_false(self):
        """Test that invalid integers fail validation."""
        assert self.attribute.validate(None) is False
        assert self.attribute.validate("") is False
        assert self.attribute.validate("abc") is False
        assert self.attribute.validate("12.34") is False
        assert self.attribute.validate("1.0e10") is False

    def test_normalize_boundary_values_should_normalize(self):
        """Test normalization of boundary values."""
        assert self.attribute.normalize("0") == "0"
        assert self.attribute.normalize("-2147483648") == "-2147483648"
        assert self.attribute.normalize("2147483647") == "2147483647"

    def test_validate_large_integers_should_return_true(self):
        """Test that large integers validate successfully."""
        assert self.attribute.validate("9223372036854775807") is True
        assert self.attribute.validate("-9223372036854775808") is True
