# SPDX-License-Identifier: MIT

from typing import List

from openlinktoken.attributes.attribute_expression import AttributeExpression
from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.sex_attribute import SexAttribute
from openlinktoken.tokens.token import Token


class T3Token(Token):
    """
    Represents the token definition for token T3.

    It is a collection of attribute expressions that are concatenated together
    to get the token signature. The token signature is as follows:
    U(last-name)|U(first-name)|U(gender)|birth-date
    """

    ID = "T3"

    def __init__(self):
        """Initialize the T3 token definition."""
        self._definition = [
            AttributeExpression(LastNameAttribute, "T|U"),
            AttributeExpression(FirstNameAttribute, "T|U"),
            AttributeExpression(SexAttribute, "T|U"),
            AttributeExpression(BirthDateAttribute, "T|D"),
        ]

    def get_identifier(self) -> str:
        """Get the unique identifier for the token."""
        return self.ID

    def get_definition(self) -> List[AttributeExpression]:
        """Get the list of attribute expressions that define the token."""
        return self._definition
