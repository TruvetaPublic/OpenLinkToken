"""
Copyright (c) Truveta. All rights reserved.
"""


class EncryptionConstants:
    """Shared constants for AES-256 GCM encryption and decryption."""

    # AES algorithm name
    AES = "AES"

    # AES-256 GCM encryption algorithm specification
    ENCRYPTION_ALGORITHM = "AES/GCM/NoPadding"

    # AES-256 key length in bytes
    KEY_BYTE_LENGTH = 32

    # GCM initialization vector size in bytes
    IV_SIZE = 12

    # GCM authentication tag length in bits
    TAG_LENGTH_BITS = 128

    # GCM authentication tag length in bytes (128 bits = 16 bytes)
    TAG_LENGTH_BYTES = 16
