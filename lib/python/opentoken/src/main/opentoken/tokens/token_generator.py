"""
Copyright (c) Truveta. All rights reserved.
"""

import logging
from importlib.metadata import entry_points
from typing import Dict, List, Optional, Set, Type

from opentoken.attributes.attribute import Attribute
from opentoken.attributes.attribute_loader import AttributeLoader
from opentoken.tokens.base_token_definition import BaseTokenDefinition
from opentoken.tokens.inference_signature_provider import InferenceBatchResult, InferenceSignatureProvider  # noqa: F401
from opentoken.tokens.token import Token
from opentoken.tokens.token_generation_exception import TokenGenerationException
from opentoken.tokens.token_generator_result import TokenGeneratorResult
from opentoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from opentoken.tokens.tokenizer.tokenizer import Tokenizer
from opentoken.tokentransformer.token_transformer import TokenTransformer

logger = logging.getLogger(__name__)

_inference_provider: Optional[InferenceSignatureProvider] = None
_provider_discovered = False


def _get_inference_provider() -> Optional[InferenceSignatureProvider]:
    """Lazily discover and cache the first registered InferenceSignatureProvider."""
    global _inference_provider, _provider_discovered
    if not _provider_discovered:
        _provider_discovered = True
        eps = entry_points(group="opentoken.inference_providers")
        for ep in eps:
            try:
                provider_cls = ep.load()
                _inference_provider = provider_cls()
                break
            except Exception:
                pass
    return _inference_provider


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
        provider = _get_inference_provider()
        if provider is not None and provider.get_token_id() == token_id and provider.is_enabled():
            try:
                return provider.generate_signature(person_attributes)
            except Exception as error:
                logger.error("Error generating token signature for token id: %s", token_id, exc_info=error)
                return None

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

    def generate_tokens_excluding(
        self,
        person_attributes: Dict[Type[Attribute], str],
        excluded_token_ids: Set[str],
    ) -> TokenGeneratorResult:
        """Get tokens for all rules except those in *excluded_token_ids*.

        Args:
            person_attributes: The person attributes map.
            excluded_token_ids: Set of token identifiers to skip.

        Returns:
            A TokenGeneratorResult object containing the tokens and invalid attributes.
        """
        result = TokenGeneratorResult()

        for token_id in self.token_definition.get_token_identifiers():
            if token_id in excluded_token_ids:
                continue
            try:
                token = self._get_token(token_id, person_attributes, result)
                if token is not None:
                    result.tokens[token_id] = token
            except Exception as error:
                logger.error(f"Error generating token for token id: {token_id}", exc_info=error)

        return result

    def apply_precomputed_signature(
        self, result: TokenGeneratorResult, token_id: str, signature: Optional[str]
    ) -> None:
        """Tokenize and store a token from a precomputed signature.

        Args:
            result: The token generator result to update.
            token_id: The token identifier key to store the result under.
            signature: The precomputed signature string, or ``None`` for a blank token.
        """
        try:
            token = self.tokenizer.tokenize(signature)
            result.tokens[token_id] = token
            if Token.BLANK == token:
                result.blank_tokens_by_rule.add(token_id)
        except Exception as error:
            logger.error("Error generating token for token id: %s", token_id, exc_info=error)
            result.tokens[token_id] = Token.BLANK
            result.blank_tokens_by_rule.add(token_id)

    def store_raw_token(self, result: TokenGeneratorResult, token_id: str, token_value: Optional[str]) -> None:
        """Store a pre-computed token value directly, bypassing the tokenizer and all transformers.

        Use for tokens whose value is already in its final form (e.g., internally
        pre-hashed signatures such as T6 rotation values).

        Args:
            result: The token generator result to update.
            token_id: The token identifier key to store the result under.
            token_value: The final token value, or ``None`` / blank to record a blank token.
        """
        if token_value and token_value != Token.BLANK:
            result.tokens[token_id] = token_value
        else:
            result.tokens[token_id] = Token.BLANK
            result.blank_tokens_by_rule.add(token_id)

    def apply_embedding_derived_tokens(
        self,
        result: TokenGeneratorResult,
        token_id_prefix: str,
        token_strings: List[str],
    ) -> None:
        """Apply pre-computed embedding-derived tokens to the result.

        Args:
            result: The token generator result to update.
            token_id_prefix: Prefix for derived token keys (e.g. ``"T6-R"``).
            token_strings: Pre-computed token strings from the embedding transformer.
        """
        for i, token_string in enumerate(token_strings):
            result.tokens[f"{token_id_prefix}{i}"] = token_string

    @staticmethod
    def get_inference_provider() -> Optional[InferenceSignatureProvider]:
        """Return the discovered InferenceSignatureProvider, or None if none is installed."""
        return _get_inference_provider()

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
