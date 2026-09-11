# SPDX-License-Identifier: MIT

from typing import List

from openlinktoken.crypto_suite import CryptoSuite
from openlinktoken.tokens.token import Token
from openlinktoken.tokens.tokenizer.token_digest import TokenDigest
from openlinktoken.tokens.tokenizer.token_digest_factory import TokenDigestFactory
from openlinktoken.tokens.tokenizer.tokenizer import Tokenizer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer


class CryptoSuiteTokenizer(Tokenizer):
    """Generate tokens with a digest selected by a crypto suite."""

    EMPTY = Token.BLANK

    def __init__(
        self,
        token_transformer_list: List[TokenTransformer],
        crypto_suite: CryptoSuite | None = None,
    ):
        """Initialize the common suite-aware tokenization pipeline."""
        self.token_transformer_list = token_transformer_list
        self.crypto_suite = crypto_suite or CryptoSuite.default()
        self.token_digest: TokenDigest = TokenDigestFactory.for_suite(self.crypto_suite)

    def get_token_transformer_list(self) -> List[TokenTransformer]:
        """Return transformers configured after tokenization."""
        return self.token_transformer_list

    def tokenize(self, value: str) -> str:
        """Generate a hexadecimal digest token and apply its transformers."""
        if value is None or value.strip() == "":
            return self.EMPTY

        transformed_token = self.token_digest.digest(value.encode("utf-8")).hex()
        for token_transformer in self.token_transformer_list:
            transformed_token = token_transformer.transform(transformed_token)
        return transformed_token
