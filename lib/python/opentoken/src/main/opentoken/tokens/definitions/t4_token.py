"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import List

from opentoken.attributes.attribute_expression import AttributeExpression
from opentoken.attributes.person.birth_date_attribute import BirthDateAttribute
from opentoken.attributes.person.sex_attribute import SexAttribute
from opentoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
from opentoken.tokens.token import Token


class T4Token(Token):
    """
    Represents the token definition for token T4.

    It is a collection of attribute expressions that are concatenated together
    to get the token signature. The token signature is as follows:
    social-security-number|U(gender)|birth-date
    """

    ID = "T4"

    def __init__(self):
        """Initialize the T4 token definition."""
        self._definition = [
            AttributeExpression(SocialSecurityNumberAttribute, "T|M(\\d+)"),
            AttributeExpression(SexAttribute, "T|U"),
            AttributeExpression(BirthDateAttribute, "T|D"),
        ]

    def get_identifier(self) -> str:
        """Get the unique identifier for the token."""
        return self.ID

    def get_definition(self) -> List[AttributeExpression]:
        """Get the list of attribute expressions that define the token."""
        return self._definition
