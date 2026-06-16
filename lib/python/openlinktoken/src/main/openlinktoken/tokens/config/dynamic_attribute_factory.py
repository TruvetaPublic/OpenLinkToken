# SPDX-License-Identifier: MIT

from typing import Dict, Set, Type

from openlinktoken.attributes.attribute import Attribute
from openlinktoken.attributes.attribute_loader import AttributeLoader
from openlinktoken.tokens.config.tokenization_config import AttributeMappingEntry, TokenizationConfig


class DynamicAttributeFactory:
    """Creates and caches unique attribute subclasses for each logical field in the config."""

    def __init__(self, config: TokenizationConfig):
        self._field_id_to_class: Dict[str, Type[Attribute]] = {}
        self._csv_column_to_class: Dict[str, Type[Attribute]] = {}

        type_name_to_base_class = self._build_type_name_index()
        self._create_dynamic_classes(config.attributes, type_name_to_base_class)

    def get_class_for_field(self, field_id: str) -> Type[Attribute]:
        return self._field_id_to_class[field_id]

    def get_class_for_csv_column(self, csv_column: str) -> Type[Attribute]:
        return self._csv_column_to_class[csv_column]

    def get_all_classes(self) -> Set[Type[Attribute]]:
        return set(self._field_id_to_class.values())

    def _create_dynamic_classes(
        self,
        attributes: Dict[str, AttributeMappingEntry],
        type_name_to_base_class: Dict[str, Type[Attribute]],
    ) -> None:
        for csv_column, entry in attributes.items():
            base_class = type_name_to_base_class.get(entry.type)
            if base_class is None:
                raise ValueError(
                    f"Unknown attribute type '{entry.type}' for field '{entry.field}'. "
                    f"Recognized types are: {sorted(type_name_to_base_class.keys())}."
                )

            dynamic_class = type(f"{entry.field}Attribute", (base_class,), {})
            self._field_id_to_class[entry.field] = dynamic_class
            self._csv_column_to_class[csv_column] = dynamic_class

    @staticmethod
    def _build_type_name_index() -> Dict[str, Type[Attribute]]:
        index: Dict[str, Type[Attribute]] = {}
        for attribute in AttributeLoader.load():
            attribute_class = type(attribute)
            index[attribute.get_name()] = attribute_class
            for alias in attribute.get_aliases():
                index[alias] = attribute_class
        return index
