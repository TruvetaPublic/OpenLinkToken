"""
Copyright (c) Truveta. All rights reserved.
"""

from unittest.mock import Mock

import pytest

from openlinktoken.tokens.tokenizer.passthrough_tokenizer import PassthroughTokenizer


class TestPassthroughTokenizer:
    """Test cases for PassthroughTokenizer."""

    @pytest.fixture
    def setup(self):
        """Set up test fixtures."""
        # Mocking TokenTransformer implementations
        self.hash_transformer_mock = Mock()
        self.encrypt_transformer_mock = Mock()

        # List of transformers to pass to PassthroughTokenizer
        transformers = [
            self.hash_transformer_mock,
            self.encrypt_transformer_mock,
        ]

        # Instantiate the tokenizer with mocked transformers
        self.tokenizer = PassthroughTokenizer(transformers)

    def test_tokenize_null_or_empty_input_returns_empty_string(self, setup):
        """Test that None or empty input returns EMPTY constant."""
        result_none = self.tokenizer.tokenize(None)  # Test for None input
        assert result_none == PassthroughTokenizer.EMPTY

        result_empty = self.tokenizer.tokenize("")  # Test for empty string input
        assert result_empty == PassthroughTokenizer.EMPTY

        result_blank = self.tokenizer.tokenize("   ")  # Test for input with only whitespace
        assert result_blank == PassthroughTokenizer.EMPTY

    def test_tokenize_valid_input_returns_unchanged_value(self, setup):
        """Test that valid input is passed through with transformers applied."""
        input_value = "test-input"

        # Mock the transformations to simulate behavior of TokenTransformers
        self.hash_transformer_mock.transform.return_value = input_value
        self.encrypt_transformer_mock.transform.return_value = "encrypted-token"

        result = self.tokenizer.tokenize(input_value)  # Call the tokenize method

        # Verify the transformers were called with the original input value
        self.hash_transformer_mock.transform.assert_called_once_with(input_value)
        self.encrypt_transformer_mock.transform.assert_called_once_with(input_value)

        assert result == "encrypted-token"  # Check the final result after applying transformers

    def test_tokenize_valid_input_no_transformers_returns_original_value(self):
        """Test that without transformers, the original value is returned unchanged."""
        input_value = "test-input"

        tokenizer = PassthroughTokenizer([])  # Recreate tokenizer with no transformers

        result = tokenizer.tokenize(input_value)  # Call the tokenize method

        assert result == input_value  # Verify that the result is the original value unchanged

    def test_tokenize_valid_input_transformer_throws_exception(self, setup):
        """Test that transformer exceptions are propagated."""
        input_value = "test-input"

        # Mock the first transformer to throw an exception
        self.hash_transformer_mock.transform.side_effect = RuntimeError("Transform error")

        # Call the tokenize method and assert it propagates the exception
        with pytest.raises(RuntimeError) as exc_info:
            self.tokenizer.tokenize(input_value)

        assert str(exc_info.value) == "Transform error"

    def test_tokenize_multiple_transformers_applies_in_order(self, setup):
        """Test that multiple transformers are applied in sequence."""
        input_value = "original-value"
        after_first_transform = "after-first"
        after_second_transform = "after-second"

        # Mock the transformers to apply sequential transformations
        self.hash_transformer_mock.transform.return_value = after_first_transform
        self.encrypt_transformer_mock.transform.return_value = after_second_transform

        result = self.tokenizer.tokenize(input_value)

        # Verify transformers were called in order
        self.hash_transformer_mock.transform.assert_called_once_with(input_value)
        self.encrypt_transformer_mock.transform.assert_called_once_with(after_first_transform)

        assert result == after_second_transform

    def test_tokenize_special_characters_returns_unchanged(self):
        """Test that special characters pass through unchanged."""
        input_value = "special!@#$%^&*()_+-=[]{}|;':\",./<>?"

        tokenizer = PassthroughTokenizer([])  # No transformers

        result = tokenizer.tokenize(input_value)

        assert result == input_value  # Special characters should pass through unchanged

    def test_tokenize_unicode_characters_returns_unchanged(self):
        """Test that Unicode characters pass through unchanged."""
        input_value = "Hello 世界 🌍"

        tokenizer = PassthroughTokenizer([])  # No transformers

        result = tokenizer.tokenize(input_value)

        assert result == input_value  # Unicode characters should pass through unchanged
