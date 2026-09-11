# SPDX-License-Identifier: MIT
"""SHA-256 token digest implementation."""

import hashlib

from openlinktoken.tokens.tokenizer.token_digest import TokenDigest


class Sha256TokenDigest(TokenDigest):
    """Calculate a SHA-256 token digest."""

    def digest(self, value: bytes) -> bytes:
        """Return the SHA-256 digest of the supplied bytes."""
        return hashlib.sha256(value).digest()
