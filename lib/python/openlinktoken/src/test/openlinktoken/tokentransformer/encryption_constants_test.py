"""
Copyright (c) Truveta. All rights reserved.
"""

from openlinktoken.tokentransformer.encryption_constants import EncryptionConstants


class TestEncryptionConstants:
    """Test cases for EncryptionConstants."""

    def test_encryption_constants_exist(self):
        """Test that all encryption constants exist."""
        assert hasattr(EncryptionConstants, "AES")
        assert hasattr(EncryptionConstants, "ENCRYPTION_ALGORITHM")
        assert hasattr(EncryptionConstants, "KEY_BYTE_LENGTH")
        assert hasattr(EncryptionConstants, "IV_SIZE")
        assert hasattr(EncryptionConstants, "TAG_LENGTH_BITS")
        assert hasattr(EncryptionConstants, "TAG_LENGTH_BYTES")

    def test_encryption_constants_values(self):
        """Test that encryption constants have correct values."""
        assert EncryptionConstants.AES == "AES"
        assert EncryptionConstants.ENCRYPTION_ALGORITHM == "AES/GCM/NoPadding"
        assert EncryptionConstants.KEY_BYTE_LENGTH == 32
        assert EncryptionConstants.IV_SIZE == 12
        assert EncryptionConstants.TAG_LENGTH_BITS == 128
        assert EncryptionConstants.TAG_LENGTH_BYTES == 16

    def test_encryption_constants_immutable(self):
        """Test that encryption constants are not None."""
        assert EncryptionConstants.AES is not None
        assert EncryptionConstants.ENCRYPTION_ALGORITHM is not None
        assert EncryptionConstants.KEY_BYTE_LENGTH is not None
        assert EncryptionConstants.IV_SIZE is not None
        assert EncryptionConstants.TAG_LENGTH_BITS is not None
        assert EncryptionConstants.TAG_LENGTH_BYTES is not None
