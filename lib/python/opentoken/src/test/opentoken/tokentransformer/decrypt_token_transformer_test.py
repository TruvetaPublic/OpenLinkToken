"""
Copyright (c) Truveta. All rights reserved.
"""

import pickle

import pytest

from opentoken.tokentransformer.decrypt_token_transformer import DecryptTokenTransformer
from opentoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer

class TestDecryptTokenTransformer:
    """Test cases for DecryptTokenTransformer."""

    VALID_KEY = "12345678901234567890123456789012"  # 32-character key
    INVALID_KEY = "short-key"  # Invalid short key

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.decryptor = DecryptTokenTransformer(self.VALID_KEY)
        self.encryptor = EncryptTokenTransformer(self.VALID_KEY)

    def test_serializable(self):
        """Test that DecryptTokenTransformer is serializable and deserializable."""
        decrypt_token_transformer = DecryptTokenTransformer(self.VALID_KEY)
        
        # Serialize the transformer
        serialized = pickle.dumps(decrypt_token_transformer)
        
        # Deserialize the transformer
        deserialized = pickle.loads(serialized)

        # First encrypt a token
        token = "mySecretToken"
        encrypted_token = self.encryptor.transform(token)

        # Then decrypt using deserialized transformer
        decrypted_token = deserialized.transform(encrypted_token)

        assert token == decrypted_token

    def test_constructor_valid_key_success(self):
        """Test that constructor with valid key succeeds."""
        valid_transformer = DecryptTokenTransformer(self.VALID_KEY)
        assert valid_transformer is not None

    def test_constructor_invalid_key_length_throws_value_error(self):
        """Test that constructor with invalid key length throws ValueError."""
        with pytest.raises(ValueError) as exc_info:
            DecryptTokenTransformer(self.INVALID_KEY)  # Key is too short
        
        assert "Key must be 32 characters long" == str(exc_info.value)

    def test_transform_valid_encrypted_token_returns_decrypted_token(self):
        """Test that transforming a valid encrypted token returns the decrypted token."""
        original_token = "mySecretToken"

        # Encrypt the token first
        encrypted_token = self.encryptor.transform(original_token)

        # Now decrypt it
        decrypted_token = self.decryptor.transform(encrypted_token)

        assert original_token == decrypted_token

    def test_transform_multiple_tokens_decrypts_correctly(self):
        """Test that multiple tokens can be encrypted and decrypted correctly."""
        token1 = "firstToken"
        token2 = "secondToken"
        token3 = "thirdToken"

        # Encrypt all tokens
        encrypted1 = self.encryptor.transform(token1)
        encrypted2 = self.encryptor.transform(token2)
        encrypted3 = self.encryptor.transform(token3)

        # Decrypt all tokens
        decrypted1 = self.decryptor.transform(encrypted1)
        decrypted2 = self.decryptor.transform(encrypted2)
        decrypted3 = self.decryptor.transform(encrypted3)

        # Verify all decryptions
        assert token1 == decrypted1
        assert token2 == decrypted2
        assert token3 == decrypted3

    def test_transform_same_token_encrypted_twice_both_decrypt_correctly(self):
        """Test that the same token encrypted twice produces different encrypted values but both decrypt correctly."""
        original_token = "sameToken"

        # Encrypt the same token twice (should produce different encrypted values due to random IV)
        encrypted1 = self.encryptor.transform(original_token)
        encrypted2 = self.encryptor.transform(original_token)

        # Both encrypted tokens should be different
        assert encrypted1 != encrypted2

        # But both should decrypt to the same original token
        decrypted1 = self.decryptor.transform(encrypted1)
        decrypted2 = self.decryptor.transform(encrypted2)

        assert original_token == decrypted1
        assert original_token == decrypted2

    def test_transform_special_characters_decrypts_correctly(self):
        """Test that tokens with special characters decrypt correctly."""
        special_token = "token|with|pipes|and|special!@#$%^&*()_+characters"

        encrypted = self.encryptor.transform(special_token)
        decrypted = self.decryptor.transform(encrypted)

        assert special_token == decrypted

    def test_transform_unicode_characters_decrypts_correctly(self):
        """Test that tokens with unicode characters decrypt correctly."""
        unicode_token = "token-with-unicode-你好-мир-🎉"

        encrypted = self.encryptor.transform(unicode_token)
        decrypted = self.decryptor.transform(encrypted)

        assert unicode_token == decrypted

    def test_transform_wrong_key_throws_exception(self):
        """Test that decrypting with the wrong key throws an exception."""
        original_token = "mySecretToken"

        # Encrypt with one key
        encrypted_token = self.encryptor.transform(original_token)

        # Try to decrypt with a different key
        wrong_decryptor = DecryptTokenTransformer("00000000000000000000000000000000")

        # Should throw an exception
        with pytest.raises(Exception):
            wrong_decryptor.transform(encrypted_token)
