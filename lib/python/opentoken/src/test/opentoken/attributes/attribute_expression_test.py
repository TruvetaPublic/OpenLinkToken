"""
Tests for AttributeExpression.
"""

import pytest

from opentoken.attributes.attribute_expression import AttributeExpression
from opentoken.attributes.general.record_id_attribute import RecordIdAttribute
from opentoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute


class TestAttributeExpression:
    """Test cases for AttributeExpression."""

    def test_get_effective_value_with_empty_expression(self):
        """Test effective value with an empty expression."""
        attribute = AttributeExpression(RecordIdAttribute, None)
        value = "random-uuid-string"
        result = attribute.get_effective_value(value)

        assert result == value

    def test_get_effective_value_with_uppercase_expression(self):
        """Test effective value with an uppercase expression."""
        attribute = AttributeExpression(RecordIdAttribute, "U")
        value = "abcd"
        result = attribute.get_effective_value(value)

        assert result == "ABCD"

    def test_get_effective_value_with_trim_expression(self):
        """Test effective value with a trim expression."""
        attribute = AttributeExpression(RecordIdAttribute, "T")
        value = " abcd "
        result = attribute.get_effective_value(value)

        assert result == "abcd"

    def test_get_effective_value_with_substring_expression(self):
        """Test effective value with a substring expression."""
        attribute1 = AttributeExpression(RecordIdAttribute, "s(0,1)")
        attribute2 = AttributeExpression(RecordIdAttribute, "S(3,4)")
        value = "abcd"
        result1 = attribute1.get_effective_value(value)
        result2 = attribute2.get_effective_value(value)

        assert result1 == "a"
        assert result2 == "d"

    def test_get_effective_value_with_substring_out_of_bounds(self):
        """Test effective value with a substring expression that goes out of bounds."""
        attribute1 = AttributeExpression(RecordIdAttribute, "s(0,1)")
        attribute2 = AttributeExpression(RecordIdAttribute, "S(3,16)")
        value = "abcd"
        result1 = attribute1.get_effective_value(value)
        result2 = attribute2.get_effective_value(value)

        assert result1 == "a"
        assert result2 == "d"

    def test_get_effective_value_with_replace_expression(self):
        """Test effective value with a replace expression."""
        attribute1 = AttributeExpression(RecordIdAttribute, "R('/','-')")
        attribute2 = AttributeExpression(RecordIdAttribute, "r('9999','')")
        value = "99/99/9999"
        result1 = attribute1.get_effective_value(value)
        result2 = attribute2.get_effective_value(value)

        assert result1 == "99-99-9999"
        assert result2 == "99/99/"

    def test_get_effective_value_with_match_expression(self):
        """Test effective value with a match expression."""
        attribute = AttributeExpression(SocialSecurityNumberAttribute, "M(\\d+)")
        value = "123-45-6789"
        result = attribute.get_effective_value(value)

        assert result == "123456789"

    def test_get_effective_value_with_multiple_expressions(self):
        """Test effective value with multiple expressions."""
        attribute = AttributeExpression(RecordIdAttribute, "U|T|R('.','')|S(5,7)")
        value = "1234 56th Ave."
        result = attribute.get_effective_value(value)

        assert result == "56"

    def test_invalid_expression_throws(self):
        """Test that invalid expressions throw exceptions."""
        value = "whatever"

        attribute = AttributeExpression(RecordIdAttribute, "R(5,9)")
        with pytest.raises(ValueError):
            attribute.get_effective_value(value)

        attribute = AttributeExpression(RecordIdAttribute, "S('d',9)")
        with pytest.raises(ValueError):
            attribute.get_effective_value(value)
