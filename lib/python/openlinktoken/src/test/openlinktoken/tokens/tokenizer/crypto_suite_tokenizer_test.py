# SPDX-License-Identifier: MIT

from openlinktoken.crypto_suite import CryptoSuite
from openlinktoken.tokens.tokenizer.crypto_suite_tokenizer import CryptoSuiteTokenizer


class TestCryptoSuiteTokenizer:
    """Verify the common tokenizer pipeline for suite-selected digests."""

    def test_tokenize_uses_suite_digest_and_hex_encoding(self):
        """The tokenizer uses the factory-selected digest before transformations."""
        tokenizer = CryptoSuiteTokenizer([], CryptoSuite.from_id("suite-sha3-v1"))

        assert tokenizer.tokenize("test-input") == "ab96273f069fc38264bf16cc2287218779c5eed6c0fee89490b990ffc35a2af5"
