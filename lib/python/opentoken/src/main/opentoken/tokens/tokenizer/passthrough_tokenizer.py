"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import List
from opentoken.tokens.token import Token
from opentoken.tokens.tokenizer.tokenizer import Tokenizer
from opentoken.tokentransformer.token_transformer import TokenTransformer


class PassthroughTokenizer(Tokenizer):
    """
    A tokenizer that returns the input value unchanged (passthrough).

    This tokenizer does not apply any hashing or cryptographic transformation
    to the input value. It simply returns the input as-is, optionally applying
    token transformers if provided.

    This is useful for scenarios where you want to preserve the original token
    signature without any cryptographic processing, while still allowing for
    optional transformations (e.g., encryption).
    """

    EMPTY = Token.BLANK
    """
    The empty token value.

    This is the value returned when the token signature is None or blank.
    """

    def __init__(self, token_transformer_list: List[TokenTransformer]):
        """
        Initialize the tokenizer.

        Args:
            token_transformer_list: A list of token transformers.
        """
        self.token_transformer_list = token_transformer_list

    def tokenize(self, value: str) -> str:
        """
        Return the input value unchanged (passthrough).

        Token = value

        The token is optionally transformed with one or more transformers.

        Args:
            value: The token signature value.

        Returns:
            The token. If the token signature value is None or blank,
            EMPTY is returned.

        Raises:
            Exception: If an error is thrown by the transformer.
        """
        if value is None or value.strip() == "":
            return self.EMPTY

        transformed_token = value

        # Apply transformers
        for token_transformer in self.token_transformer_list:
            transformed_token = token_transformer.transform(transformed_token)
        
        return transformed_token
