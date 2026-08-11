# SPDX-License-Identifier: MIT

import logging
from importlib.metadata import entry_points
from typing import Dict, List, Optional, Set, Type

from openlinktoken.attributes.attribute import Attribute
from openlinktoken.attributes.attribute_loader import AttributeLoader
from openlinktoken.attributes.field_registry import FieldRegistry
from openlinktoken.tokens.base_token_definition import BaseTokenDefinition
from openlinktoken.tokens.inference_signature_provider import (  # noqa: F401
    InferenceBatchResult,
    InferenceSignatureProvider,
)
from openlinktoken.tokens.token import Token
from openlinktoken.tokens.token_generation_exception import TokenGenerationException
from openlinktoken.tokens.token_generator_result import TokenGeneratorResult
from openlinktoken.tokens.tokenizer.passthrough_tokenizer import PassthroughTokenizer
from openlinktoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from openlinktoken.tokens.tokenizer.tokenizer import Tokenizer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer

logger = logging.getLogger(__name__)

_inference_provider: Optional[InferenceSignatureProvider] = None
_provider_discovered = False


def _get_inference_provider() -> Optional[InferenceSignatureProvider]:
    """Lazily discover and cache the first registered InferenceSignatureProvider."""
    global _inference_provider, _provider_discovered
    if not _provider_discovered:
        _provider_discovered = True
        eps = entry_points(group="openlinktoken.inference_providers")
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
        if person_attributes is None:
            raise ValueError("Person attributes cannot be null.")

        if self._has_active_inference_provider(token_id):
            return self._get_inference_signature(token_id, self._to_field_id_map(person_attributes))

        definition = self.token_definition.get_token_definition(token_id)
        if definition is None or not definition:
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

        definition = self.token_definition.get_token_definition(token_id)
        token_has_active_provider = self._has_active_inference_provider(token_id)

        # Inference-only tokens (empty definition, no active provider) produce no output by design;
        # skip tokenizing entirely rather than recording a spurious blank.
        if not definition and not token_has_active_provider:
            return None

        return self._tokenize_signature(token_id, signature, result)

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
        """Store a pre-hashed token value, applying only non-hash transformers (e.g. encryption).

        Use for tokens that are already hashed (e.g. ML1 HMAC rotation values).
        HashTokenTransformer is skipped to avoid re-hashing; all other transformers
        (e.g. EncryptTokenTransformer) are still applied via PassthroughTokenizer.

        Args:
            result: The token generator result to update.
            token_id: The token identifier key to store the result under.
            token_value: The pre-hashed token value, or ``None`` / blank to record a blank token.
        """
        all_transformers = self.tokenizer.get_token_transformer_list()
        encrypt_transformers = [t for t in all_transformers if not isinstance(t, HashTokenTransformer)]
        passthrough = PassthroughTokenizer(encrypt_transformers)
        try:
            token = passthrough.tokenize(token_value)
            result.tokens[token_id] = token
            if Token.BLANK == token:
                result.blank_tokens_by_rule.add(token_id)
        except Exception as error:
            logger.error("Error storing raw token for token id: %s", token_id, exc_info=error)
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
            token_id_prefix: Prefix for derived token keys (e.g. ``"ML1-R"``).
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
        if person_attributes is None:
            raise ValueError("Person attributes cannot be null.")

        if self._has_active_inference_provider(token_id):
            return self._get_inference_signature(token_id, person_attributes)

        definition = self.token_definition.get_token_definition(token_id)
        if not definition:
            return None

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
        return self.generate_tokens_excluding_via_field_id(person_attributes, set())

    def generate_tokens_excluding_via_field_id(
        self,
        person_attributes: Dict[str, str],
        excluded_token_ids: Set[str],
    ) -> TokenGeneratorResult:
        """Get field-ID tokens while skipping the requested token identifiers.

        Args:
            person_attributes: Person attributes keyed by field ID.
            excluded_token_ids: Token identifiers to omit before signature generation.

        Returns:
            A TokenGeneratorResult object containing the generated tokens and invalid attributes.
        """
        result = TokenGeneratorResult()

        for token_id in self.token_definition.get_token_identifiers():
            if token_id in excluded_token_ids:
                continue
            try:
                definition = self.token_definition.get_token_definition(token_id)
                if not definition and not self._has_active_inference_provider(token_id):
                    continue
                signature = self._get_token_signature_via_field_id(token_id, person_attributes, result)
                logger.debug(f"Token signature for token id {token_id}: {signature}")
                token = self._tokenize_signature(token_id, signature, result)
                if token is not None:
                    result.tokens[token_id] = token
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

    @staticmethod
    def _has_active_provider_for_token(token_id: str, provider: Optional[InferenceSignatureProvider]) -> bool:
        return provider is not None and provider.get_token_id() == token_id and provider.is_enabled()

    def _has_active_inference_provider(self, token_id: str) -> bool:
        return self._has_active_provider_for_token(token_id, _get_inference_provider())

    def _get_inference_signature(self, token_id: str, person_attributes: Dict[str, str]) -> Optional[str]:
        provider = _get_inference_provider()
        if not self._has_active_provider_for_token(token_id, provider):
            return None
        try:
            return provider.generate_signature(person_attributes)
        except Exception as error:
            logger.error("Error generating token signature for token id: %s", token_id, exc_info=error)
            return None

    def _tokenize_signature(
        self, token_id: str, signature: Optional[str], result: TokenGeneratorResult
    ) -> Optional[str]:
        try:
            if self._has_active_inference_provider(token_id):
                transformers = [
                    transformer
                    for transformer in self.tokenizer.get_token_transformer_list()
                    if not isinstance(transformer, HashTokenTransformer)
                ]
                token = PassthroughTokenizer(transformers).tokenize(signature)
            else:
                token = self.tokenizer.tokenize(signature)
            if Token.BLANK == token:
                result.blank_tokens_by_rule.add(token_id)
            return token
        except Exception as error:
            logger.error("Error generating token for token id: %s", token_id, exc_info=error)
            raise TokenGenerationException("Error generating token", error)

    def _to_field_id_map(self, person_attributes: Dict[Type[Attribute], str]) -> Dict[str, str]:
        return {
            attribute.get_name(): value
            for attribute_class, value in person_attributes.items()
            if (attribute := self.attribute_instance_map.get(attribute_class)) is not None
        }

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
