# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from openlinktoken.attributes.attribute import Attribute


class AttributeField:
    """
    Represents a named field slot in a person record.

    An AttributeField separates two concerns that were previously conflated:
    - Field identity: "which value from the person record?" (the field_id)
    - Attribute behavior: "how to normalize/validate?" (the attribute_class)

    This allows multiple fields to share the same attribute type (e.g., two fields
    both using StringAttribute normalization) while remaining distinct keys in the
    person attributes map.
    """

    def __init__(self, field_id: str, attribute_class: Type["Attribute"]):
        """
        Create an attribute field with the given identity and attribute type.

        Args:
            field_id: Unique field identifier (e.g., "LastName", "MotherLastName").
            attribute_class: The attribute class providing normalization and validation behavior.
        """
        if field_id is None:
            raise ValueError("field_id must not be None")
        if attribute_class is None:
            raise ValueError("attribute_class must not be None")
        self._field_id = field_id
        self._attribute_class = attribute_class

    @property
    def field_id(self) -> str:
        """Get the unique field identifier."""
        return self._field_id

    @property
    def attribute_class(self) -> Type["Attribute"]:
        """Get the attribute class providing normalization and validation behavior."""
        return self._attribute_class

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, AttributeField):
            return False
        return self._field_id == other._field_id

    def __hash__(self) -> int:
        return hash(self._field_id)

    def __repr__(self) -> str:
        return f"AttributeField(field_id='{self._field_id}', attribute_class={self._attribute_class.__name__})"
