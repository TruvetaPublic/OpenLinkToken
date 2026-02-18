"""
Copyright (c) Truveta. All rights reserved.
"""

from unittest.mock import Mock, patch

import pytest

from opentoken.attributes.attribute_expression import AttributeExpression
from opentoken.attributes.person.first_name_attribute import FirstNameAttribute
from opentoken.attributes.person.last_name_attribute import LastNameAttribute
from opentoken.tokens.base_token_definition import BaseTokenDefinition
from opentoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from opentoken.tokens.token_generation_exception import TokenGenerationException
from opentoken.tokens.token_generator import TokenGenerator
from opentoken.tokens.token_generator_result import TokenGeneratorResult
from opentoken.tokentransformer.token_transformer import TokenTransformer


class TestTokenGenerator:
    """Test cases for TokenGenerator."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.tokenizer = Mock(spec=SHA256Tokenizer)
        self.token_transformer_list = []
        self.token_definition = Mock(spec=BaseTokenDefinition)

        # Mock the AttributeLoader to avoid dependencies
        with patch('opentoken.tokens.token_generator.AttributeLoader') as mock_loader:
            mock_loader.load.return_value = {
                FirstNameAttribute(), 
                LastNameAttribute()
            }
            self.token_generator = TokenGenerator.from_transformers(self.token_definition, self.token_transformer_list)
        
        # Inject mock tokenizer
        self.token_generator.tokenizer = self.tokenizer

    def test_get_all_tokens_valid_tokens_with_expressions(self):
        """Test generating all tokens with valid tokens and expressions."""
        self.token_definition.get_token_identifiers.return_value = {"token1", "token2"}

        attr_expr1 = AttributeExpression(FirstNameAttribute, "U")
        attr_expr2 = AttributeExpression(LastNameAttribute, "R('MacDonald','Donald')")

        attribute_expressions1 = [attr_expr1]
        attribute_expressions2 = [attr_expr2]

        self.token_definition.get_token_definition.side_effect = lambda token_id: {
            "token1": attribute_expressions1,
            "token2": attribute_expressions2
        }[token_id]

        person_attributes = {
            FirstNameAttribute: "John",
            LastNameAttribute: "Old MacDonald"
        }

        self.tokenizer.tokenize.return_value = "hashedToken"

        tokens = self.token_generator.get_all_tokens(person_attributes).tokens

        assert tokens is not None
        assert len(tokens) == 2
        assert tokens.get("token1") == "hashedToken"
        assert tokens.get("token2") == "hashedToken"

    def test_get_all_tokens_invalid_attribute_skips_token_generation(self):
        """Test that invalid attributes skip token generation."""
        self.token_definition.get_token_identifiers.return_value = {"token1"}
        self.tokenizer.tokenize.return_value = None

        attr_expr = AttributeExpression(FirstNameAttribute, "U")
        attribute_expressions = [attr_expr]
        self.token_definition.get_token_definition.return_value = attribute_expressions

        # Person attributes (invalid case with missing name)
        person_attributes = {
            LastNameAttribute: "MacDonald"
        }

        tokens = self.token_generator.get_all_tokens(person_attributes).tokens

        # Validate that no tokens are generated
        assert len(tokens) == 0, "Expected no tokens to be generated due to validation failure"

    def test_get_all_tokens_error_in_token_generation_logs_error(self):
        """Test that errors in token generation are logged and handled gracefully."""
        self.token_definition.get_token_identifiers.return_value = {"token1"}

        attr_expr = AttributeExpression(FirstNameAttribute, "U")
        attribute_expressions = [attr_expr]
        self.token_definition.get_token_definition.return_value = attribute_expressions

        person_attributes = {
            FirstNameAttribute: "John"
        }

        # Simulate error during tokenization
        self.tokenizer.tokenize.side_effect = RuntimeError("Tokenization error")

        tokens = self.token_generator.get_all_tokens(person_attributes).tokens

        # Validate that no tokens are generated due to tokenization error
        assert len(tokens) == 0, "Expected no tokens to be generated due to tokenization error"

    def test_get_token_signature_valid_signature(self):
        """Test getting a valid token signature."""
        attr_expr1 = AttributeExpression(FirstNameAttribute, "U")
        attr_expr2 = AttributeExpression(LastNameAttribute, "U")

        attribute_expressions = [attr_expr1, attr_expr2]
        self.token_definition.get_token_definition.return_value = attribute_expressions

        person_attributes = {
            FirstNameAttribute: "John",
            LastNameAttribute: "Smith"
        }

        signature = self.token_generator._get_token_signature("token1", person_attributes, TokenGeneratorResult())

        assert signature is not None
        assert signature == "JOHN|SMITH"

    def test_get_token_signature_null_person_attributes(self):
        """Test that null person attributes raise an exception."""
        with pytest.raises(ValueError):
            self.token_generator._get_token_signature("token1", None, TokenGeneratorResult())

    def test_get_token_signature_missing_required_attribute(self):
        """Test that missing required attributes return None."""
        attr_expr = AttributeExpression(FirstNameAttribute, "U")
        attribute_expressions = [attr_expr]
        self.token_definition.get_token_definition.return_value = attribute_expressions

        person_attributes = {
            LastNameAttribute: "Smith"
        }

        signature = self.token_generator._get_token_signature("token1", person_attributes, TokenGeneratorResult())

        assert signature is None

    def test_get_token_signature_invalid_attribute_value(self):
        """Test that invalid attribute values return None."""
        attr_expr = AttributeExpression(FirstNameAttribute, "U")
        attribute_expressions = [attr_expr]
        self.token_definition.get_token_definition.return_value = attribute_expressions

        person_attributes = {
            FirstNameAttribute: ""  # Invalid empty name
        }

        signature = self.token_generator._get_token_signature("token1", person_attributes, TokenGeneratorResult())

        assert signature is None

    def test_get_token_valid_input_returns_hashed_token(self):
        """Test that valid input returns a hashed token."""
        attr_expr = AttributeExpression(FirstNameAttribute, "U")
        attribute_expressions = [attr_expr]

        self.token_definition.get_token_definition.return_value = attribute_expressions
        self.tokenizer.tokenize.return_value = "hashedToken123"

        person_attributes = {
            FirstNameAttribute: "John"
        }

        token = self.token_generator._get_token("token1", person_attributes, TokenGeneratorResult())

        assert token is not None
        assert token == "hashedToken123"

    def test_get_token_null_signature_returns_none(self):
        """Test that null signature returns None."""
        self.tokenizer.tokenize.return_value = None
        attr_expr = AttributeExpression(FirstNameAttribute, "U")
        attribute_expressions = [attr_expr]

        self.token_definition.get_token_definition.return_value = attribute_expressions

        person_attributes = {
            # Missing required attribute leads to null signature
            LastNameAttribute: "Smith"
        }

        token = self.token_generator._get_token("token1", person_attributes, TokenGeneratorResult())

        assert token is None

    def test_get_token_tokenization_error_throws_exception(self):
        """Test that tokenization errors throw TokenGenerationException."""
        attr_expr = AttributeExpression(FirstNameAttribute, "U")
        attribute_expressions = [attr_expr]

        self.token_definition.get_token_definition.return_value = attribute_expressions
        self.tokenizer.tokenize.side_effect = RuntimeError("Tokenization failed")

        person_attributes = {
            FirstNameAttribute: "John"
        }

        with pytest.raises(TokenGenerationException):
            self.token_generator._get_token("token1", person_attributes, TokenGeneratorResult())

    def test_tokenizer_initialization_error_raises_exception(self):
        """Test that tokenizer initialization errors are raised."""
        bad_transformer = Mock(spec=TokenTransformer)
        bad_transformer.transform.side_effect = RuntimeError("Transformer error")
        
        # Creating tokenizer with bad transformer should raise
        with pytest.raises(Exception):
            with patch('opentoken.tokens.token_generator.AttributeLoader') as mock_loader:
                mock_loader.load.return_value = {FirstNameAttribute()}
                # Pass a tokenizer that will fail during initialization
                bad_tokenizer = SHA256Tokenizer([bad_transformer])
                bad_tokenizer.tokenize("test")  # Force the error

    def test_get_token_signature_attribute_expression_error(self):
        """Test that errors in attribute expression processing return None."""
        # Use a real attribute expression with an invalid expression pattern
        # that will cause get_effective_value to throw ValueError
        attr_expr = AttributeExpression(FirstNameAttribute, "S(invalid)")
        
        attribute_expressions = [attr_expr]
        self.token_definition.get_token_definition.return_value = attribute_expressions
        
        person_attributes = {
            FirstNameAttribute: "John"
        }
        
        result = TokenGeneratorResult()
        signature = self.token_generator._get_token_signature("token1", person_attributes, result)
        
        # Should return None when expression processing fails
        assert signature is None

    def test_get_all_token_signatures(self):
        """Test getting all token signatures for valid inputs."""
        self.token_definition.get_token_identifiers.return_value = {"token1", "token2"}
        
        attr_expr = AttributeExpression(FirstNameAttribute, "U")
        attribute_expressions = [attr_expr]
        self.token_definition.get_token_definition.return_value = attribute_expressions
        
        person_attributes = {
            FirstNameAttribute: "John"
        }
        
        signatures = self.token_generator.get_all_token_signatures(person_attributes)
        
        assert len(signatures) == 2
        assert "token1" in signatures
        assert "token2" in signatures
        assert signatures["token1"] == "JOHN"
        assert signatures["token2"] == "JOHN"

    def test_get_all_token_signatures_with_error(self):
        """Test that errors during signature generation are handled gracefully."""
        self.token_definition.get_token_identifiers.return_value = {"token1", "token2"}
        
        # First token succeeds, second throws error
        def mock_get_definition(token_id):
            if token_id == "token1":
                return [AttributeExpression(FirstNameAttribute, "U")]
            else:
                raise RuntimeError("Token definition error")
        
        self.token_definition.get_token_definition.side_effect = mock_get_definition
        
        person_attributes = {
            FirstNameAttribute: "John"
        }
        
        signatures = self.token_generator.get_all_token_signatures(person_attributes)
        
        # Should only have token1, token2 failed
        assert len(signatures) == 1
        assert "token1" in signatures
        assert "token2" not in signatures

    def test_get_invalid_person_attributes(self):
        """Test getting invalid person attributes from person attributes map."""
        person_attributes = {
            FirstNameAttribute: "",  # Invalid empty name
            LastNameAttribute: "Smith"  # Valid name
        }
        
        invalid_attrs = self.token_generator.get_invalid_person_attributes(person_attributes)
        
        assert len(invalid_attrs) == 1
        assert "FirstName" in invalid_attrs

    def test_get_invalid_person_attributes_all_valid(self):
        """Test that no invalid attributes are returned when all are valid."""
        person_attributes = {
            FirstNameAttribute: "John",
            LastNameAttribute: "Smith"
        }
        
        invalid_attrs = self.token_generator.get_invalid_person_attributes(person_attributes)
        
        assert len(invalid_attrs) == 0