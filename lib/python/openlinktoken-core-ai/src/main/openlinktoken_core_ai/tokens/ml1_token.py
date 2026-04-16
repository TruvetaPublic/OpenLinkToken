"""Optional ML1 token definition."""
from typing import List

from openlinktoken.attributes.attribute_expression import AttributeExpression
from openlinktoken.tokens.token import Token


class ML1Token(Token):
    """Represents optional ML1 token definition."""

    ID = "ML1"

    def __init__(self):
        self._definition: List[AttributeExpression] = []

    def get_identifier(self) -> str:
        return self.ID

    def get_definition(self) -> List[AttributeExpression]:
        return self._definition
