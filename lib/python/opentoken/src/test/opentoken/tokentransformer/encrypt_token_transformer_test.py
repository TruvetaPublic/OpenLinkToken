"""
Copyright (c) Truveta. All rights reserved.
"""

import base64
import pickle

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from opentoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer


class TestEncryptTokenTransformer:
    """Test cases for EncryptTokenTransformer."""

    VALID_KEY = "12345678901234567890123456789012"  # 32-character key
    INVALID_KEY = "short-key"  # Invalid short key

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.transformer = EncryptTokenTransformer(self.VALID_KEY)

    def test_serializable(self):
        """Test that EncryptTokenTransformer is serializable and deserializable."""
        encrypt_token_transformer = EncryptTokenTransformer(self.VALID_KEY)
        
        # Serialize the transformer
        serialized = pickle.dumps(encrypt_token_transformer)
        
        # Deserialize the transformer
        deserialized = pickle.loads(serialized)

        token = "mySecretToken"
        encrypted_token = deserialized.transform(token)

        # Ensure the encrypted token is not null or empty
        assert encrypted_token is not None
        assert encrypted_token != ""

        # Check if the token is base64-encoded by decoding it
        decoded_bytes = base64.b64decode(encrypted_token)
        assert decoded_bytes is not None

    def test_constructor_valid_key_success(self):
        """Test that constructor with valid key succeeds."""
        valid_transformer = EncryptTokenTransformer(self.VALID_KEY)
        assert valid_transformer is not None

    def test_constructor_invalid_key_length_throws_value_error(self):
        """Test that constructor with invalid key length throws ValueError."""
        with pytest.raises(ValueError) as exc_info:
            EncryptTokenTransformer(self.INVALID_KEY)  # Key is too short
        
        assert "Key must be 32 characters long" == str(exc_info.value)

    def test_transform_valid_token_returns_encrypted_token(self):
        """Test that transforming a valid token returns an encrypted token."""
        token = "mySecretToken"
        encrypted_token = self.transformer.transform(token)

        # Ensure the encrypted token is not null or empty
        assert encrypted_token is not None
        assert encrypted_token != ""

        # Check if the token is base64-encoded by decoding it
        decoded_bytes = base64.b64decode(encrypted_token)
        assert decoded_bytes is not None

    def test_transform_reversible_encryption(self):
        """Test that encryption followed by decryption returns the original token."""
        token = "mySecretToken"

        # Encrypt the token
        encrypted_token = self.transformer.transform(token)

        # Decrypt the token using the same settings
        message_bytes = base64.b64decode(encrypted_token)
        
        # Extract IV, ciphertext, and tag
        iv = message_bytes[:12]  # First 12 bytes are IV
        ciphertext_and_tag = message_bytes[12:]  # Rest is ciphertext + tag
        ciphertext = ciphertext_and_tag[:-16]  # All but last 16 bytes
        tag = ciphertext_and_tag[-16:]  # Last 16 bytes are the tag

        # Create cipher for decryption
        cipher = Cipher(
            algorithms.AES(self.VALID_KEY.encode('utf-8')),
            modes.GCM(iv, tag),
            backend=default_backend()
        )

        # Decrypt
        decryptor = cipher.decryptor()
        decrypted_bytes = decryptor.update(ciphertext) + decryptor.finalize()
        decrypted_token = decrypted_bytes.decode('utf-8')

        # Ensure the decrypted token matches the original token
        assert token == decrypted_token

    def test_transform_different_tokens_produce_different_results(self):
        """Test that different tokens produce different encrypted results."""
        token1 = "firstToken"
        token2 = "secondToken"

        encrypted_token1 = self.transformer.transform(token1)
        encrypted_token2 = self.transformer.transform(token2)

        # Different tokens should produce different encrypted results
        assert encrypted_token1 != encrypted_token2

    def test_transform_same_token_produces_different_results_due_to_random_iv(self):
        """Test that the same token produces different results due to random IV."""
        token = "sameToken"

        encrypted_token1 = self.transformer.transform(token)
        encrypted_token2 = self.transformer.transform(token)

        # Same token should produce different encrypted results due to random IV
        assert encrypted_token1 != encrypted_token2

        # But both should decrypt to the same original token
        decrypted1 = self._decrypt_token(encrypted_token1)
        decrypted2 = self._decrypt_token(encrypted_token2)
        
        assert decrypted1 == token
        assert decrypted2 == token

    def _decrypt_token(self, encrypted_token: str) -> str:
        """
        Helper method to decrypt an encrypted token.
        
        Args:
            encrypted_token: The base64-encoded encrypted token.
            
        Returns:
            The decrypted token.
        """
        message_bytes = base64.b64decode(encrypted_token)
        
        # Extract IV, ciphertext, and tag
        iv = message_bytes[:12]  # First 12 bytes are IV
        ciphertext_and_tag = message_bytes[12:]  # Rest is ciphertext + tag
        ciphertext = ciphertext_and_tag[:-16]  # All but last 16 bytes
        tag = ciphertext_and_tag[-16:]  # Last 16 bytes are the tag

        # Create cipher for decryption
        cipher = Cipher(
            algorithms.AES(self.VALID_KEY.encode('utf-8')),
            modes.GCM(iv, tag),
            backend=default_backend()
        )

        # Decrypt
        decryptor = cipher.decryptor()
        decrypted_bytes = decryptor.update(ciphertext) + decryptor.finalize()
        return decrypted_bytes.decode('utf-8')