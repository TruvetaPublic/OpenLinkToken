# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod


class TokenDigest(ABC):
    """Interface for suite-selected token digest implementations.

    Args:
        None.

    Returns:
        An instance of a concrete ``TokenDigest`` implementation; this
        abstract class cannot be instantiated directly.
    """

    @abstractmethod
    def digest(self, value: bytes) -> bytes:
        """Digest token-signature bytes.

        Args:
            value: UTF-8 token-signature bytes to digest.

        Returns:
            The digest bytes produced by the concrete implementation.

        Raises:
            NotImplementedError: If called without a concrete implementation.
        """
