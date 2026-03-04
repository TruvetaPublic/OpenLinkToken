"""
Copyright (c) Truveta. All rights reserved.
"""

from abc import ABC, abstractmethod
from typing import List, Set

from opentoken.attributes.attribute_expression import AttributeExpression


class BaseTokenDefinition(ABC):
    """
    A generic interface for the token definition.
    """

    @abstractmethod
    def get_version(self) -> str:
        """
        Get the version of the token definition.

        Returns:
            The token definition version.
        """
        pass

    @abstractmethod
    def get_token_identifiers(self) -> Set[str]:
        """
        Get all token identifiers. For example, a set of { T1, T2, T3, T4, T5 }.

        The token identifiers are also called rule identifiers because every token is
        generated from rule definition.

        Returns:
            A set of token identifiers.
        """
        pass

    @abstractmethod
    def get_token_definition(self, token_id: str) -> List[AttributeExpression]:
        """
        Get the token definition for a given token identifier.

        Args:
            token_id: The token/rule identifier.

        Returns:
            A list of token/rule definition.
        """
        pass
