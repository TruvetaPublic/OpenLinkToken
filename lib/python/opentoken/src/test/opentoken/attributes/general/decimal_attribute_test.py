"""
Copyright (c) Truveta. All rights reserved.
"""

import pytest

from opentoken.attributes.general.decimal_attribute import DecimalAttribute


class TestDecimalAttribute:
    """Test cases for DecimalAttribute."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.attribute = DecimalAttribute()

    def test_get_name_should_return_decimal(self):
        """Test that get_name returns 'Decimal'."""
        assert self.attribute.get_name() == "Decimal"

    def test_get_aliases_should_return_decimal_alias(self):
        """Test that get_aliases returns list with 'Decimal'."""
        aliases = self.attribute.get_aliases()
        assert len(aliases) == 1
        assert "Decimal" in aliases

    def test_normalize_valid_decimal_should_normalize(self):
        """Test normalization of valid decimals."""
        # Use pytest.approx for platform-independent float assertions
        assert float(self.attribute.normalize("123.45")) == pytest.approx(123.45)
        assert float(self.attribute.normalize("0")) == pytest.approx(0.0)
        assert float(self.attribute.normalize("-456.78")) == pytest.approx(-456.78)
        assert float(self.attribute.normalize("  789  ")) == pytest.approx(789.0)
        assert float(self.attribute.normalize("+123.45")) == pytest.approx(123.45)

    def test_normalize_decimal_without_leading_digit_should_normalize(self):
        """Test normalization of decimals without leading digit."""
        assert float(self.attribute.normalize(".5")) == pytest.approx(0.5)

    def test_normalize_decimal_without_trailing_digit_should_normalize(self):
        """Test normalization of decimals without trailing digit."""
        assert float(self.attribute.normalize("1.")) == pytest.approx(1.0)

    def test_normalize_scientific_notation_should_normalize(self):
        """Test normalization of scientific notation."""
        result = float(self.attribute.normalize("1.5e10"))
        assert result == pytest.approx(1.5e10)

        result = float(self.attribute.normalize("-3.14E-2"))
        assert result == pytest.approx(-0.0314, abs=1e-10)

    def test_normalize_null_value_should_raise_error(self):
        """Test that None value raises error."""
        with pytest.raises((TypeError, ValueError)):
            self.attribute.normalize(None)  # type: ignore

    def test_normalize_invalid_decimal_should_raise_error(self):
        """Test that invalid decimals raise ValueError."""
        with pytest.raises(ValueError):
            self.attribute.normalize("abc")
        with pytest.raises(ValueError):
            self.attribute.normalize("")
        with pytest.raises(ValueError):
            self.attribute.normalize("   ")

    def test_validate_valid_decimal_should_return_true(self):
        """Test that valid decimals validate successfully."""
        assert self.attribute.validate("123.45") is True
        assert self.attribute.validate("0") is True
        assert self.attribute.validate("-456.78") is True
        assert self.attribute.validate("  789  ") is True
        assert self.attribute.validate("+123.45") is True
        assert self.attribute.validate(".5") is True
        assert self.attribute.validate("1.") is True
        assert self.attribute.validate("1.5e10") is True
        assert self.attribute.validate("-3.14E-2") is True

    def test_validate_invalid_decimal_should_return_false(self):
        """Test that invalid decimals fail validation."""
        assert self.attribute.validate(None) is False  # type: ignore
        assert self.attribute.validate("") is False
        assert self.attribute.validate("abc") is False
        assert self.attribute.validate("1.2.3") is False

    def test_validate_boundary_values_should_return_true(self):
        """Test that boundary values validate successfully."""
        assert self.attribute.validate("0.0") is True
        assert self.attribute.validate("3.14159265358979") is True
        assert self.attribute.validate("1.0E308") is True  # Near max double
        assert self.attribute.validate("1.0E-308") is True  # Near min positive double
