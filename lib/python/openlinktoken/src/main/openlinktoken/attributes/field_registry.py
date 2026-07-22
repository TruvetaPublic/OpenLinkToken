# SPDX-License-Identifier: MIT

from typing import Dict, Optional, Set, Type

from openlinktoken.attributes.attribute import Attribute
from openlinktoken.attributes.attribute_field import AttributeField
from openlinktoken.attributes.attribute_loader import AttributeLoader


class FieldRegistry:
    """
    Registry mapping field identifiers to their corresponding Attribute instances.

    The FieldRegistry is the resolution layer that connects field identifiers
    (string keys used in person-attribute maps) to the attribute instances that provide
    normalization and validation behavior.

    Built-in attributes are auto-registered using their canonical name as the field ID.
    Config-driven fields can register additional mappings (e.g., "MotherLastName" → StringAttribute).
    """

    def __init__(self, fields: Dict[str, AttributeField], field_to_attribute: Dict[str, Attribute]):
        """
        Initialize a FieldRegistry with the given mappings.

        Use FieldRegistry.create_default() or FieldRegistry.Builder for construction.

        Args:
            fields: Mapping of field ID to AttributeField.
            field_to_attribute: Mapping of field ID to Attribute instance.
        """
        self._fields: Dict[str, AttributeField] = dict(fields)
        self._field_to_attribute: Dict[str, Attribute] = dict(field_to_attribute)

    @classmethod
    def create_default(cls) -> "FieldRegistry":
        """
        Create a default registry populated with all built-in attributes.

        Each attribute is registered using its canonical name (from get_name()) as the field ID.

        Returns:
            A new registry with built-in attribute registrations.
        """
        builder = cls.Builder()
        for attribute in AttributeLoader.load():
            builder.register(attribute.get_name(), type(attribute), attribute)
        return builder.build()

    def get_attribute(self, field_id: str) -> Optional[Attribute]:
        """
        Resolve the attribute instance for a given field ID.

        Args:
            field_id: The field identifier.

        Returns:
            The attribute if registered, None otherwise.
        """
        return self._field_to_attribute.get(field_id)

    def get_field(self, field_id: str) -> Optional[AttributeField]:
        """
        Resolve the attribute field definition for a given field ID.

        Args:
            field_id: The field identifier.

        Returns:
            The AttributeField if registered, None otherwise.
        """
        return self._fields.get(field_id)

    def get_field_ids(self) -> Set[str]:
        """
        Return all registered field IDs.

        Returns:
            A set of field identifiers.
        """
        return set(self._fields.keys())

    def size(self) -> int:
        """
        Return the number of registered fields.

        Returns:
            The registry size.
        """
        return len(self._fields)

    class Builder:
        """Builder for constructing a FieldRegistry with custom registrations."""

        def __init__(self):
            self._fields: Dict[str, AttributeField] = {}
            self._field_to_attribute: Dict[str, Attribute] = {}

        @classmethod
        def from_defaults(cls) -> "FieldRegistry.Builder":
            """
            Create a builder pre-populated with all built-in attribute registrations.

            Returns:
                A new builder with defaults loaded.
            """
            builder = cls()
            for attribute in AttributeLoader.load():
                builder.register(attribute.get_name(), type(attribute), attribute)
            return builder

        def register(
            self, field_id: str, attribute_class: Type[Attribute], attribute: Attribute
        ) -> "FieldRegistry.Builder":
            """
            Register a field ID with its attribute class and instance.

            Args:
                field_id: The unique field identifier.
                attribute_class: The attribute class providing behavior.
                attribute: The attribute instance for normalization/validation.

            Returns:
                This builder for chaining.
            """
            self._fields[field_id] = AttributeField(field_id, attribute_class)
            self._field_to_attribute[field_id] = attribute
            return self

        def build(self) -> "FieldRegistry":
            """
            Build an immutable FieldRegistry from the current registrations.

            Returns:
                The constructed registry.
            """
            return FieldRegistry(self._fields, self._field_to_attribute)
