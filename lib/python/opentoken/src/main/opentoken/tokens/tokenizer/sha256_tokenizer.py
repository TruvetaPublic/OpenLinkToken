"""
Copyright (c) Truveta. All rights reserved.
"""

import hashlib
from typing import List
from opentoken.tokens.token import Token
from opentoken.tokens.tokenizer.tokenizer import Tokenizer
from opentoken.tokentransformer.token_transformer import TokenTransformer


class SHA256Tokenizer(Tokenizer):
    """
    Generates token using SHA256 digest.

    The token is generated using SHA256 digest and is hex encoded.
    If token transformations are specified, the token is then transformed
    by those transformers.
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
        Generate the token for the given token signature.

        Token = Hex(Sha256(token-signature))

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

        # Convert string to bytes using UTF-8 encoding
        value_bytes = value.encode('utf-8')

        # Create SHA-256 hash
        digest = hashlib.sha256()
        digest.update(value_bytes)
        hash_bytes = digest.digest()

        # Convert to hex string
        transformed_token = hash_bytes.hex()

        # Apply transformers
        for token_transformer in self.token_transformer_list:
            transformed_token = token_transformer.transform(transformed_token)
        
        return transformed_token
