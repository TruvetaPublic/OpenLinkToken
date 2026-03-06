"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import List

from opentoken.attributes.attribute_expression import AttributeExpression
from opentoken.attributes.person.birth_date_attribute import BirthDateAttribute
from opentoken.attributes.person.first_name_attribute import FirstNameAttribute
from opentoken.attributes.person.last_name_attribute import LastNameAttribute
from opentoken.attributes.person.sex_attribute import SexAttribute
from opentoken.tokens.token import Token


class T1Token(Token):
    """
    Represents the token definition for token T1.

    It is a collection of attribute expressions that are concatenated together
    to get the token signature. The token signature is as follows:
    U(last-name)|U(first-name-1)|U(gender)|birth-date
    """

    ID = "T1"

    def __init__(self):
        """Initialize the T1 token definition."""
        self._definition = [
            AttributeExpression(LastNameAttribute, "T|U"),
            AttributeExpression(FirstNameAttribute, "T|S(0,1)|U"),
            AttributeExpression(SexAttribute, "T|U"),
            AttributeExpression(BirthDateAttribute, "T|D"),
        ]

    def get_identifier(self) -> str:
        """Get the unique identifier for the token."""
        return self.ID

    def get_definition(self) -> List[AttributeExpression]:
        """Get the list of attribute expressions that define the token."""
        return self._definition
