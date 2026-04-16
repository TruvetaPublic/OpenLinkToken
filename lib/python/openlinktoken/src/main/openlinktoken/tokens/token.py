# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import List

from openlinktoken.attributes.attribute_expression import AttributeExpression


class Token(ABC):
    """
    A token is a collection of attribute expressions that are concatenated
    together to get the token signature and a unique identifier.
    """

    # Represents the value for tokens with invalid or missing data.
    # This constant is a placeholder for cases where a token is either
    # not provided or contains invalid information.
    BLANK = "0000000000000000000000000000000000000000000000000000000000000000"

    @abstractmethod
    def get_identifier(self) -> str:
        """
        Get the unique identifier for the token.

        Returns:
            The unique identifier for the token.
        """
        pass

    @abstractmethod
    def get_definition(self) -> List[AttributeExpression]:
        """
        Get the list of attribute expressions that define the token.

        Returns:
            The list of attribute expressions that define the token.
        """
        pass
