"""
Copyright (c) Truveta. All rights reserved.
"""

import base64
import hashlib
import hmac
import logging
import threading
from opentoken.tokentransformer.token_transformer import TokenTransformer


logger = logging.getLogger(__name__)


class HashTokenTransformer(TokenTransformer):
    """
    Transforms the token using a cryptographic hash function with
    a secret key.

    See: https://datatracker.ietf.org/doc/html/rfc4868 (HMACSHA256)
    """

    def __init__(self, hashing_secret: str):
        """
        Initializes the underlying MAC with the secret key.

        Args:
            hashing_secret: The cryptographic secret key.

        Raises:
            ValueError: If the hashing secret is None or empty.
        """
        self.hashing_secret = hashing_secret
        self._lock = threading.Lock()

        if not hashing_secret or hashing_secret.strip() == "":
            self._mac_available = False
        else:
            self._mac_available = True

    def transform(self, token: str) -> str:
        """
        Hash token transformer.

        The token is transformed using HMAC SHA256 algorithm.

        Args:
            token: The token to be transformed.

        Returns:
            Hashed token in base64 format.

        Raises:
            ValueError: If token is None or blank.
            RuntimeError: If the HMAC is not initialized properly.
        """
        if token is None or token.strip() == "":
            logger.error("Invalid Argument. Token can't be None or blank.")
            raise ValueError("Invalid Argument. Token can't be None or blank.")

        if not self._mac_available:
            raise RuntimeError("HMAC is not properly initialized due to empty hashing secret.")

        with self._lock:
            # Create HMAC with SHA256 - token is encoded to bytes using UTF-8
            mac = hmac.new(
                self.hashing_secret.encode('utf-8'),
                token.encode('utf-8'),
                hashlib.sha256
            )

            # Get the digest and encode to base64
            digest = mac.digest()
            return base64.b64encode(digest).decode('utf-8')

    def __getstate__(self):
        """Custom serialization support."""
        state = self.__dict__.copy()
        # Remove the lock as it can't be pickled
        del state['_lock']
        return state

    def __setstate__(self, state):
        """Custom deserialization support."""
        self.__dict__.update(state)
        # Recreate the lock
        self._lock = threading.Lock()
