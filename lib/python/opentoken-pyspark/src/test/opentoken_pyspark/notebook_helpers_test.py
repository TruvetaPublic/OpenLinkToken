"""
Copyright (c) Truveta. All rights reserved.

Tests for notebook helper utilities.
"""

import json
from pathlib import Path

import pytest

import opentoken_pyspark.notebook_helpers as notebook_helpers
from opentoken.attributes.person.birth_date_attribute import BirthDateAttribute
from opentoken.attributes.person.first_name_attribute import FirstNameAttribute
from opentoken.attributes.person.last_name_attribute import LastNameAttribute
from opentoken.attributes.person.sex_attribute import SexAttribute
from opentoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
from opentoken.ec_key_utils import generate_key_pair
from opentoken.exchange_config import derive_transport_encryption_key, resolve_exchange_config_inputs
from opentoken.exchange_jwe import build_exchange_envelope
from opentoken_pyspark.notebook_helpers import (
    CustomTokenDefinition,
    TokenBuilder,
    create_token_generator,
    expression_help,
    list_attributes,
    quick_token,
)
from opentoken_pyspark.overlap_analyzer import OpenTokenOverlapAnalyzer


class TestTokenBuilder:
    """Tests for TokenBuilder."""

    def test_build_simple_token(self):
        """Test building a simple custom token."""
        token = TokenBuilder("T6").add("last_name", "T|U").add("first_name", "T|U").build()

        assert token.get_identifier() == "T6"
        assert len(token.get_definition()) == 2

    def test_add_attribute_by_string(self):
        """Test adding attributes using string names."""
        builder = TokenBuilder("T7")
        builder.add("birth_date", "T|D")
        token = builder.build()

        assert token.get_identifier() == "T7"
        assert len(token.get_definition()) == 1

    def test_add_invalid_attribute_name(self):
        """Test that adding an invalid attribute name raises ValueError."""
        builder = TokenBuilder("T8")
        with pytest.raises(ValueError, match="Unknown attribute"):
            builder.add("invalid_attribute", "T")

    def test_method_chaining(self):
        """Test that add() supports method chaining."""
        token = (
            TokenBuilder("T9").add("last_name", "T|U").add("first_name", "T|S(0,3)|U").add("birth_date", "T|D").build()
        )

        assert len(token.get_definition()) == 3


class TestCustomTokenDefinition:
    """Tests for CustomTokenDefinition."""

    def test_add_single_token(self):
        """Test adding a single token to definition."""
        token = TokenBuilder("T6").add("last_name", "T|U").build()
        definition = CustomTokenDefinition().add_token(token)

        assert "T6" in definition.get_token_identifiers()
        assert definition.get_token_definition("T6") is not None

    def test_add_multiple_tokens(self):
        """Test adding multiple tokens to definition."""
        t6 = TokenBuilder("T6").add("last_name", "T|U").build()
        t7 = TokenBuilder("T7").add("first_name", "T|U").build()

        definition = CustomTokenDefinition().add_token(t6).add_token(t7)

        assert "T6" in definition.get_token_identifiers()
        assert "T7" in definition.get_token_identifiers()
        assert len(definition.get_token_identifiers()) == 2

    def test_get_version(self):
        """Test that get_version returns custom version string."""
        definition = CustomTokenDefinition()
        assert definition.get_version() == "2.0-custom"

    def test_get_nonexistent_token(self):
        """Test getting a token definition that doesn't exist."""
        definition = CustomTokenDefinition()
        result = definition.get_token_definition("NonExistent")
        assert result is None


