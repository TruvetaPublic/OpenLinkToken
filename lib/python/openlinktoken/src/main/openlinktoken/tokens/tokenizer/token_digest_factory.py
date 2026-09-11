# SPDX-License-Identifier: MIT

from openlinktoken.crypto_suite import CryptoSuite
from openlinktoken.tokens.tokenizer.sha3_token_digest import Sha3TokenDigest
from openlinktoken.tokens.tokenizer.sha256_token_digest import Sha256TokenDigest
from openlinktoken.tokens.tokenizer.shake256_token_digest import Shake256TokenDigest
from openlinktoken.tokens.tokenizer.token_digest import TokenDigest


class TokenDigestFactory:
    """Create token digest implementations from validated suite metadata."""

    _IMPLEMENTATIONS = {
        "SHA-256": Sha256TokenDigest,
        "SHA3-256": Sha3TokenDigest,
        "SHAKE256-256": Shake256TokenDigest,
    }

    @classmethod
    def for_suite(cls, crypto_suite: CryptoSuite) -> TokenDigest:
        """Create the digest implementation declared by a crypto suite."""
        if not isinstance(crypto_suite, CryptoSuite):
            raise ValueError("A valid CryptoSuite is required to select a token digest.")
        return cls.for_algorithm(crypto_suite.token_digest_algorithm)

    @classmethod
    def for_algorithm(cls, algorithm: str) -> TokenDigest:
        """Create a digest implementation from its registered algorithm name."""
        try:
            return cls._IMPLEMENTATIONS[algorithm]()
        except KeyError as error:
            raise ValueError(f"Unsupported token digest algorithm '{algorithm}'.") from error
