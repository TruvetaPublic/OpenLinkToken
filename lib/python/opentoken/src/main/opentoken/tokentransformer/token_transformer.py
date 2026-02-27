"""
Copyright (c) Truveta. All rights reserved.
"""

from abc import ABC, abstractmethod


class TokenTransformer(ABC):
    """A generic interface for the token transformer."""

    @abstractmethod
    def transform(self, token: str) -> str:
        """
        Transforms the token using a token transformation rule/strategy.

        Args:
            token: The token to be transformed.

        Returns:
            The transformed token.

        Raises:
            Exception: Error encountered while transforming the token.
        """
