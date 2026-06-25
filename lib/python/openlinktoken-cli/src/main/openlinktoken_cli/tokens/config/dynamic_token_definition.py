# SPDX-License-Identifier: MIT

from typing import Dict, List, Set

from openlinktoken.attributes.attribute_expression import AttributeExpression
from openlinktoken.tokens.base_token_definition import BaseTokenDefinition
from openlinktoken_cli.tokens.config.dynamic_attribute_factory import DynamicAttributeFactory
from openlinktoken_cli.tokens.config.tokenization_config import TokenizationConfig


class DynamicTokenDefinition(BaseTokenDefinition):
    """A token definition built at runtime from a custom tokenization configuration."""

    VERSION = "custom"

    def __init__(self, config: TokenizationConfig, factory: DynamicAttributeFactory):
        self._definitions: Dict[str, List[AttributeExpression]] = {}

        for token_id, rule_entries in config.token_rules.items():
            expressions = []
            for entry in rule_entries:
                attribute_class = factory.get_class_for_field(entry.field)
                attribute_expression = AttributeExpression(attribute_class, entry.expression)
                # Config-mode rules resolve row values by logical field id, not by class key.
                attribute_expression.field_id = entry.field
                expressions.append(attribute_expression)
            self._definitions[token_id] = expressions

    def get_version(self) -> str:
        return self.VERSION

    def get_token_identifiers(self) -> Set[str]:
        return set(self._definitions.keys())

    def get_token_definition(self, token_id: str) -> List[AttributeExpression]:
        return self._definitions.get(token_id)
