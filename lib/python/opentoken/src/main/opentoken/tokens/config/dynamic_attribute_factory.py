"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import Dict, Set, Type

from opentoken.attributes.attribute import Attribute
from opentoken.attributes.attribute_loader import AttributeLoader
from opentoken.tokens.config.tokenization_config import AttributeMappingEntry, TokenizationConfig


class DynamicAttributeFactory:
    """Creates and caches unique attribute subclasses for each logical field in the config.

    The core token generation pipeline uses Type[Attribute] as a dictionary key when
    passing data between the CSV reader and the token generator. This means two config
    fields that share the same base attribute type (e.g., patient zip and hospital zip,
    both using PostalCodeAttribute) would collide on the same key.

    This factory solves that by creating a unique Python subclass per logical field
    using type(), so each field has its own identity while inheriting all validation and
    normalization from the declared base attribute type.
    """

    def __init__(self, config: TokenizationConfig):
        """Initialize the factory and create dynamic subclasses for all configured fields.

        Args:
            config: The parsed tokenization configuration.
        """
        self._field_id_to_class: Dict[str, Type[Attribute]] = {}
        self._csv_column_to_class: Dict[str, Type[Attribute]] = {}

        type_name_to_base_class = self._build_type_name_index()
        self._create_dynamic_classes(config.attributes, type_name_to_base_class)

    def get_class_for_field(self, field_id: str) -> Type[Attribute]:
        """Get the dynamic attribute class for a logical field identifier.

        Args:
            field_id: The logical field identifier (the 'field' value from the config).

        Returns:
            The unique dynamic attribute class for this field.

        Raises:
            KeyError: If the field_id is not registered.
        """
        return self._field_id_to_class[field_id]

    def get_class_for_csv_column(self, csv_column: str) -> Type[Attribute]:
        """Get the dynamic attribute class for a CSV column name.

        Args:
            csv_column: The CSV column name (the key in the config 'attributes' section).

        Returns:
            The unique dynamic attribute class for this CSV column.

        Raises:
            KeyError: If the csv_column is not registered.
        """
        return self._csv_column_to_class[csv_column]

    def get_all_classes(self) -> Set[Type[Attribute]]:
        """Get all dynamically created attribute classes.

        Returns:
            The set of all dynamic attribute classes registered in this factory.
        """
        return set(self._field_id_to_class.values())

    def _create_dynamic_classes(
        self,
        attributes: Dict[str, AttributeMappingEntry],
        type_name_to_base_class: Dict[str, Type[Attribute]],
    ) -> None:
        """Create and register a unique dynamic subclass for each attribute mapping entry.

        Args:
            attributes: The attribute mapping entries from the config.
            type_name_to_base_class: Index of type name → base attribute class.

        Raises:
            ValueError: If a declared attribute type is not recognized.
        """
        for csv_column, entry in attributes.items():
            base_class = type_name_to_base_class.get(entry.type)
            if base_class is None:
                raise ValueError(
                    f"Unknown attribute type '{entry.type}' for field '{entry.field}'. "
                    f"Recognized types are: {sorted(type_name_to_base_class.keys())}."
                )

            # Create a unique subclass so this field has its own Type[Attribute] identity
            dynamic_class = type(f"{entry.field}Attribute", (base_class,), {})

            self._field_id_to_class[entry.field] = dynamic_class
            self._csv_column_to_class[csv_column] = dynamic_class

    @staticmethod
    def _build_type_name_index() -> Dict[str, Type[Attribute]]:
        """Build a lookup from attribute name/alias strings to their attribute classes.

        Returns:
            A dict mapping each name and alias string to the corresponding attribute class.
        """
        index: Dict[str, Type[Attribute]] = {}
        for attribute in AttributeLoader.load():
            attribute_class = type(attribute)
            index[attribute.get_name()] = attribute_class
            for alias in attribute.get_aliases():
                index[alias] = attribute_class
        return index
