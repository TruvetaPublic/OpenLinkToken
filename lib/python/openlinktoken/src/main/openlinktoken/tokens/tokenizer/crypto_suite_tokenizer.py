# SPDX-License-Identifier: MIT

from typing import List

from openlinktoken.crypto.crypto_suite import CryptoSuite
from openlinktoken.tokens.token import Token
from openlinktoken.tokens.tokenizer.token_digest import TokenDigest
from openlinktoken.tokens.tokenizer.token_digest_factory import TokenDigestFactory
from openlinktoken.tokens.tokenizer.tokenizer import Tokenizer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer


class CryptoSuiteTokenizer(Tokenizer):
    """Generate tokens with a digest selected by a crypto suite.

    Args:
        token_transformer_list: Transformers applied after digesting a signature.
        crypto_suite: Optional suite selecting the digest; defaults to the
            backward-compatible SHA-256 suite.

    Returns:
        A ``CryptoSuiteTokenizer`` configured with the selected digest and
        transformers.
    """

    EMPTY = Token.BLANK

    def __init__(
        self,
        token_transformer_list: List[TokenTransformer],
        crypto_suite: CryptoSuite | None = None,
    ):
        """Initialize the common suite-aware tokenization pipeline.

        Args:
            token_transformer_list: Transformers to apply after digesting.
            crypto_suite: Optional suite selecting the digest implementation.

        Returns:
            None.
        """
        self.token_transformer_list = token_transformer_list
        self.crypto_suite = crypto_suite or CryptoSuite.default()
        self.token_digest: TokenDigest = TokenDigestFactory.for_suite(self.crypto_suite)

    def get_token_transformer_list(self) -> List[TokenTransformer]:
        """Return transformers configured after tokenization.

        Args:
            None.

        Returns:
            The configured list of token transformers.
        """
        return self.token_transformer_list

    def tokenize(self, value: str) -> str:
        """Generate a hexadecimal digest token and apply its transformers.

        Args:
            value: Token signature text to digest; blank or ``None`` values
                produce the blank-token marker.

        Returns:
            The transformed hexadecimal digest, or the blank-token marker.
        """
        if value is None or value.strip() == "":
            return self.EMPTY

        transformed_token = self.token_digest.digest(value.encode("utf-8")).hex()
        for token_transformer in self.token_transformer_list:
            transformed_token = token_transformer.transform(transformed_token)
        return transformed_token
