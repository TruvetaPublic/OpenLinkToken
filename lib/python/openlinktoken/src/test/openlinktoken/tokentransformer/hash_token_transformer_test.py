# SPDX-License-Identifier: MIT

import base64
import hashlib
import hmac
import pickle

import pytest

from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer


class TestHashTokenTransformer:
    """Test cases for HashTokenTransformer."""

    VALID_SECRET = "sampleSecret"
    VALID_TOKEN = "sampleToken"

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.transformer = HashTokenTransformer(self.VALID_SECRET)

    def test_serializable(self):
        """Test that HashTokenTransformer is serializable and deserializable."""
        encrypt_token_transformer = HashTokenTransformer(self.VALID_SECRET)

        # Serialize the transformer
        serialized = pickle.dumps(encrypt_token_transformer)

        # Deserialize the transformer
        deserialized = pickle.loads(serialized)

        # Transform a token using the deserialized transformer
        hashed_token = deserialized.transform(self.VALID_TOKEN)

        assert hashed_token is not None

        # Manually calculate the expected hash for validation
        expected_hashed_token = self._calculate_expected_hash(self.VALID_SECRET, self.VALID_TOKEN)

        assert expected_hashed_token == hashed_token

    def test_transform_valid_token_returns_hashed_token(self):
        """Test that transforming a valid token returns the expected hashed token."""
        hashed_token = self.transformer.transform(self.VALID_TOKEN)
        assert hashed_token is not None

        # Manually calculate the expected hash for validation
        expected_hashed_token = self._calculate_expected_hash(self.VALID_SECRET, self.VALID_TOKEN)

        assert expected_hashed_token == hashed_token

    def test_transform_null_token_throws_value_error(self):
        """Test that transforming a null token throws ValueError."""
        with pytest.raises(ValueError) as exc_info:
            self.transformer.transform(None)

        assert "Invalid Argument. Token can't be None or blank." == str(exc_info.value)

    def test_transform_blank_token_throws_value_error(self):
        """Test that transforming a blank token throws ValueError."""
        with pytest.raises(ValueError) as exc_info:
            self.transformer.transform("")

        assert "Invalid Argument. Token can't be None or blank." == str(exc_info.value)

    def test_transform_whitespace_token_throws_value_error(self):
        """Test that transforming a whitespace-only token throws ValueError."""
        with pytest.raises(ValueError) as exc_info:
            self.transformer.transform("   ")

        assert "Invalid Argument. Token can't be None or blank." == str(exc_info.value)

    def test_constructor_null_secret_initializes_with_null_mac(self):
        """Test that constructor with null secret creates unusable transformer."""
        null_secret_transformer = HashTokenTransformer(None)

        with pytest.raises(RuntimeError) as exc_info:
            null_secret_transformer.transform(self.VALID_TOKEN)

        assert "HMAC is not properly initialized due to empty hashing secret." == str(exc_info.value)

    def test_constructor_blank_secret_initializes_with_null_mac(self):
        """Test that constructor with blank secret creates unusable transformer."""
        blank_secret_transformer = HashTokenTransformer("")

        with pytest.raises(RuntimeError) as exc_info:
            blank_secret_transformer.transform(self.VALID_TOKEN)

        assert "HMAC is not properly initialized due to empty hashing secret." == str(exc_info.value)

    def test_constructor_whitespace_secret_initializes_with_null_mac(self):
        """Test that constructor with whitespace-only secret creates unusable transformer."""
        whitespace_secret_transformer = HashTokenTransformer("   ")

        with pytest.raises(RuntimeError) as exc_info:
            whitespace_secret_transformer.transform(self.VALID_TOKEN)

        assert "HMAC is not properly initialized due to empty hashing secret." == str(exc_info.value)

    def test_transform_valid_token_multiple_times_returns_consistent_hash(self):
        """Test that transforming the same token multiple times returns consistent results."""
        hash1 = self.transformer.transform(self.VALID_TOKEN)
        hash2 = self.transformer.transform(self.VALID_TOKEN)

        assert hash1 == hash2  # The hashed value should be consistent

    def test_transform_supports_raw_byte_secrets(self):
        """Raw byte secrets must be hashed without UTF-8 re-encoding."""
        raw_secret = b"\xff\x00sample-secret-material"
        transformer = HashTokenTransformer(raw_secret)

        hashed_token = transformer.transform(self.VALID_TOKEN)

        expected_hashed_token = base64.b64encode(
            hmac.new(raw_secret, self.VALID_TOKEN.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")
        assert expected_hashed_token == hashed_token

    def _calculate_expected_hash(self, secret: str, token: str) -> str:
        """
        Calculate the expected HMAC-SHA256 hash for validation.

        Args:
            secret: The secret key.
            token: The token to hash.

        Returns:
            The base64-encoded HMAC-SHA256 hash.
        """
        mac = hmac.new(secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256)
        expected_hash = mac.digest()
        return base64.b64encode(expected_hash).decode("utf-8")
