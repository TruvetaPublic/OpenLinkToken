# SPDX-License-Identifier: MIT


from openlinktoken.attributes.field_registry import FieldRegistry
from openlinktoken.attributes.general.string_attribute import StringAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute


class TestFieldRegistry:
    """Test cases for FieldRegistry."""

    def test_create_default_loads_built_in_attributes(self):
        """Test that create_default populates the registry with built-in attributes."""
        registry = FieldRegistry.create_default()
        assert registry.size() > 0
        assert "FirstName" in registry.get_field_ids()
        assert "LastName" in registry.get_field_ids()
        assert "String" in registry.get_field_ids()

    def test_get_attribute_returns_registered_instance(self):
        """Test resolving an attribute by field ID."""
        registry = FieldRegistry.create_default()
        attribute = registry.get_attribute("FirstName")
        assert attribute is not None
        assert attribute.get_name() == "FirstName"

    def test_get_attribute_returns_none_for_unknown_field(self):
        """Test that unknown field IDs return None."""
        registry = FieldRegistry.create_default()
        attribute = registry.get_attribute("NonExistent")
        assert attribute is None

    def test_get_field_returns_attribute_field(self):
        """Test resolving an AttributeField by field ID."""
        registry = FieldRegistry.create_default()
        field = registry.get_field("LastName")
        assert field is not None
        assert field.field_id == "LastName"
        assert field.attribute_class == LastNameAttribute

    def test_builder_registers_custom_field(self):
        """Test that the builder can register custom fields with shared attribute types."""
        attribute = StringAttribute()
        registry = (
            FieldRegistry.Builder.from_defaults()
            .register("MotherLastName", StringAttribute, attribute)
            .register("FatherLastName", StringAttribute, attribute)
            .build()
        )

        assert "MotherLastName" in registry.get_field_ids()
        assert "FatherLastName" in registry.get_field_ids()

        mother_attr = registry.get_attribute("MotherLastName")
        father_attr = registry.get_attribute("FatherLastName")
        assert mother_attr is attribute
        assert father_attr is attribute

    def test_builder_from_defaults_includes_built_ins(self):
        """Test that from_defaults pre-populates built-in attributes."""
        registry = FieldRegistry.Builder.from_defaults().build()
        assert "FirstName" in registry.get_field_ids()
        assert "LastName" in registry.get_field_ids()

    def test_multiple_fields_same_attribute_type(self):
        """Test that multiple fields can share the same attribute type."""
        string_attr = StringAttribute()
        registry = (
            FieldRegistry.Builder()
            .register("Field1", StringAttribute, string_attr)
            .register("Field2", StringAttribute, string_attr)
            .register("Field3", StringAttribute, string_attr)
            .build()
        )

        assert registry.size() == 3
        assert registry.get_field("Field1") is not None
        assert registry.get_field("Field2") is not None
        assert registry.get_field("Field3") is not None
        assert registry.get_attribute("Field1") is not None
        assert registry.get_attribute("Field2") is not None
        assert registry.get_attribute("Field3") is not None
