# SPDX-License-Identifier: MIT

import hashlib
from typing import List

from openlinktoken.crypto_suite import CryptoSuite
from openlinktoken.tokens.token import Token
from openlinktoken.tokens.tokenizer.tokenizer import Tokenizer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer


class SHA256Tokenizer(Tokenizer):
    """
    Generates tokens using the digest selected by a crypto suite.

    The token is generated using a suite-selected digest and is hex encoded.
    If token transformations are specified, the token is then transformed
    by those transformers.
    """

    EMPTY = Token.BLANK
    """
    The empty token value.

    This is the value returned when the token signature is None or blank.
    """

    def __init__(
        self,
        token_transformer_list: List[TokenTransformer],
        crypto_suite: CryptoSuite | None = None,
    ):
        """
        Initialize the tokenizer.

        Args:
            token_transformer_list: A list of token transformers.
            crypto_suite: The suite selecting the token digest. Defaults to SHA-256.
        """
        self.token_transformer_list = token_transformer_list
        self.crypto_suite = crypto_suite or CryptoSuite.default()

    def get_token_transformer_list(self) -> List[TokenTransformer]:
        """Return transformers configured after digest tokenization."""
        return self.token_transformer_list

    def tokenize(self, value: str) -> str:
        """
        Generate the token for the given token signature.

        Token = Hex(digest(token-signature))

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
        value_bytes = value.encode("utf-8")

        if self.crypto_suite.token_digest_algorithm == "SHA-256":
            hash_bytes = hashlib.sha256(value_bytes).digest()
        elif self.crypto_suite.token_digest_algorithm == "SHA3-256":
            hash_bytes = hashlib.sha3_256(value_bytes).digest()
        elif self.crypto_suite.token_digest_algorithm == "SHAKE256-256":
            hash_bytes = hashlib.shake_256(value_bytes).digest(32)
        else:
            raise ValueError(f"Unsupported token digest algorithm '{self.crypto_suite.token_digest_algorithm}'.")

        # Convert to hex string
        transformed_token = hash_bytes.hex()

        # Apply transformers
        for token_transformer in self.token_transformer_list:
            transformed_token = token_transformer.transform(transformed_token)

        return transformed_token
