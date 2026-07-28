"""Optional ML1 token definition."""

from typing import List

from openlinktoken.attributes.attribute_expression import AttributeExpression
from openlinktoken.tokens.token import Token


class ML1Token(Token):
    """Represents optional ML1 token definition."""

    TOKEN_ID = "ML1"

    def __init__(self):
        """Initialize an ML1 definition with no attribute expressions."""
        self._definition: List[AttributeExpression] = []

    def get_identifier(self) -> str:
        """Return the stable registry identifier for this token definition."""
        return self.TOKEN_ID

    def get_definition(self) -> List[AttributeExpression]:
        """Return the attribute expressions that make up the ML1 definition."""
        return self._definition
