"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import Dict, List, Set

from opentoken.attributes.attribute_expression import AttributeExpression
from opentoken.tokens.base_token_definition import BaseTokenDefinition


class TokenDefinition(BaseTokenDefinition):
    """
    Encapsulates the token definitions.

    The tokens are generated using some token generation rules. This class
    encapsulates the definition of those rules. Together, they are commonly
    referred to as token definitions or rule definitions.

    Each token/rule definition is a collection of AttributeExpression that are
    concatenated together to get the token signature.
    """

    def __init__(self):
        """
        Initializes the token definitions.
        Loads all token definitions using TokenRegistry.
        """
        from opentoken.tokens.token_registry import TokenRegistry

        self.definitions: Dict[str, List[AttributeExpression]] = TokenRegistry.load_all_tokens()

    def get_version(self) -> str:
        """
        Get the version of the token definition.
        """
        return "2.0"

    def get_token_identifiers(self) -> Set[str]:
        """
        Get all token identifiers.
        """
        return set(self.definitions.keys())

    def get_token_definition(self, token_id: str) -> List[AttributeExpression]:
        """
        Get the token definition for a given token identifier.
        """
        return self.definitions.get(token_id)
