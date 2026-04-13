# SPDX-License-Identifier: MIT

import hashlib


class RecordIdHasher:
    """Utility for hashing record IDs using SHA-256."""

    @staticmethod
    def hash(record_id: str) -> str:
        """
        Hash the given record ID using SHA-256 and return a lowercase hex string.

        Args:
            record_id: The record ID to hash.

        Returns:
            The SHA-256 hex digest of the record ID.
        """
        return hashlib.sha256(record_id.encode("utf-8")).hexdigest()
