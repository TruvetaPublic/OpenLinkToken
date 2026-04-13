# SPDX-License-Identifier: MIT

import hashlib
from unittest.mock import Mock

import pytest

from openlinktoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from openlinktoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer


class TestSHA256Tokenizer:
    """Test cases for SHA256Tokenizer."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mocking TokenTransformer implementations (Hash and Encrypt)
        self.hash_transformer_mock = Mock(spec=HashTokenTransformer)
        self.encrypt_transformer_mock = Mock(spec=EncryptTokenTransformer)

        # List of transformers to pass to SHA256Tokenizer
        transformers = [self.hash_transformer_mock, self.encrypt_transformer_mock]

        # Instantiate the tokenizer with mocked transformers
        self.tokenizer = SHA256Tokenizer(transformers)

    def test_tokenize_null_or_empty_input_returns_empty_string(self):
        """Test that null or empty input returns the empty token."""
        result_none = self.tokenizer.tokenize(None)  # Test for None input
        assert result_none == SHA256Tokenizer.EMPTY

        result_empty = self.tokenizer.tokenize("")  # Test for empty string input
        assert result_empty == SHA256Tokenizer.EMPTY

        result_blank = self.tokenizer.tokenize("   ")  # Test for input with only whitespace
        assert result_blank == SHA256Tokenizer.EMPTY

    def test_tokenize_valid_input_returns_hashed_token(self):
        """Test that valid input returns a hashed token after transformations."""
        input_value = "test-input"
        expected_hash = self._calculate_sha256(input_value)  # Expected SHA-256 hash (in hex format) for "test-input"

        # Mock the transformations to simulate behavior of TokenTransformers
        self.hash_transformer_mock.transform.return_value = expected_hash
        self.encrypt_transformer_mock.transform.return_value = "encrypted-token"

        result = self.tokenizer.tokenize(input_value)  # Call the tokenize method

        # Verify the transformers were called
        self.hash_transformer_mock.transform.assert_called_once()
        self.encrypt_transformer_mock.transform.assert_called_once_with(expected_hash)

        assert result == "encrypted-token"  # Check the final result after applying the transformers

    def test_tokenize_valid_input_no_transformers_returns_raw_hash(self):
        """Test that valid input with no transformers returns raw hash."""
        input_value = "test-input"

        tokenizer = SHA256Tokenizer([])  # Recreate tokenizer with no transformers
        expected_hash = self._calculate_sha256(input_value)  # Expected SHA-256 hash (in hex format) for "test-input"

        result = tokenizer.tokenize(input_value)  # Call the tokenize method

        assert (
            result == expected_hash
        )  # Verify that the result is just the raw SHA-256 hash (no transformations applied)

    def test_tokenize_valid_input_transformer_throws_exception(self):
        """Test that transformer exceptions are propagated."""
        input_value = "test-input"

        # Mock the first transformer to throw an exception
        self.hash_transformer_mock.transform.side_effect = RuntimeError("Transform error")

        # Call the tokenize method and assert it propagates the exception
        with pytest.raises(RuntimeError) as exc_info:
            self.tokenizer.tokenize(input_value)

        assert str(exc_info.value) == "Transform error"

    def test_tokenize_consistent_hashing(self):
        """Test that the same input always produces the same hash."""
        input_value = "consistent-test"

        # Tokenizer with no transformers for raw hash comparison
        tokenizer = SHA256Tokenizer([])

        result1 = tokenizer.tokenize(input_value)
        result2 = tokenizer.tokenize(input_value)

        assert result1 == result2
        assert len(result1) == 64  # SHA-256 produces 64 char hex string

    def test_tokenize_different_inputs_produce_different_hashes(self):
        """Test that different inputs produce different hashes."""
        tokenizer = SHA256Tokenizer([])

        result1 = tokenizer.tokenize("input1")
        result2 = tokenizer.tokenize("input2")

        assert result1 != result2

    def test_tokenize_unicode_input(self):
        """Test tokenization with Unicode input."""
        input_value = "こんにちは"  # Japanese "hello"
        tokenizer = SHA256Tokenizer([])

        result = tokenizer.tokenize(input_value)

        assert result is not None
        assert len(result) == 64

        # Verify consistency with Unicode
        result2 = tokenizer.tokenize(input_value)
        assert result == result2

    def _calculate_sha256(self, input_str: str) -> str:
        """Utility method to calculate SHA-256 hash for a given input string."""
        hash_object = hashlib.sha256(input_str.encode("utf-8"))
        return hash_object.hexdigest()
