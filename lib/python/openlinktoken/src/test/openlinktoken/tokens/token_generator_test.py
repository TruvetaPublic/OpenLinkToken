# SPDX-License-Identifier: MIT

import logging
from unittest.mock import Mock, patch

import pytest

import openlinktoken.tokens.token_generator as token_generator_module
from openlinktoken.attributes.attribute_expression import AttributeExpression
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.tokens.base_token_definition import BaseTokenDefinition
from openlinktoken.tokens.token import Token
from openlinktoken.tokens.token_generation_exception import TokenGenerationException
from openlinktoken.tokens.token_generator import TokenGenerator
from openlinktoken.tokens.token_generator_result import TokenGeneratorResult
from openlinktoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer


@pytest.fixture(autouse=True)
def reset_inference_provider_cache():
    """Isolate lazy provider discovery between tests."""
    token_generator_module._inference_provider = None
    token_generator_module._provider_discovered = False
    yield
    token_generator_module._inference_provider = None
    token_generator_module._provider_discovered = False


class TestTokenGenerator:
    """Test cases for TokenGenerator."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.tokenizer = Mock(spec=SHA256Tokenizer)
        self.token_transformer_list = []
        self.token_definition = Mock(spec=BaseTokenDefinition)

        # Mock the AttributeLoader to avoid dependencies
        with patch("openlinktoken.tokens.token_generator.AttributeLoader") as mock_loader:
            mock_loader.load.return_value = {FirstNameAttribute(), LastNameAttribute()}
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
            "token2": attribute_expressions2,
        }[token_id]

        person_attributes = {FirstNameAttribute: "John", LastNameAttribute: "Old MacDonald"}

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
        person_attributes = {LastNameAttribute: "MacDonald"}

        tokens = self.token_generator.get_all_tokens(person_attributes).tokens

        # Validate that no tokens are generated
        assert len(tokens) == 0, "Expected no tokens to be generated due to validation failure"

    def test_get_all_tokens_error_in_token_generation_logs_error(self):
        """Test that errors in token generation are logged and handled gracefully."""
        self.token_definition.get_token_identifiers.return_value = {"token1"}

        attr_expr = AttributeExpression(FirstNameAttribute, "U")
        attribute_expressions = [attr_expr]
        self.token_definition.get_token_definition.return_value = attribute_expressions

        person_attributes = {FirstNameAttribute: "John"}

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

        person_attributes = {FirstNameAttribute: "John", LastNameAttribute: "Smith"}

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

        person_attributes = {LastNameAttribute: "Smith"}

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

        person_attributes = {FirstNameAttribute: "John"}

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

        person_attributes = {FirstNameAttribute: "John"}

        with pytest.raises(TokenGenerationException):
            self.token_generator._get_token("token1", person_attributes, TokenGeneratorResult())

    def test_tokenizer_initialization_error_raises_exception(self):
        """Test that tokenizer initialization errors are raised."""
        bad_transformer = Mock(spec=TokenTransformer)
        bad_transformer.transform.side_effect = RuntimeError("Transformer error")

        # Creating tokenizer with bad transformer should raise
        with pytest.raises(Exception):
            with patch("openlinktoken.tokens.token_generator.AttributeLoader") as mock_loader:
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

        person_attributes = {FirstNameAttribute: "John"}

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

        person_attributes = {FirstNameAttribute: "John"}

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

        person_attributes = {FirstNameAttribute: "John"}

        signatures = self.token_generator.get_all_token_signatures(person_attributes)

        # Should only have token1, token2 failed
        assert len(signatures) == 1
        assert "token1" in signatures
        assert "token2" not in signatures

    def test_get_invalid_person_attributes(self):
        """Test getting invalid person attributes from person attributes map."""
        person_attributes = {
            FirstNameAttribute: "",  # Invalid empty name
            LastNameAttribute: "Smith",  # Valid name
        }

        invalid_attrs = self.token_generator.get_invalid_person_attributes(person_attributes)

        assert len(invalid_attrs) == 1
        assert "FirstName" in invalid_attrs

    def test_get_invalid_person_attributes_all_valid(self):
        """Test that no invalid attributes are returned when all are valid."""
        person_attributes = {FirstNameAttribute: "John", LastNameAttribute: "Smith"}

        invalid_attrs = self.token_generator.get_invalid_person_attributes(person_attributes)

        assert len(invalid_attrs) == 0

    def test_inference_provider_is_discovered_and_cached(self):
        """A registered inference provider is loaded once and then cached."""

        class Provider:
            def get_token_id(self):
                return "ML1"

            def is_enabled(self):
                return True

            def generate_signature(self, person_attributes):
                return "provider-signature"

        entry_point = Mock()
        entry_point.load.return_value = Provider
        with patch.object(token_generator_module, "entry_points", return_value=[entry_point]):
            first = TokenGenerator.get_inference_provider()
            second = TokenGenerator.get_inference_provider()

        assert first is second
        entry_point.load.assert_called_once()

    def test_inference_provider_discovery_returns_none_without_entry_points(self):
        """Provider discovery is optional when no provider package is installed."""
        with patch.object(token_generator_module, "entry_points", return_value=[]):
            provider = TokenGenerator.get_inference_provider()

        assert provider is None

    def test_inference_provider_discovery_ignores_load_errors(self):
        """A broken provider package does not prevent standard token generation."""
        entry_point = Mock()
        entry_point.load.side_effect = RuntimeError("provider load failed")

        with patch.object(token_generator_module, "entry_points", return_value=[entry_point]):
            provider = TokenGenerator.get_inference_provider()

        assert provider is None
        entry_point.load.assert_called_once()

    def test_disabled_inference_provider_uses_token_definition(self):
        """Disabled inference providers fall back to standard definitions."""

        class Provider:
            def get_token_id(self):
                return "ML1"

            def is_enabled(self):
                return False

            def generate_signature(self, person_attributes):
                return "unused"

        token_generator_module._inference_provider = Provider()
        token_generator_module._provider_discovered = True
        self.token_definition.get_token_definition.return_value = [AttributeExpression(FirstNameAttribute, "U")]

        signature = self.token_generator._get_token_signature(
            "ML1",
            {FirstNameAttribute: "John"},
            TokenGeneratorResult(),
        )

        assert signature == "JOHN"

    def test_enabled_inference_provider_generates_signature(self):
        """An enabled provider handles its matching token identifier."""

        class Provider:
            def get_token_id(self):
                return "ML1"

            def is_enabled(self):
                return True

            def generate_signature(self, person_attributes):
                return "provider-signature"

        token_generator_module._inference_provider = Provider()
        token_generator_module._provider_discovered = True

        signature = self.token_generator._get_token_signature(
            "ML1",
            {FirstNameAttribute: "John"},
            TokenGeneratorResult(),
        )

        assert signature == "provider-signature"
        self.token_definition.get_token_definition.assert_not_called()

    def test_field_id_inference_provider_handles_empty_definition(self):
        """Field-ID APIs invoke enabled providers even without an attribute definition."""

        class Provider:
            def get_token_id(self):
                return "ML1"

            def is_enabled(self):
                return True

            def generate_signature(self, person_attributes):
                return f"{person_attributes['LastName']}-provider"

        token_generator_module._inference_provider = Provider()
        token_generator_module._provider_discovered = True
        self.token_definition.get_token_identifiers.return_value = {"ML1"}
        self.token_definition.get_token_definition.return_value = []
        self.tokenizer.get_token_transformer_list.return_value = []

        signatures = self.token_generator.get_all_token_signatures_via_field_id({"LastName": "Smith"})
        result = self.token_generator.get_all_tokens_via_field_id({"LastName": "Smith"})

        assert signatures == {"ML1": "Smith-provider"}
        assert result.tokens == {"ML1": "Smith-provider"}
        assert result.blank_tokens_by_rule == set()

    def test_inference_provider_skips_hashing_and_tracks_blank(self):
        """Provider signatures bypass hashing while missing values become tracked blanks."""

        class Provider:
            def get_token_id(self):
                return "ML1"

            def is_enabled(self):
                return True

            def generate_signature(self, person_attributes):
                return person_attributes.get("LastName")

        token_generator_module._inference_provider = Provider()
        token_generator_module._provider_discovered = True
        self.token_definition.get_token_identifiers.return_value = {"ML1"}
        self.token_definition.get_token_definition.return_value = []
        self.token_generator.tokenizer = SHA256Tokenizer([HashTokenTransformer(b"secret")])

        result = self.token_generator.get_all_tokens_via_field_id({"LastName": "Smith"})
        blank_result = self.token_generator.get_all_tokens_via_field_id({})

        assert result.tokens == {"ML1": "Smith"}
        assert result.blank_tokens_by_rule == set()
        assert blank_result.tokens == {"ML1": Token.BLANK}
        assert blank_result.blank_tokens_by_rule == {"ML1"}

    def test_deprecated_class_keyed_inference_api_adapts_to_field_ids(self):
        """Deprecated class-keyed APIs adapt canonical attribute names for providers."""

        class Provider:
            def get_token_id(self):
                return "ML1"

            def is_enabled(self):
                return True

            def generate_signature(self, person_attributes):
                return f"{person_attributes['LastName']}-provider"

        token_generator_module._inference_provider = Provider()
        token_generator_module._provider_discovered = True
        self.token_definition.get_token_identifiers.return_value = {"ML1"}
        self.token_definition.get_token_definition.return_value = []

        signatures = self.token_generator.get_all_token_signatures({LastNameAttribute: "Smith"})

        assert signatures == {"ML1": "Smith-provider"}

    def test_inference_provider_error_returns_none(self, caplog):
        """Provider errors are logged and converted to a missing signature."""

        class Provider:
            def get_token_id(self):
                return "ML1"

            def is_enabled(self):
                return True

            def generate_signature(self, person_attributes):
                raise RuntimeError("provider failed")

        token_generator_module._inference_provider = Provider()
        token_generator_module._provider_discovered = True

        with caplog.at_level(logging.ERROR):
            signature = self.token_generator._get_token_signature(
                "ML1",
                {FirstNameAttribute: "John"},
                TokenGeneratorResult(),
            )

        assert signature is None
        assert "provider failed" in caplog.text

    def test_empty_definition_skips_tokenization_without_provider(self):
        """Inference-only token definitions produce no blank token without a provider."""
        self.token_definition.get_token_definition.return_value = []

        with patch.object(token_generator_module, "entry_points", return_value=[]):
            token = self.token_generator._get_token("ML1", {}, TokenGeneratorResult())

        assert token is None
        self.tokenizer.tokenize.assert_not_called()

    def test_field_id_tokens_skip_empty_definition_without_provider(self):
        """Field-ID token generation skips inference-only definitions when disabled."""
        self.token_definition.get_token_identifiers.return_value = {"ML1"}
        self.token_definition.get_token_definition.return_value = []

        with patch.object(token_generator_module, "entry_points", return_value=[]):
            result = self.token_generator.get_all_tokens_via_field_id({})

        assert result.tokens == {}
        self.tokenizer.tokenize.assert_not_called()

    def test_generate_tokens_excluding_skips_requested_identifiers(self):
        """Excluded identifiers are omitted while other tokens are generated."""
        self.token_definition.get_token_identifiers.return_value = {"include", "exclude"}
        self.token_definition.get_token_definition.side_effect = {
            "include": [AttributeExpression(FirstNameAttribute, "U")],
            "exclude": [AttributeExpression(LastNameAttribute, "U")],
        }.get
        self.tokenizer.tokenize.return_value = "token"

        result = self.token_generator.generate_tokens_excluding(
            {FirstNameAttribute: "John", LastNameAttribute: "Smith"},
            {"exclude"},
        )

        assert result.tokens == {"include": "token"}
        assert self.token_definition.get_token_definition.call_count == 2
        assert all(call.args == ("include",) for call in self.token_definition.get_token_definition.call_args_list)

    def test_apply_precomputed_signature_records_blank_token(self):
        """Precomputed blank signatures are stored and tracked by token id."""
        result = TokenGeneratorResult()
        self.tokenizer.tokenize.return_value = Token.BLANK

        self.token_generator.apply_precomputed_signature(result, "ML1", "signature")

        assert result.tokens["ML1"] == Token.BLANK
        assert "ML1" in result.blank_tokens_by_rule

    def test_apply_precomputed_signature_records_blank_on_tokenizer_error(self):
        """Tokenizer failures produce a tracked blank token for precomputed values."""
        result = TokenGeneratorResult()
        self.tokenizer.tokenize.side_effect = RuntimeError("tokenizer failed")

        self.token_generator.apply_precomputed_signature(result, "ML1", "signature")

        assert result.tokens["ML1"] == Token.BLANK
        assert "ML1" in result.blank_tokens_by_rule

    def test_store_raw_token_skips_hash_transformer(self):
        """Raw values bypass hashing while still applying remaining transformers."""
        hash_transformer = HashTokenTransformer(b"secret")
        encrypt_transformer = Mock()
        encrypt_transformer.transform.return_value = "encrypted-token"
        self.tokenizer.get_token_transformer_list.return_value = [hash_transformer, encrypt_transformer]
        result = TokenGeneratorResult()

        self.token_generator.store_raw_token(result, "ML1", "prehashed-value")

        assert result.tokens["ML1"] == "encrypted-token"
        encrypt_transformer.transform.assert_called_once_with("prehashed-value")

    def test_store_raw_token_records_blank_on_transformer_error(self):
        """Raw-token transformer failures are converted to a tracked blank token."""
        encrypt_transformer = Mock()
        encrypt_transformer.transform.side_effect = RuntimeError("encryption failed")
        self.tokenizer.get_token_transformer_list.return_value = [encrypt_transformer]
        result = TokenGeneratorResult()

        self.token_generator.store_raw_token(result, "ML1", "prehashed-value")

        assert result.tokens["ML1"] == Token.BLANK
        assert "ML1" in result.blank_tokens_by_rule

    def test_apply_embedding_derived_tokens_uses_sequential_ids(self):
        """Embedding-derived values are stored under the requested sequential prefix."""
        result = TokenGeneratorResult()

        self.token_generator.apply_embedding_derived_tokens(
            result,
            "ML1-R",
            ["first", "second"],
        )

        assert result.tokens == {"ML1-R0": "first", "ML1-R1": "second"}
