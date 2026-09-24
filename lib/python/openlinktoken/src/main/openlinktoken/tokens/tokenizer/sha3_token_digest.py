# SPDX-License-Identifier: MIT
"""SHA3-256 token digest implementation."""

import hashlib

from openlinktoken.tokens.tokenizer.token_digest import TokenDigest


class Sha3TokenDigest(TokenDigest):
    """Calculate SHA3-256 digests for token-signature bytes.

    Args:
        None.

    Returns:
        A ``Sha3TokenDigest`` instance.
    """

    def digest(self, value: bytes) -> bytes:
        """Return the SHA3-256 digest of supplied bytes.

        Args:
            value: Token-signature bytes to digest.

        Returns:
            The 32-byte SHA3-256 digest.
        """
        return hashlib.sha3_256(value).digest()
