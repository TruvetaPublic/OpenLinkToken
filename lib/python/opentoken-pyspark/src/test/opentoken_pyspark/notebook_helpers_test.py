"""
Copyright (c) Truveta. All rights reserved.

Tests for notebook helper utilities.
"""

import pytest

from opentoken_pyspark.notebook_helpers import (
    CustomTokenDefinition,
    TokenBuilder,
    create_token_generator,
    expression_help,
    list_attributes,
    quick_token,
)


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
