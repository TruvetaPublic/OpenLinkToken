# SPDX-License-Identifier: MIT

import base64
import hashlib
import hmac
import logging
import threading
from typing import Union

from openlinktoken.crypto_suite import CryptoSuite
from openlinktoken.tokentransformer.token_transformer import TokenTransformer

logger = logging.getLogger(__name__)


class HashTokenTransformer(TokenTransformer):
    """
    Transforms the token using a cryptographic hash function with
    a secret key.

    See: https://datatracker.ietf.org/doc/html/rfc4868 (HMACSHA256)
    """

    def __init__(
        self,
        hashing_secret: Union[str, bytes, None],
        crypto_suite: CryptoSuite | None = None,
    ):
        """
        Initializes the underlying MAC with the secret key.

        Accepts a ``str`` (encoded to UTF-8), raw ``bytes``, or ``None`` / empty
        to create a no-op transformer (``transform`` will raise ``RuntimeError``).

        Args:
            hashing_secret: The cryptographic secret key.
            crypto_suite: The suite selecting the keyed MAC. Defaults to HMAC-SHA256.

        Raises:
            ValueError: If the hashing secret is None or empty.
        """
        self._lock = threading.Lock()
        self.crypto_suite = crypto_suite or CryptoSuite.default()
        if isinstance(hashing_secret, bytes):
            self.hashing_secret = hashing_secret
            self._mac_available = len(hashing_secret) > 0
        elif not hashing_secret or hashing_secret.strip() == "":
            self.hashing_secret = b""
            self._mac_available = False
        else:
            self.hashing_secret = hashing_secret.encode("utf-8")
            self._mac_available = True

    def transform(self, token: str) -> str:
        """
        Hash token transformer.

        The token is transformed using the suite-selected HMAC algorithm.

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
            if self.crypto_suite.token_mac_algorithm == "KMAC256-256":
                if len(self.hashing_secret) < 32:
                    raise ValueError("KMAC256 requires a hashing secret of at least 32 bytes.")
                from Crypto.Hash import KMAC256

                digest = KMAC256.new(key=self.hashing_secret, data=token.encode("utf-8"), mac_len=32).digest()
                return base64.b64encode(digest).decode("utf-8")

            digest_name = {
                "HS256": hashlib.sha256,
                "HS3-256": hashlib.sha3_256,
            }.get(self.crypto_suite.token_mac_algorithm)
            if digest_name is None:
                raise ValueError(f"Unsupported token MAC algorithm '{self.crypto_suite.token_mac_algorithm}'.")
            mac = hmac.new(self.hashing_secret, token.encode("utf-8"), digest_name)

            # Get the digest and encode to base64
            digest = mac.digest()
            return base64.b64encode(digest).decode("utf-8")

    def __getstate__(self):
        """Custom serialization support."""
        state = self.__dict__.copy()
        # Remove the lock as it can't be pickled
        del state["_lock"]
        return state

    def __setstate__(self, state):
        """Custom deserialization support."""
        self.__dict__.update(state)
        # Recreate the lock
        self._lock = threading.Lock()
