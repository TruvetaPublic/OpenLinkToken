"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import Dict, Type

from opentoken.attributes.attribute import Attribute
from opentoken.attributes.general.record_id_attribute import RecordIdAttribute
from opentoken.attributes.person.birth_date_attribute import BirthDateAttribute
from opentoken.attributes.person.first_name_attribute import FirstNameAttribute
from opentoken.attributes.person.last_name_attribute import LastNameAttribute
from opentoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from opentoken.attributes.person.sex_attribute import SexAttribute
from opentoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
from opentoken.tokens.token import Token
from opentoken.tokens.token_definition import TokenDefinition
from opentoken.tokens.token_generator import TokenGenerator
from opentoken.tokens.token_generator_result import TokenGeneratorResult
from opentoken.tokentransformer.no_operation_token_transformer import NoOperationTokenTransformer


class TestTokenGeneratorBlankTokens:
    """Test cases for TokenGenerator blank token tracking functionality."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Setup real TokenDefinition and TokenTransformers for testing
        self.token_definition = TokenDefinition()
        self.token_transformer_list = [NoOperationTokenTransformer()]

        self.token_generator = TokenGenerator.from_transformers(self.token_definition, self.token_transformer_list)

    def test_blank_tokens_tracking_with_invalid_attributes(self):
        """Test blank token tracking when attributes are missing for token generation."""
        # Create person attributes with missing postal code (required for T2)
        person_attributes: Dict[Type[Attribute], str] = {
            RecordIdAttribute: "123",
            FirstNameAttribute: "John",
            LastNameAttribute: "Doe",
            SexAttribute: "Male",
            BirthDateAttribute: "1990-01-01",
            SocialSecurityNumberAttribute: "123456789",
            # Missing PostalCodeAttribute intentionally to force T2 to generate blank token
        }

        result = self.token_generator.get_all_tokens(person_attributes)

        # Verify that tokens were generated
        assert len(result.tokens) > 0

        # T2 should generate a blank token due to missing postal code
        blank_tokens_by_rule = result.blank_tokens_by_rule
        assert "T2" in blank_tokens_by_rule, "T2 should generate blank token due to missing postal code"

        # Verify that the blank token is the expected BLANK value
        assert result.tokens.get("T2") == Token.BLANK

    def test_blank_tokens_tracking_with_invalid_ssn(self):
        """Test blank token tracking when SSN is invalid."""
        # Create person attributes with invalid SSN (required for T4)
        person_attributes: Dict[Type[Attribute], str] = {
            RecordIdAttribute: "123",
            FirstNameAttribute: "John",
            LastNameAttribute: "Doe",
            SexAttribute: "Male",
            BirthDateAttribute: "1990-01-01",
            SocialSecurityNumberAttribute: "111-11-1111",  # Invalid SSN from the INVALID_SSNS set
            PostalCodeAttribute: "12345",
        }

        result = self.token_generator.get_all_tokens(person_attributes)

        # Verify that tokens were generated
        assert len(result.tokens) > 0

        # T4 should generate a blank token due to invalid SSN
        blank_tokens_by_rule = result.blank_tokens_by_rule
        assert "T4" in blank_tokens_by_rule, "T4 should generate blank token due to invalid SSN"

        # Verify that the blank token is the expected BLANK value
        assert result.tokens.get("T4") == Token.BLANK

    def test_blank_tokens_tracking_with_valid_attributes(self):
        """Test blank token tracking when all attributes are valid."""
        # Create person attributes with all valid data
        person_attributes: Dict[Type[Attribute], str] = {
            RecordIdAttribute: "123",
            FirstNameAttribute: "John",
            LastNameAttribute: "Doe",
            SexAttribute: "Male",
            BirthDateAttribute: "1990-01-01",
            SocialSecurityNumberAttribute: "223-45-6789",
            PostalCodeAttribute: "22345",
        }

        result = self.token_generator.get_all_tokens(person_attributes)

        # Verify that tokens were generated
        assert len(result.tokens) > 0

        # No blank tokens should be generated with valid data
        blank_tokens_by_rule = result.blank_tokens_by_rule
        assert len(blank_tokens_by_rule) == 0, "No blank tokens should be generated with valid data"

        # Verify that no tokens have the BLANK value
        for token in result.tokens.values():
            assert token != Token.BLANK, "No token should be empty with valid data"

    def test_blank_tokens_tracking_initial_state(self):
        """Test that TokenGeneratorResult initializes with empty blank tokens set."""
        result = TokenGeneratorResult()

        # Initially, blank tokens set should be empty
        blank_tokens_by_rule = result.blank_tokens_by_rule
        assert len(blank_tokens_by_rule) == 0, "Initial blank tokens set should be empty"

    def test_blank_tokens_tracking_multiple_invalid_attributes(self):
        """Test blank token tracking when multiple attributes cause blank tokens."""
        # Create person attributes with multiple issues
        person_attributes: Dict[Type[Attribute], str] = {
            RecordIdAttribute: "123",
            FirstNameAttribute: "John",
            LastNameAttribute: "Doe",
            SexAttribute: "Male",
            BirthDateAttribute: "1990-01-01",
            SocialSecurityNumberAttribute: "111-11-1111",  # Invalid SSN
            # Missing PostalCodeAttribute - this should cause issues for T2
        }

        result = self.token_generator.get_all_tokens(person_attributes)

        # Verify that multiple blank tokens are tracked
        blank_tokens_by_rule = result.blank_tokens_by_rule

        # Should have blank tokens for rules that require these attributes
        assert len(blank_tokens_by_rule) > 0, "Should have blank tokens for invalid/missing attributes"

    def test_blank_tokens_set_immutability(self):
        """Test that the blank tokens set behaves correctly."""
        result = TokenGeneratorResult()

        # Get the blank tokens set
        blank_tokens_by_rule = result.blank_tokens_by_rule

        # Add a rule ID
        blank_tokens_by_rule.add("TEST_RULE")

        # Verify it was added
        assert "TEST_RULE" in blank_tokens_by_rule

        # Verify the set contains the expected element
        assert len(blank_tokens_by_rule) == 1
