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
        """Build token definitions from config entries resolved by the attribute factory.

        Args:
            config: Parsed tokenization configuration containing token rule entries.
            factory: Dynamic attribute factory used to resolve each rule field id
                to its generated attribute class.

        Returns:
            None. Populates ``self._definitions`` for runtime token generation.
        """
        self._definitions: Dict[str, List[AttributeExpression]] = {}

        for token_id, rule_entries in config.token_rules.items():
            expressions = []
            for entry in rule_entries:
                attribute_class = factory.get_class_for_field(entry.field)
                expressions.append(AttributeExpression(attribute_class, entry.expression))
            self._definitions[token_id] = expressions

    def get_version(self) -> str:
        """Return the runtime token-definition version identifier.

        Returns:
            The string ``"custom"`` indicating config-driven token definitions.
        """
        return self.VERSION

    def get_token_identifiers(self) -> Set[str]:
        """Return all configured token/rule ids.

        Returns:
            A set of token ids defined in the input configuration.
        """
        return set(self._definitions.keys())

    def get_token_definition(self, token_id: str) -> List[AttributeExpression]:
        """Return the ordered attribute-expression definition for a token id.

        Args:
            token_id: Token/rule identifier to retrieve.

        Returns:
            The list of ``AttributeExpression`` entries for the token id, or an
            empty list when the token id is not present.
        """
        return self._definitions.get(token_id, [])
