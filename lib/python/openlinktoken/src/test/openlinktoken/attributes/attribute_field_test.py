# SPDX-License-Identifier: MIT

import pytest

from openlinktoken.attributes.attribute_field import AttributeField
from openlinktoken.attributes.general.string_attribute import StringAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute


class TestAttributeField:
    """Test cases for AttributeField."""

    def test_constructor(self):
        """Test basic field construction."""
        field = AttributeField("LastName", LastNameAttribute)
        assert field.field_id == "LastName"
        assert field.attribute_class == LastNameAttribute

    def test_constructor_rejects_none_field_id(self):
        """Test that None field_id raises ValueError."""
        with pytest.raises(ValueError, match="field_id must not be None"):
            AttributeField(None, StringAttribute)

    def test_constructor_rejects_none_attribute_class(self):
        """Test that None attribute_class raises ValueError."""
        with pytest.raises(ValueError, match="attribute_class must not be None"):
            AttributeField("Test", None)

    def test_equality_by_field_id(self):
        """Test that equality is determined by field_id only."""
        field1 = AttributeField("Name", StringAttribute)
        field2 = AttributeField("Name", FirstNameAttribute)
        assert field1 == field2
        assert hash(field1) == hash(field2)

    def test_inequality_by_field_id(self):
        """Test that different field_ids produce inequality."""
        field1 = AttributeField("FirstName", StringAttribute)
        field2 = AttributeField("LastName", StringAttribute)
        assert field1 != field2

    def test_repr(self):
        """Test string representation."""
        field = AttributeField("BirthDate", StringAttribute)
        assert "BirthDate" in repr(field)
        assert "StringAttribute" in repr(field)
