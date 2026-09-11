# SPDX-License-Identifier: MIT
"""SHA3-256 token digest implementation."""

import hashlib

from openlinktoken.tokens.tokenizer.token_digest import TokenDigest


class Sha3TokenDigest(TokenDigest):
    """Calculate a SHA3-256 token digest."""

    def digest(self, value: bytes) -> bytes:
        """Return the SHA3-256 digest of the supplied bytes."""
        return hashlib.sha3_256(value).digest()
