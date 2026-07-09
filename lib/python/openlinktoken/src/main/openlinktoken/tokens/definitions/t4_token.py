# SPDX-License-Identifier: MIT

from typing import List

from openlinktoken.attributes.attribute_expression import AttributeExpression
from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
from openlinktoken.attributes.person.sex_attribute import SexAttribute
from openlinktoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
from openlinktoken.tokens.definitions.field_ids import FieldIds
from openlinktoken.tokens.token import Token


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
            AttributeExpression(SocialSecurityNumberAttribute, "T|M(\\d+)", field_id=FieldIds.SOCIAL_SECURITY_NUMBER),
            AttributeExpression(SexAttribute, "T|U", field_id=FieldIds.SEX),
            AttributeExpression(BirthDateAttribute, "T|D", field_id=FieldIds.BIRTH_DATE),
        ]

    def get_identifier(self) -> str:
        """Get the unique identifier for the token."""
        return self.ID

    def get_definition(self) -> List[AttributeExpression]:
        """Get the list of attribute expressions that define the token."""
        return self._definition
