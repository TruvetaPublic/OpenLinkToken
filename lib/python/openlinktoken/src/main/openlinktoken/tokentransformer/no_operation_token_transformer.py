"""
Copyright (c) Truveta. All rights reserved.
"""

from openlinktoken.tokentransformer.token_transformer import TokenTransformer


class NoOperationTokenTransformer(TokenTransformer):
    """
    A No Operation token transformer. No transformation is
    applied whatsoever.
    """

    def transform(self, token: str) -> str:
        """
        No operation token transformer.

        Does not transform the token in any ways.

        Args:
            token: The token to be transformed.

        Returns:
            The unchanged token.
        """
        return token
