# SPDX-License-Identifier: MIT
"""SHA-256 token digest implementation."""

import hashlib

from openlinktoken.tokens.tokenizer.token_digest import TokenDigest


class Sha256TokenDigest(TokenDigest):
    """Calculate SHA-256 digests for token-signature bytes.

    Args:
        None.

    Returns:
        A ``Sha256TokenDigest`` instance.
    """

    def digest(self, value: bytes) -> bytes:
        """Return the SHA-256 digest of supplied bytes.

        Args:
            value: Token-signature bytes to digest.

        Returns:
            The 32-byte SHA-256 digest.
        """
        return hashlib.sha256(value).digest()
