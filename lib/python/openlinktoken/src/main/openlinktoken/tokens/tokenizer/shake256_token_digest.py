# SPDX-License-Identifier: MIT
"""SHAKE256 token digest implementation."""

import hashlib

from openlinktoken.tokens.tokenizer.token_digest import TokenDigest


class Shake256TokenDigest(TokenDigest):
    """Calculate fixed-width SHAKE256 digests for token-signature bytes.

    Args:
        None.

    Returns:
        A ``Shake256TokenDigest`` instance.
    """

    OUTPUT_LENGTH = 32

    def digest(self, value: bytes) -> bytes:
        """Return 32 bytes from the SHAKE256 extendable-output function.

        Args:
            value: Token-signature bytes to digest.

        Returns:
            The 32-byte SHAKE256 digest.
        """
        return hashlib.shake_256(value).digest(self.OUTPUT_LENGTH)