class TestCreateTokenGenerator:
    """Tests for create_token_generator helper."""

    def test_create_with_default_definition(self):
        """Test creating a generator with default token definition."""
        generator = create_token_generator("test-hash-secret", "12345678901234567890123456789012")
        assert generator is not None

    def test_create_with_custom_definition(self):
        """Test creating a generator with custom token definition."""
        token = TokenBuilder("T6").add("last_name", "T|U").build()
        definition = CustomTokenDefinition().add_token(token)

        generator = create_token_generator("test-hash-secret", "12345678901234567890123456789012", definition)
        assert generator is not None

    def test_create_from_exchange_config_matches_direct_secrets(self, tmp_path):
        """Exchange-config generator helper should match direct-secret output."""
        exchange_config_path, private_key_path, _ = _write_exchange_config(tmp_path)
        resolved_exchange = resolve_exchange_config_inputs(exchange_config_path, private_key_path=private_key_path)

        generator = notebook_helpers.create_token_generator_from_exchange_config(
            exchange_config_path=exchange_config_path,
            private_key_path=private_key_path,
        )
        expected_generator = create_token_generator(
            resolved_exchange.hashing_secret,
            derive_transport_encryption_key(resolved_exchange),
        )
        analyzer = OpenTokenOverlapAnalyzer(derive_transport_encryption_key(resolved_exchange))
        generated_tokens = generator.get_all_tokens(_sample_person_attributes()).tokens
        expected_tokens = expected_generator.get_all_tokens(_sample_person_attributes()).tokens

        assert generated_tokens.keys() == expected_tokens.keys()
        for token_id, generated_token in generated_tokens.items():
            assert analyzer._decrypt_token(generated_token) == analyzer._decrypt_token(expected_tokens[token_id])

    def test_create_from_exchange_config_accepts_direct_exchange_config_and_private_key_values(self, tmp_path):
        """Direct exchange-config JSON and private-key PEM values should configure the helper."""
        exchange_config_path, private_key_path, _ = _write_exchange_config(tmp_path)
        resolved_exchange = resolve_exchange_config_inputs(exchange_config_path, private_key_path=private_key_path)

        generator = notebook_helpers.create_token_generator_from_exchange_config(
            exchange_config_value=exchange_config_path.read_text(encoding="utf-8"),
            private_key_value=private_key_path.read_text(encoding="utf-8"),
        )
        expected_generator = create_token_generator(
            resolved_exchange.hashing_secret,
            derive_transport_encryption_key(resolved_exchange),
        )
        analyzer = OpenTokenOverlapAnalyzer(derive_transport_encryption_key(resolved_exchange))
        generated_tokens = generator.get_all_tokens(_sample_person_attributes()).tokens
        expected_tokens = expected_generator.get_all_tokens(_sample_person_attributes()).tokens

        assert generated_tokens.keys() == expected_tokens.keys()
        for token_id, generated_token in generated_tokens.items():
            assert analyzer._decrypt_token(generated_token) == analyzer._decrypt_token(expected_tokens[token_id])


class TestQuickToken:
    """Tests for quick_token convenience function."""

    def test_quick_token_creation(self):
        """Test creating a quick token with attribute list."""
        generator = quick_token(
            "T10",
            [("last_name", "T|U"), ("first_name", "T|S(0,3)|U"), ("birth_date", "T|D")],
            "test-hash-secret",
            "12345678901234567890123456789012",
        )
        assert generator is not None

    def test_quick_token_with_postal_code(self):
        """Test quick token with postal code attribute."""
        generator = quick_token(
            "T11", [("postal_code", "T|S(0,3)"), ("sex", "T|U")], "test-hash-secret", "12345678901234567890123456789012"
        )
        assert generator is not None

    def test_quick_token_from_exchange_config_matches_direct_secrets(self, tmp_path, monkeypatch):
        """Exchange-config quick-token helper should match direct-secret output."""
        exchange_config_path, _, sender_private_pem = _write_exchange_config(tmp_path)
        monkeypatch.setenv("OPENTOKEN_TEST_PRIVATE_KEY", sender_private_pem.decode("utf-8"))
        resolved_exchange = resolve_exchange_config_inputs(
            exchange_config_path,
            private_key_env="OPENTOKEN_TEST_PRIVATE_KEY",
        )

        generator = notebook_helpers.quick_token_from_exchange_config(
            token_id="T10",
            attributes=[("last_name", "T|U"), ("first_name", "T|U"), ("birth_date", "T|D")],
            exchange_config_path=exchange_config_path,
            private_key_env="OPENTOKEN_TEST_PRIVATE_KEY",
        )
        expected_generator = quick_token(
            "T10",
            [("last_name", "T|U"), ("first_name", "T|U"), ("birth_date", "T|D")],
            resolved_exchange.hashing_secret,
            derive_transport_encryption_key(resolved_exchange),
        )
        analyzer = OpenTokenOverlapAnalyzer(derive_transport_encryption_key(resolved_exchange))
        generated_tokens = generator.get_all_tokens(_sample_person_attributes()).tokens
        expected_tokens = expected_generator.get_all_tokens(_sample_person_attributes()).tokens

        assert generated_tokens.keys() == expected_tokens.keys()
        for token_id, generated_token in generated_tokens.items():
            assert analyzer._decrypt_token(generated_token) == analyzer._decrypt_token(expected_tokens[token_id])

    def test_quick_token_from_exchange_config_accepts_direct_exchange_config_and_private_key_values(self, tmp_path):
        """Direct exchange-config JSON and private-key PEM values should work in quick-token helpers."""
        exchange_config_path, private_key_path, _ = _write_exchange_config(tmp_path)
        resolved_exchange = resolve_exchange_config_inputs(exchange_config_path, private_key_path=private_key_path)

        generator = notebook_helpers.quick_token_from_exchange_config(
            token_id="T10",
            attributes=[("last_name", "T|U"), ("first_name", "T|U"), ("birth_date", "T|D")],
            exchange_config_value=exchange_config_path.read_text(encoding="utf-8"),
            private_key_value=private_key_path.read_text(encoding="utf-8"),
        )
        expected_generator = quick_token(
            "T10",
            [("last_name", "T|U"), ("first_name", "T|U"), ("birth_date", "T|D")],
            resolved_exchange.hashing_secret,
            derive_transport_encryption_key(resolved_exchange),
        )
        analyzer = OpenTokenOverlapAnalyzer(derive_transport_encryption_key(resolved_exchange))
        generated_tokens = generator.get_all_tokens(_sample_person_attributes()).tokens
        expected_tokens = expected_generator.get_all_tokens(_sample_person_attributes()).tokens

        assert generated_tokens.keys() == expected_tokens.keys()
        for token_id, generated_token in generated_tokens.items():
            assert analyzer._decrypt_token(generated_token) == analyzer._decrypt_token(expected_tokens[token_id])


