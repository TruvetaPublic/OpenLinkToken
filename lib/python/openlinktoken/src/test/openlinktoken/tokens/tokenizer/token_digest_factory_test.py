# SPDX-License-Identifier: MIT

import hashlib

import pytest

from openlinktoken.crypto_suite import CryptoSuite
from openlinktoken.tokens.tokenizer.sha3_token_digest import Sha3TokenDigest
from openlinktoken.tokens.tokenizer.sha256_token_digest import Sha256TokenDigest
from openlinktoken.tokens.tokenizer.shake256_token_digest import Shake256TokenDigest
from openlinktoken.tokens.tokenizer.token_digest_factory import TokenDigestFactory


class TestTokenDigestFactory:
    """Verify suite-selected token digest implementations."""

    def test_factory_selects_digest_implementation_for_each_suite(self):
        """Each registered suite selects its declared digest implementation."""
        assert isinstance(TokenDigestFactory.for_suite(CryptoSuite.from_id("suite-sha256-v1")), Sha256TokenDigest)
        assert isinstance(TokenDigestFactory.for_suite(CryptoSuite.from_id("suite-sha3-v1")), Sha3TokenDigest)
        assert isinstance(TokenDigestFactory.for_suite(CryptoSuite.from_id("suite-pq-shake-v1")), Shake256TokenDigest)

    def test_digest_implementations_match_standard_vectors(self):
        """Each implementation produces the expected digest bytes."""
        value = b"test-input"

        assert Sha256TokenDigest().digest(value) == hashlib.sha256(value).digest()
        assert Sha3TokenDigest().digest(value) == hashlib.sha3_256(value).digest()
        assert Shake256TokenDigest().digest(value) == hashlib.shake_256(value).digest(32)

    def test_factory_rejects_unsupported_digest_algorithm(self):
        """The factory rejects a suite with an unsupported digest identifier."""
        suite = CryptoSuite(
            suite_id="suite-unsupported-v1",
            token_digest_algorithm="UNKNOWN",
            token_mac_algorithm="HS256",
            token_content_encryption="A256GCM",
            exchange_key_agreement="ECDH",
            exchange_config_version=1,
        )

        with pytest.raises(ValueError, match="Unsupported token digest algorithm"):
            TokenDigestFactory.for_suite(suite)
