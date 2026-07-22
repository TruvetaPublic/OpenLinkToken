# SPDX-License-Identifier: MIT

import logging
from typing import Dict, List, Optional, Set, Type

from openlinktoken.attributes.attribute import Attribute
from openlinktoken.attributes.attribute_loader import AttributeLoader
from openlinktoken.attributes.field_registry import FieldRegistry
from openlinktoken.tokens.base_token_definition import BaseTokenDefinition
from openlinktoken.tokens.token import Token
from openlinktoken.tokens.token_generation_exception import TokenGenerationException
from openlinktoken.tokens.token_generator_result import TokenGeneratorResult
from openlinktoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from openlinktoken.tokens.tokenizer.tokenizer import Tokenizer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer

logger = logging.getLogger(__name__)


class TokenGenerator:
    """Generates both the token signature and the token itself."""

    @classmethod
    def from_transformers(
        cls, token_definition: BaseTokenDefinition, token_transformer_list: List[TokenTransformer]
    ) -> "TokenGenerator":
        """
        Convenience constructor that creates a TokenGenerator with SHA256Tokenizer.

        Args:
            token_definition: The token definition.
            token_transformer_list: A list of token transformers.

        Returns:
            A TokenGenerator instance with SHA256Tokenizer.
        """
        return cls(token_definition, SHA256Tokenizer(token_transformer_list))

    def __init__(
        self,
        token_definition: BaseTokenDefinition,
        tokenizer: Tokenizer,
        field_registry: Optional[FieldRegistry] = None,
    ):
        """
        Initialize the token generator with an explicit tokenizer.

        Args:
            token_definition: The token definition.
            tokenizer: Tokenizer implementation. Use PassthroughTokenizer for plain mode.
            field_registry: Optional custom field registry for field-ID-based lookups.
                When None, a default registry is created from built-in attributes.
        """
        self.token_definition = token_definition
        self.attribute_instance_map: Dict[Type[Attribute], Attribute] = {}

        # Load attributes
        for attribute in AttributeLoader.load():
            self.attribute_instance_map[type(attribute)] = attribute

        self.tokenizer = tokenizer
        self.field_registry = field_registry or FieldRegistry.create_default()

    def _get_token_signature(
        self, token_id: str, person_attributes: Dict[Type[Attribute], str], result: TokenGeneratorResult
    ) -> Optional[str]:
        """
        Get the token signature using a class-keyed person attributes map.

        .. deprecated::
            Use :meth:`_get_token_signature_via_field_id` with a field-ID-keyed map instead.

        Args:
            token_id: The token identifier.
            person_attributes: The person attributes map, keyed by attribute class.
            result: The token generator result.

        Returns:
            The token signature using the token definition for the given token identifier.
        """
        definition = self.token_definition.get_token_definition(token_id)

        if person_attributes is None:
            raise ValueError("Person attributes cannot be null.")

        values = []

        for attribute_expression in definition:
            attribute_class = attribute_expression.attribute_class

            if attribute_class not in person_attributes:
                return None

            attribute = self.attribute_instance_map.get(attribute_class)
            if attribute is None:
                return None

            attribute_value = person_attributes[attribute_class]

            if not attribute.validate(attribute_value):
                result.invalid_attributes.add(attribute.get_name())
                return None

            attribute_value = attribute.normalize(attribute_value)

            try:
                attribute_value = attribute_expression.get_effective_value(attribute_value)
                values.append(attribute_value)
            except ValueError as e:
                logger.error(str(e))
                return None

        # Filter out None and blank values, then join with '|'
        filtered_values = [v for v in values if v is not None and v.strip() != ""]
        return "|".join(filtered_values)

    def get_all_token_signatures(self, person_attributes: Dict[Type[Attribute], str]) -> Dict[str, str]:
        """
        Get the token signatures for all token/rule identifiers using a class-keyed map.

        .. deprecated::
            Use :meth:`get_all_token_signatures_via_field_id` with a field-ID-keyed map instead.

        Args:
            person_attributes: The person attributes map, keyed by attribute class.

        Returns:
            A map of token/rule identifier to the token signature.
        """
        signatures = {}

        for token_id in self.token_definition.get_token_identifiers():
            try:
                signature = self._get_token_signature(token_id, person_attributes, TokenGeneratorResult())
                if signature is not None:
                    signatures[token_id] = signature
            except Exception as e:
                logger.error(f"Error generating token signature for token id: {token_id}", exc_info=e)

        return signatures

    def _get_token(
        self, token_id: str, person_attributes: Dict[Type[Attribute], str], result: TokenGeneratorResult
    ) -> Optional[str]:
        """
        Get token for a given token identifier using a class-keyed person attributes map.

        .. deprecated::
            Use :meth:`get_all_tokens_via_field_id` with a field-ID-keyed map instead.
        """
        signature = self._get_token_signature(token_id, person_attributes, result)
        logger.debug(f"Token signature for token id {token_id}: {signature}")

        try:
            token = self.tokenizer.tokenize(signature)
            # Track blank tokens by rule
            if Token.BLANK == token:
                result.blank_tokens_by_rule.add(token_id)
            return token
        except Exception as e:
            logger.error(f"Error generating token for token id: {token_id}", exc_info=e)
            raise TokenGenerationException("Error generating token", e)

    def get_all_tokens(self, person_attributes: Dict[Type[Attribute], str]) -> TokenGeneratorResult:
        """
        Get the tokens for all token/rule identifiers using a class-keyed person attributes map.

        .. deprecated::
            Use :meth:`get_all_tokens_via_field_id` with a field-ID-keyed ``Dict[str, str]`` map instead.

        Args:
            person_attributes: The person attributes map, keyed by attribute class.

        Returns:
            A TokenGeneratorResult object containing the tokens and invalid attributes.
        """
        result = TokenGeneratorResult()

        for token_id in self.token_definition.get_token_identifiers():
            try:
                token = self._get_token(token_id, person_attributes, result)
                if token is not None:
                    result.tokens[token_id] = token
            except Exception as e:
                logger.error(f"Error generating token for token id: {token_id}", exc_info=e)

        return result

    def get_invalid_person_attributes(self, person_attributes: Dict[Type[Attribute], str]) -> Set[str]:
        """
        Get invalid person attribute names.

        .. deprecated::
            Use field-ID-keyed person attributes with :meth:`get_all_tokens_via_field_id` instead.

        Args:
            person_attributes: The person attributes map, keyed by attribute class.

        Returns:
            A set of invalid person attribute names.
        """
        response = set()

        for attribute_class, value in person_attributes.items():
            attribute = self.attribute_instance_map.get(attribute_class)
            if attribute and not attribute.validate(value):
                response.add(attribute.get_name())

        return response

    # ===== Primary API =====

    def _get_token_signature_via_field_id(
        self, token_id: str, person_attributes: Dict[str, str], result: TokenGeneratorResult
    ) -> Optional[str]:
        """
        Get the token signature for a given token identifier.

        Args:
            token_id: The token identifier.
            person_attributes: Person attributes keyed by field ID (e.g., "LastName" → "Smith").
            result: The token generator result.

        Returns:
            The token signature, or None if required fields are missing or invalid.
        """
        definition = self.token_definition.get_token_definition(token_id)

        if person_attributes is None:
            raise ValueError("Person attributes cannot be null.")

        values = []

        for attribute_expression in definition:
            resolved_field_id = self._resolve_field_id(attribute_expression)
            if resolved_field_id is None or resolved_field_id not in person_attributes:
                return None

            attribute = self._resolve_attribute(attribute_expression, resolved_field_id)
            if attribute is None:
                return None

            attribute_value = person_attributes[resolved_field_id]

            if not attribute.validate(attribute_value):
                result.invalid_attributes.add(attribute.get_name())
                return None

            attribute_value = attribute.normalize(attribute_value)

            try:
                attribute_value = attribute_expression.get_effective_value(attribute_value)
                values.append(attribute_value)
            except ValueError as e:
                logger.error(str(e))
                return None

        filtered_values = [v for v in values if v is not None and v.strip() != ""]
        return "|".join(filtered_values)

    def get_all_tokens_via_field_id(self, person_attributes: Dict[str, str]) -> TokenGeneratorResult:
        """
        Get the tokens for all token/rule identifiers.

        This is the preferred API. It natively supports multiple fields sharing the same
        attribute type (e.g., "MotherLastName" and "FatherLastName" both backed by StringAttribute).

        Args:
            person_attributes: Person attributes keyed by field ID (e.g., "LastName" → "Smith").

        Returns:
            A TokenGeneratorResult object containing the tokens and invalid attributes.
        """
        result = TokenGeneratorResult()

        for token_id in self.token_definition.get_token_identifiers():
            try:
                signature = self._get_token_signature_via_field_id(token_id, person_attributes, result)
                logger.debug(f"Token signature for token id {token_id}: {signature}")
                try:
                    token = self.tokenizer.tokenize(signature)
                    if Token.BLANK == token:
                        result.blank_tokens_by_rule.add(token_id)
                    if token is not None:
                        result.tokens[token_id] = token
                except Exception as e:
                    logger.error(f"Error generating token for token id: {token_id}", exc_info=e)
            except Exception as e:
                logger.error(f"Error generating token for token id: {token_id}", exc_info=e)

        return result

    def get_all_token_signatures_via_field_id(self, person_attributes: Dict[str, str]) -> Dict[str, str]:
        """
        Get the token signatures for all token/rule identifiers. Mostly useful for debugging.

        Args:
            person_attributes: Person attributes keyed by field ID.

        Returns:
            A map of token/rule identifier to the token signature.
        """
        signatures = {}

        for token_id in self.token_definition.get_token_identifiers():
            try:
                signature = self._get_token_signature_via_field_id(token_id, person_attributes, TokenGeneratorResult())
                if signature is not None:
                    signatures[token_id] = signature
            except Exception as e:
                logger.error(f"Error generating token signature for token id: {token_id}", exc_info=e)

        return signatures

    def _resolve_field_id(self, expression) -> Optional[str]:
        """Resolve the effective field ID from an AttributeExpression."""
        if expression.field_id is not None:
            return expression.field_id
        # Legacy fallback: derive field ID from attribute class name
        attribute = self.attribute_instance_map.get(expression.attribute_class)
        return attribute.get_name() if attribute else None

    def _resolve_attribute(self, expression, resolved_field_id: str) -> Optional[Attribute]:
        """Resolve the attribute instance for an expression and field ID."""
        # Try field registry first
        from_registry = self.field_registry.get_attribute(resolved_field_id)
        if from_registry is not None:
            return from_registry
        # Fallback to class-based lookup
        return self.attribute_instance_map.get(expression.attribute_class)
