"""
Copyright (c) Truveta. All rights reserved.
"""

import logging
from collections import OrderedDict
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Type

from opentoken.attributes.attribute import Attribute
from opentoken.attributes.attribute_loader import AttributeLoader
from opentoken.attributes.person.birth_date_attribute import BirthDateAttribute
from opentoken.attributes.person.first_name_attribute import FirstNameAttribute
from opentoken.attributes.person.last_name_attribute import LastNameAttribute
from opentoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from opentoken.attributes.person.sex_attribute import SexAttribute
from opentoken.tokens.base_token_definition import BaseTokenDefinition
from opentoken.tokens.t6_inference_config import T6InferenceConfig
from opentoken.tokens.t6_onnx_signature_generator import T6OnnxSignatureGenerator, t6_payload_to_json
from opentoken.tokens.token import Token
from opentoken.tokens.token_generation_exception import TokenGenerationException
from opentoken.tokens.token_generator_result import TokenGeneratorResult
from opentoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from opentoken.tokens.tokenizer.tokenizer import Tokenizer
from opentoken.tokentransformer.token_transformer import TokenTransformer

if TYPE_CHECKING:
    import numpy as np

    from opentoken.tokentransformer.rotation.embedding_transformer import EmbeddingTransformer

logger = logging.getLogger(__name__)


