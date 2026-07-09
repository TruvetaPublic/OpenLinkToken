# SPDX-License-Identifier: MIT

from typing import Dict, Type

from openlinktoken.attributes.attribute import Attribute
from openlinktoken.attributes.attribute_loader import AttributeLoader
from openlinktoken.attributes.field_registry import FieldRegistry
from openlinktoken_cli.tokens.config.tokenization_config import AttributeMappingEntry, TokenizationConfig


class ConfiguredAttributeResolver:
    """Resolves config field ids to built-in attribute classes and column mappings."""

    def __init__(self, config: TokenizationConfig):
        """Build lookup indexes from a parsed tokenization config.

        Args:
            config: Parsed tokenization config whose attribute entries drive the mappings.
        """
        self._field_id_to_class: Dict[str, Type[Attribute]] = {}
        self._field_id_to_instance: Dict[str, Attribute] = {}
        self._column_to_field_id: Dict[str, str] = {}

        type_name_to_base_class = self._build_type_name_index()
        base_class_to_instance: Dict[Type[Attribute], Attribute] = {type(attr): attr for attr in AttributeLoader.load()}
        self._register_field_mappings(config.attributes, type_name_to_base_class, base_class_to_instance)

    def get_class_for_field(self, field_id: str) -> Type[Attribute]:
        """Return the attribute class registered for a logical field id.

        Args:
            field_id: The logical field identifier defined in the tokenization config.

        Returns:
            The attribute class mapped to the given field id.

        Raises:
            KeyError: If no class is registered for the field id.
        """
        return self._field_id_to_class[field_id]

    def get_field_for_column(self, column: str) -> str:
        """Return the logical field id for an input column name.

        Args:
            column: The input column name as it appears in the data source.

        Returns:
            The logical field id mapped to the column.

        Raises:
            KeyError: If the column name has no registered mapping.
        """
        return self._column_to_field_id[column]

    def build_field_registry(self) -> FieldRegistry:
        """Build a FieldRegistry from all configured field-to-attribute mappings.

        Returns:
            A registry mapping each configured field id to its attribute instance.
        """
        builder = FieldRegistry.Builder()
        for field_id, instance in self._field_id_to_instance.items():
            builder.register(field_id, self._field_id_to_class[field_id], instance)
        return builder.build()

    def _register_field_mappings(
        self,
        attributes: Dict[str, AttributeMappingEntry],
        type_name_to_base_class: Dict[str, Type[Attribute]],
        base_class_to_instance: Dict[Type[Attribute], Attribute],
    ) -> None:
        for column, entry in attributes.items():
            base_class = type_name_to_base_class.get(entry.type)
            if base_class is None:
                raise ValueError(
                    f"Unknown attribute type '{entry.type}' for field '{entry.field}'. "
                    f"Recognized types are: {sorted(type_name_to_base_class.keys())}."
                )

            self._field_id_to_class[entry.field] = base_class
            self._field_id_to_instance[entry.field] = base_class_to_instance[base_class]
            self._column_to_field_id[column] = entry.field

    @staticmethod
    def _build_type_name_index() -> Dict[str, Type[Attribute]]:
        index: Dict[str, Type[Attribute]] = {}
        attributes = sorted(
            AttributeLoader.load(),
            key=lambda attribute: (type(attribute).__name__, attribute.get_name()),
        )
        for attribute in attributes:
            attribute_class = type(attribute)
            ConfiguredAttributeResolver._register_index_mapping(index, attribute.get_name(), attribute_class)
            for alias in attribute.get_aliases():
                ConfiguredAttributeResolver._register_index_mapping(index, alias, attribute_class)
        return index

    @staticmethod
    def _register_index_mapping(
        index: Dict[str, Type[Attribute]],
        type_name: str,
        attribute_class: Type[Attribute],
    ) -> None:
        existing = index.get(type_name)
        if existing is not None and existing is not attribute_class:
            raise ValueError(
                f"Conflicting attribute type mapping for '{type_name}': "
                f"'{existing.__name__}' and '{attribute_class.__name__}'."
            )

        index[type_name] = attribute_class
