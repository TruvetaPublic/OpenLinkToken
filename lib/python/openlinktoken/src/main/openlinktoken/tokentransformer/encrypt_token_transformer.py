"""
Copyright (c) Truveta. All rights reserved.
"""

import base64
import logging
import secrets
from typing import Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from openlinktoken.tokentransformer.encryption_constants import EncryptionConstants
from openlinktoken.tokentransformer.token_transformer import TokenTransformer

logger = logging.getLogger(__name__)


class EncryptTokenTransformer(TokenTransformer):
    """
    Transforms the token using AES-256 symmetric encryption.

    See: https://datatracker.ietf.org/doc/html/rfc3826 (AES)
    """

    def __init__(self, encryption_key: Union[str, bytes]):
        """
        Initializes the underlying cipher (AES) with the encryption secret.

        Accepts either a ``str`` (UTF-8 encoded; must encode to exactly 32 bytes) or
        raw ``bytes`` (must be exactly 32 bytes).

        Args:
            encryption_key: The encryption key. The UTF-8 encoded key material must be exactly 32 bytes long.

        Raises:
            ValueError: If the encryption key material is not exactly 32 bytes long.
        """
        if isinstance(encryption_key, bytes):
            if len(encryption_key) != EncryptionConstants.KEY_BYTE_LENGTH:
                logger.error(f"Invalid Argument. Key must be {EncryptionConstants.KEY_BYTE_LENGTH} bytes long")
                raise ValueError(f"Key must be {EncryptionConstants.KEY_BYTE_LENGTH} bytes long")
            self.encryption_key = encryption_key
        else:
            encryption_key_bytes = encryption_key.encode("utf-8")
            if len(encryption_key_bytes) != EncryptionConstants.KEY_BYTE_LENGTH:
                logger.error(f"Invalid Argument. Key must be {EncryptionConstants.KEY_BYTE_LENGTH} bytes long")
                raise ValueError(f"Key must be {EncryptionConstants.KEY_BYTE_LENGTH} bytes long")
            self.encryption_key = encryption_key_bytes

    def transform(self, token: str) -> str:
        """
        Encryption token transformer.

        Encrypts the token using AES-256 symmetric encryption algorithm.

        Args:
            token: The token to be encrypted.

        Returns:
            The encrypted token in base64 format.

        Raises:
            Exception: If encryption fails due to various cryptographic errors.
        """
        try:
            # Generate random IV (for AES GCM mode)
            iv_bytes = secrets.token_bytes(EncryptionConstants.IV_SIZE)

            # Create cipher
            cipher = Cipher(algorithms.AES(self.encryption_key), modes.GCM(iv_bytes), backend=default_backend())

            # Encrypt the token
            encryptor = cipher.encryptor()
            encrypted_bytes = encryptor.update(token.encode("utf-8")) + encryptor.finalize()

            # Get the authentication tag
            tag = encryptor.tag

            # Combine IV + encrypted data + tag
            message_bytes = iv_bytes + encrypted_bytes + tag

            return base64.b64encode(message_bytes).decode("utf-8")

        except Exception as e:
            logger.error(f"Error during token encryption: {e}")
            raise