class TokenGenerator:
    """Generates both the token signature and the token itself."""

    T6_RULE_ID = "T6"

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

    def __init__(self, token_definition: BaseTokenDefinition, tokenizer: Tokenizer):
        """
        Initialize the token generator with an explicit tokenizer.

        Args:
            token_definition: The token definition.
            tokenizer: Tokenizer implementation. Use PassthroughTokenizer for plain mode.
        """
        self.token_definition = token_definition
        self.attribute_instance_map: Dict[Type[Attribute], Attribute] = {}

        # Load attributes
        for attribute in AttributeLoader.load():
            self.attribute_instance_map[type(attribute)] = attribute

        self.tokenizer = tokenizer

    def _get_token_signature(
        self, token_id: str, person_attributes: Dict[Type[Attribute], str], result: TokenGeneratorResult
    ) -> Optional[str]:
        """
        Get the token signature for a given token identifier.

        Populates the invalid_attributes list in the result object with the attributes
        that are invalid.

        Args:
            token_id: The token identifier.
            person_attributes: The person attributes map.
            result: The token generator result.

        Returns:
            The token signature using the token definition for the given token identifier.
        """
        if token_id == self.T6_RULE_ID:
            return self._get_t6_signature(person_attributes, result)

        definition = self.token_definition.get_token_definition(token_id)

        if person_attributes is None:
            raise ValueError("Person attributes cannot be null.")

        if definition is None:
            return None

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

    def _get_t6_signature(
        self,
        person_attributes: Dict[Type[Attribute], str],
        result: TokenGeneratorResult,
    ) -> Optional[str]:
        """Build T6 signature using ONNX-backed inference when enabled."""
        if not T6InferenceConfig.is_enabled():
            return None

        payload_json = self.build_t6_payload(person_attributes, result)
        if payload_json is None:
            return None

        try:
            return T6OnnxSignatureGenerator.generate_signature(payload_json)
        except Exception as error:
            logger.error("Error generating token signature for token id: T6", exc_info=error)
            return None

    def build_t6_payload(
        self,
        person_attributes: Dict[Type[Attribute], str],
        result: TokenGeneratorResult,
    ) -> Optional[str]:
        """Build and validate the deterministic JSON payload required for T6 inference."""
        if person_attributes is None:
            return None

        payload: "OrderedDict[str, str]" = OrderedDict()
        if not self._add_t6_field(PostalCodeAttribute, "PostalCode", person_attributes, result, payload):
            return None
        if not self._add_t6_field(BirthDateAttribute, "Birthdate", person_attributes, result, payload):
            return None
        if not self._add_t6_field(FirstNameAttribute, "GivenName", person_attributes, result, payload):
            return None
        if not self._add_t6_field(LastNameAttribute, "Surname", person_attributes, result, payload):
            return None
        if not self._add_t6_field(SexAttribute, "Gender", person_attributes, result, payload):
            return None

        return t6_payload_to_json(payload)

    def _add_t6_field(
        self,
        attribute_class: Type[Attribute],
        field_name: str,
        person_attributes: Dict[Type[Attribute], str],
        result: TokenGeneratorResult,
        payload: "OrderedDict[str, str]",
    ) -> bool:
        """Validate, normalize, and append one required field for T6 payload."""
        if attribute_class not in person_attributes:
            return False

        attribute = self.attribute_instance_map.get(attribute_class)
        if attribute is None:
            return False

        value = person_attributes[attribute_class]
        if not attribute.validate(value):
            result.invalid_attributes.add(attribute.get_name())
            return False

        normalized = attribute.normalize(value)
        if normalized is None or normalized.strip() == "":
            result.invalid_attributes.add(attribute.get_name())
            return False

        payload[field_name] = normalized
        return True

    def get_all_token_signatures(self, person_attributes: Dict[Type[Attribute], str]) -> Dict[str, str]:
        """
        Get the token signatures for all token/rule identifiers.

        This is mostly a debug/logging/test method.

        Args:
            person_attributes: The person attributes map.

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
        Get token for a given token identifier.

        Args:
            token_id: The token identifier.
            person_attributes: The person attributes map.
            result: The token generator result.

        Returns:
            The token using the token definition for the given token identifier.

        Raises:
            TokenGenerationException: In case of failure to generate the token.
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
        Get the tokens for all token/rule identifiers.

        Args:
            person_attributes: The person attributes map.

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

    def get_all_tokens_excluding_t6(self, person_attributes: Dict[Type[Attribute], str]) -> TokenGeneratorResult:
        """Get tokens for all rules except T6."""
        result = TokenGeneratorResult()

        for token_id in self.token_definition.get_token_identifiers():
            if token_id == self.T6_RULE_ID:
                continue
            try:
                token = self._get_token(token_id, person_attributes, result)
                if token is not None:
                    result.tokens[token_id] = token
            except Exception as error:
                logger.error(f"Error generating token for token id: {token_id}", exc_info=error)

        return result

    def apply_t6_signature_token(self, result: TokenGeneratorResult, signature: Optional[str]) -> None:
        """Tokenize and store T6 token from a precomputed T6 signature."""
        try:
            token = self.tokenizer.tokenize(signature)
            result.tokens[self.T6_RULE_ID] = token
            if Token.BLANK == token:
                result.blank_tokens_by_rule.add(self.T6_RULE_ID)
        except Exception as error:
            logger.error("Error generating token for token id: T6", exc_info=error)
            result.tokens[self.T6_RULE_ID] = Token.BLANK
            result.blank_tokens_by_rule.add(self.T6_RULE_ID)

    def apply_t6_rotation_tokens(
        self,
        result: TokenGeneratorResult,
        embedding: "np.ndarray",
        transformer: "EmbeddingTransformer",
    ) -> None:
        """Apply T6 rotation tokens to the result from a precomputed raw embedding.

        Generates tokens named "T6-R0", "T6-R1", ..., "T6-R{N-1}" (one per rotation
        matrix) and stores them in result.tokens.

        Args:
            result: Token generator result to populate.
            embedding: Raw CLS embedding float array (1-D).
            transformer: Rotation embedding transformer.
        """
        try:
            tokens = transformer.transform(embedding.tolist())
            for i, token in enumerate(tokens):
                result.tokens[f"T6-R{i}"] = token
        except Exception as error:
            logger.error("Error generating T6 rotation tokens", exc_info=error)

    def get_invalid_person_attributes(self, person_attributes: Dict[Type[Attribute], str]) -> Set[str]:
        """
        Get invalid person attribute names.

        Args:
            person_attributes: The person attributes map.

        Returns:
            A set of invalid person attribute names.
        """
        response = set()

        for attribute_class, value in person_attributes.items():
            attribute = self.attribute_instance_map.get(attribute_class)
            if attribute and not attribute.validate(value):
                response.add(attribute.get_name())

        return response
