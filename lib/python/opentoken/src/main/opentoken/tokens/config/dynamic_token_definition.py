"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import Dict, List, Set

from opentoken.attributes.attribute_expression import AttributeExpression
from opentoken.tokens.base_token_definition import BaseTokenDefinition
from opentoken.tokens.config.dynamic_attribute_factory import DynamicAttributeFactory
from opentoken.tokens.config.tokenization_config import TokenizationConfig


class DynamicTokenDefinition(BaseTokenDefinition):
    """A token definition built at runtime from a custom tokenization configuration.

    This implements the same BaseTokenDefinition interface as the standard TokenDefinition,
    so it can be passed directly to TokenGenerator without any engine changes.

    Each token rule is constructed by pairing the dynamic attribute class (resolved via
    DynamicAttributeFactory) with the expression string from the config.
    """

    VERSION = "custom"

    def __init__(self, config: TokenizationConfig, factory: DynamicAttributeFactory):
        """Build the token definitions from the config and dynamic attribute factory.

        Args:
            config: The parsed tokenization configuration.
            factory: The factory that holds the dynamic attribute classes keyed by field id.
        """
        self._definitions: Dict[str, List[AttributeExpression]] = {}

        for token_id, rule_entries in config.token_rules.items():
            expressions = []
            for entry in rule_entries:
                attribute_class = factory.get_class_for_field(entry.field)
                expressions.append(AttributeExpression(attribute_class, entry.expression))
            self._definitions[token_id] = expressions

    def get_version(self) -> str:
        """Get the version identifier for this token definition.

        Returns:
            The string "custom" to indicate this is a config-driven definition.
        """
        return self.VERSION

    def get_token_identifiers(self) -> Set[str]:
        """Get all token identifiers defined in this configuration.

        Returns:
            A set of token identifiers (e.g., {"T1", "T2", "T3"}).
        """
        return set(self._definitions.keys())

    def get_token_definition(self, token_id: str) -> List[AttributeExpression]:
        """Get the token definition for a given token identifier.

        Args:
            token_id: The token identifier (e.g., "T1").

        Returns:
            The list of AttributeExpressions for the given token, or None if not found.
        """
        return self._definitions.get(token_id)
