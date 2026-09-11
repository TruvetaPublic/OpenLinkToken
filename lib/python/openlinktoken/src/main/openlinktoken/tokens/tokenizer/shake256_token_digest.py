# SPDX-License-Identifier: MIT
"""SHAKE256 token digest implementation."""

import hashlib

from openlinktoken.tokens.tokenizer.token_digest import TokenDigest


class Shake256TokenDigest(TokenDigest):
    """Calculate a fixed-width SHAKE256 token digest."""

    OUTPUT_LENGTH = 32

    def digest(self, value: bytes) -> bytes:
        """Return 32 bytes from the SHAKE256 extendable-output function."""
        return hashlib.shake_256(value).digest(self.OUTPUT_LENGTH)
