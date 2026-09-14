# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod


class TokenDigest(ABC):
    """Interface for suite-selected token digest implementations."""

    @abstractmethod
    def digest(self, value: bytes) -> bytes:
        """Digest UTF-8 token-signature bytes."""
