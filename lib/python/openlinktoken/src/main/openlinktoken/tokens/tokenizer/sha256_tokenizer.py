# SPDX-License-Identifier: MIT

from typing import List

from openlinktoken.crypto_suite import CryptoSuite
from openlinktoken.tokens.tokenizer.crypto_suite_tokenizer import CryptoSuiteTokenizer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer


class SHA256Tokenizer(CryptoSuiteTokenizer):
    """Backward-compatible name for the suite-aware tokenizer."""

    def __init__(
        self,
        token_transformer_list: List[TokenTransformer],
        crypto_suite: CryptoSuite | None = None,
    ):
        """Initialize the compatibility wrapper with the selected suite."""
        super().__init__(token_transformer_list, crypto_suite)
