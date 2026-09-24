# SPDX-License-Identifier: MIT

from openlinktoken.crypto.crypto_suite import CryptoSuite
from openlinktoken.tokens.tokenizer.crypto_suite_tokenizer import CryptoSuiteTokenizer


class TestCryptoSuiteTokenizer:
    """Verify tokenization with suite-selected digest implementations.

    Args:
        None.

    Returns:
        A ``TestCryptoSuiteTokenizer`` instance for pytest to collect.
    """

    def test_tokenize_uses_suite_digest_and_hex_encoding(self):
        """The tokenizer applies its selected digest before transformations.

        Args:
            None.

        Returns:
            None.
        """
        tokenizer = CryptoSuiteTokenizer([], CryptoSuite.from_id("suite-sha3-v1"))

        assert tokenizer.tokenize("test-input") == "ab96273f069fc38264bf16cc2287218779c5eed6c0fee89490b990ffc35a2af5"
