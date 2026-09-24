# SPDX-License-Identifier: MIT

"""Integration tests for field-ID-based token generation API."""

from openlinktoken.attributes.attribute_expression import AttributeExpression
from openlinktoken.attributes.field_registry import FieldRegistry
from openlinktoken.attributes.general.string_attribute import StringAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.sex_attribute import SexAttribute
from openlinktoken.tokens.base_token_definition import BaseTokenDefinition
from openlinktoken.tokens.token_generator import TokenGenerator
from openlinktoken.tokens.tokenizer.passthrough_tokenizer import PassthroughTokenizer


class _MultiFieldTokenDefinition(BaseTokenDefinition):
    """Token definition with multiple StringAttribute fields for testing."""

    def __init__(self):
        self._definitions = {
            "T_MULTI": [
                AttributeExpression.of("MotherLastName", StringAttribute, "T|U"),
                AttributeExpression.of("FatherLastName", StringAttribute, "T|U"),
                AttributeExpression.of("FirstName", FirstNameAttribute, "T|S(0,1)|U"),
            ],
            "T_LEGACY": [
                AttributeExpression(LastNameAttribute, "T|U"),
                AttributeExpression(FirstNameAttribute, "T|S(0,1)|U"),
                AttributeExpression(SexAttribute, "T|U"),
            ],
        }

    def get_version(self):
        return "test"

    def get_token_identifiers(self):
        return set(self._definitions.keys())

    def get_token_definition(self, token_id):
        return self._definitions.get(token_id, [])


class TestTokenGeneratorFieldIdApi:
    """Test the field-ID-based token generation API."""

    def setup_method(self):
        """Set up test fixtures."""
        string_attr = StringAttribute()
        registry = (
            FieldRegistry.Builder.from_defaults()
            .register("MotherLastName", StringAttribute, string_attr)
            .register("FatherLastName", StringAttribute, string_attr)
            .build()
        )
        self.token_definition = _MultiFieldTokenDefinition()
        self.token_generator = TokenGenerator(
            self.token_definition,
            PassthroughTokenizer([]),
            field_registry=registry,
        )

    def test_multi_field_same_type_generates_token(self):
        """Test that two StringAttribute fields produce a valid token signature."""
        person = {
            "MotherLastName": "Garcia",
            "FatherLastName": "Lopez",
            "FirstName": "Ana",
        }

        result = self.token_generator.get_all_tokens_via_field_id(person)
        assert "T_MULTI" in result.tokens
        assert result.tokens["T_MULTI"] == "GARCIA|LOPEZ|A"

    def test_multi_field_missing_field_skips_token(self):
        """Test that a missing field causes the token to produce BLANK."""
        person = {
            "MotherLastName": "Garcia",
            "FirstName": "Ana",
        }

        result = self.token_generator.get_all_tokens_via_field_id(person)
        # T_MULTI should get BLANK since FatherLastName is missing
        from openlinktoken.tokens.token import Token

        assert result.tokens.get("T_MULTI") == Token.BLANK

    def test_legacy_expressions_work_with_field_id_api(self):
        """Test that legacy (class-based) expressions still work via field ID resolution."""
        person = {
            "LastName": "Smith",
            "FirstName": "John",
            "Sex": "M",
        }

        result = self.token_generator.get_all_tokens_via_field_id(person)
        assert "T_LEGACY" in result.tokens
        assert result.tokens["T_LEGACY"] == "SMITH|J|MALE"

    def test_signatures_by_field_id(self):
        """Test getting token signatures using field-ID-based API."""
        person = {
            "MotherLastName": "Garcia",
            "FatherLastName": "Lopez",
            "FirstName": "Ana",
            "LastName": "Smith",
            "Sex": "F",
        }

        signatures = self.token_generator.get_all_token_signatures_via_field_id(person)
        assert "T_MULTI" in signatures
        assert signatures["T_MULTI"] == "GARCIA|LOPEZ|A"
        assert "T_LEGACY" in signatures
        assert signatures["T_LEGACY"] == "SMITH|A|FEMALE"

    def test_invalid_attribute_tracked(self):
        """Test that invalid values are tracked in the result."""
        person = {
            "MotherLastName": "",
            "FatherLastName": "Lopez",
            "FirstName": "Ana",
        }

        result = self.token_generator.get_all_tokens_via_field_id(person)
        # T_MULTI should be BLANK since MotherLastName is empty (invalid)
        from openlinktoken.tokens.token import Token

        assert result.tokens.get("T_MULTI") == Token.BLANK
        assert len(result.invalid_attributes) > 0
