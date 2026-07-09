# SPDX-License-Identifier: MIT

from typing import List

from openlinktoken.attributes.attribute_expression import AttributeExpression
from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from openlinktoken.tokens.definitions.field_ids import FieldIds
from openlinktoken.tokens.token import Token


class T2Token(Token):
    """
    Represents the token definition for token T2.

    It is a collection of attribute expressions that are concatenated together
    to get the token signature. The token signature is as follows:
    U(last-name)|U(first-name)|birth-date|postal-code-3
    """

    ID = "T2"

    def __init__(self):
        """Initialize the T2 token definition."""
        self._definition = [
            AttributeExpression(LastNameAttribute, "T|U", field_id=FieldIds.LAST_NAME),
            AttributeExpression(FirstNameAttribute, "T|U", field_id=FieldIds.FIRST_NAME),
            AttributeExpression(BirthDateAttribute, "T|D", field_id=FieldIds.BIRTH_DATE),
            AttributeExpression(PostalCodeAttribute, "T|S(0,3)|U", field_id=FieldIds.POSTAL_CODE),
        ]

    def get_identifier(self) -> str:
        """Get the unique identifier for the token."""
        return self.ID

    def get_definition(self) -> List[AttributeExpression]:
        """Get the list of attribute expressions that define the token."""
        return self._definition