class TestListAttributes:
    """Tests for list_attributes helper."""

    def test_list_attributes_returns_dict(self):
        """Test that list_attributes returns a dictionary."""
        attrs = list_attributes()
        assert isinstance(attrs, dict)
        assert len(attrs) > 0

    def test_list_attributes_contains_expected_keys(self):
        """Test that list_attributes includes common attribute names."""
        attrs = list_attributes()
        expected_keys = ["first_name", "last_name", "birth_date", "sex"]
        for key in expected_keys:
            assert key in attrs


class TestExpressionHelp:
    """Tests for expression_help function."""

    def test_expression_help_returns_string(self):
        """Test that expression_help returns a string."""
        help_text = expression_help()
        assert isinstance(help_text, str)
        assert len(help_text) > 0

    def test_expression_help_contains_syntax_info(self):
        """Test that help text includes key syntax components."""
        help_text = expression_help()
        assert "T" in help_text  # Trim
        assert "U" in help_text  # Uppercase
        assert "D" in help_text  # Date normalization
        assert "S(" in help_text  # Substring


def _sample_person_attributes():
    """Build a representative attribute map for token-generation tests."""
    return {
        FirstNameAttribute: "Alice",
        LastNameAttribute: "Wonderland",
        BirthDateAttribute: "1993-08-10",
        SexAttribute: "F",
        SocialSecurityNumberAttribute: "345-54-6795",
    }


def _write_exchange_config(tmp_path: Path) -> tuple[Path, Path, bytes]:
    """Create a test exchange config and matching sender private key file."""
    sender_private_pem, sender_public_pem = generate_key_pair("P-256")
    _, recipient_public_pem = generate_key_pair("P-256")
    exchange_config_path = tmp_path / "test.exchange.json"
    exchange_config_path.write_text(
        json.dumps(
            build_exchange_envelope(
                exchange_name="shared-exchange",
                hashing_secret=b"shared-hashing-secret",
                sender_public_pem=sender_public_pem,
                recipient_public_pem=recipient_public_pem,
                curve="P-256",
                created_at="2026-03-12T00:00:00Z",
                exchange_id="exchange-123",
            )
        ),
        encoding="utf-8",
    )
    private_key_path = tmp_path / "sender.private.pem"
    private_key_path.write_bytes(sender_private_pem)
    return exchange_config_path, private_key_path, sender_private_pem
