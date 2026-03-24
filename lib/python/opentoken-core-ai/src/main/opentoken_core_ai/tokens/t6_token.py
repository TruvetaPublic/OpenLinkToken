"""Optional T6 token definition."""
from typing import List

from opentoken.attributes.attribute_expression import AttributeExpression
from opentoken.tokens.token import Token


class T6Token(Token):
    """Represents optional T6 token definition."""

    ID = "T6"

    def __init__(self):
        self._definition: List[AttributeExpression] = []

    def get_identifier(self) -> str:
        return self.ID

    def get_definition(self) -> List[AttributeExpression]:
        return self._definition
