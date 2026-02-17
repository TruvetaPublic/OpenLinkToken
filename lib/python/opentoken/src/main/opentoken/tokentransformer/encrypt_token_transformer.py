"""
Copyright (c) Truveta. All rights reserved.
"""
import base64
import logging
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from opentoken.tokentransformer.token_transformer import TokenTransformer
from opentoken.tokentransformer.encryption_constants import EncryptionConstants


logger = logging.getLogger(__name__)


class EncryptTokenTransformer(TokenTransformer):
    """
    Transforms the token using AES-256 symmetric encryption.

    See: https://datatracker.ietf.org/doc/html/rfc3826 (AES)
    """

    def __init__(self, encryption_key: str):
        """
        Initializes the underlying cipher (AES) with the encryption secret.

        Args:
            encryption_key: The encryption key. The key must be 32 characters long.

        Raises:
            ValueError: If the encryption key is not 32 characters long.
        """
        if len(encryption_key) != EncryptionConstants.KEY_BYTE_LENGTH:
            logger.error(
                f"Invalid Argument. Key must be {EncryptionConstants.KEY_BYTE_LENGTH} characters long")
            raise ValueError(
                f"Key must be {EncryptionConstants.KEY_BYTE_LENGTH} characters long")

        self.encryption_key = encryption_key.encode('utf-8')

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
            cipher = Cipher(
                algorithms.AES(self.encryption_key),
                modes.GCM(iv_bytes),
                backend=default_backend()
            )

            # Encrypt the token
            encryptor = cipher.encryptor()
            encrypted_bytes = encryptor.update(token.encode('utf-8')) + encryptor.finalize()

            # Get the authentication tag
            tag = encryptor.tag

            # Combine IV + encrypted data + tag
            message_bytes = iv_bytes + encrypted_bytes + tag

            return base64.b64encode(message_bytes).decode('utf-8')

        except Exception as e:
            logger.error(f"Error during token encryption: {e}")
            raise
