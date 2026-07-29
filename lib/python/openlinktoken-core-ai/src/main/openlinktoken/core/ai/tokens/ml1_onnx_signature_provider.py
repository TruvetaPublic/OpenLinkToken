"""ONNX-backed ML1 signature provider for Open Link Token."""

from __future__ import annotations

import hashlib
import logging
from threading import Lock
from typing import ClassVar, Dict, List, Optional, Type

from openlinktoken.attributes.attribute import Attribute
from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from openlinktoken.attributes.person.sex_attribute import SexAttribute
from openlinktoken.core.ai.tokens.ml1_inference_config import ML1InferenceConfig
from openlinktoken.core.ai.tokens.ml1_onnx_signature_generator import (
    ML1OnnxSignatureGenerator,
    ml1_payload_to_json,
)
from openlinktoken.core.ai.tokens.ml1_token import ML1Token
from openlinktoken.core.ai.tokens.rotation_config import RotationConfig
from openlinktoken.core.ai.tokentransformer.rotation.rotation_embedding_transformer import (
    RotationEmbeddingTransformer,
)
from openlinktoken.tokens.definitions.t1_token import T1Token
from openlinktoken.tokens.inference_signature_provider import InferenceBatchResult
from openlinktoken.tokens.token import Token
from openlinktoken.tokens.token_generator_result import TokenGeneratorResult

logger = logging.getLogger(__name__)

# Pre-built T1 expression pipeline — reused across all signature computations.
_T1_DEFINITION = T1Token().get_definition()
_T1_ATTRIBUTE_INSTANCES = {expr.attribute_class: expr.attribute_class() for expr in _T1_DEFINITION}


def _compute_t1_signature(person_attributes: Dict[Type[Attribute], str]) -> Optional[str]:
    """Compute the raw (pre-transformer) T1 signature from person attributes.

    Applies the same attribute-expression pipeline as the T1 token definition:
    LASTNAME|FIRSTINITIAL|SEX|BIRTHDATE (each normalized via its expression).
    Returns None when any required T1 attribute is absent or invalid.
    """
    values = []
    for attr_expr in _T1_DEFINITION:
        attr_cls = attr_expr.attribute_class
        raw = person_attributes.get(attr_cls)
        if not raw:
            return None
        attr = _T1_ATTRIBUTE_INSTANCES[attr_cls]
        if not attr.validate(raw):
            return None
        normalized = attr.normalize(raw)
        try:
            effective = attr_expr.get_effective_value(normalized)
            if effective:
                values.append(effective)
        except ValueError:
            return None
    return "|".join(values) if values else None


def _compute_blocking_key(
    person_attributes: Dict[Type[Attribute], str],
) -> Optional[str]:
    """Compute the SHA-256 T1 blocking key used by PersonMatching rotations."""
    t1_signature = _compute_t1_signature(person_attributes)
    if t1_signature is None:
        return None
    return hashlib.sha256(t1_signature.encode("utf-8")).hexdigest()


def _hash_rotation_values(rotation_values: List[str], blocking_key: Optional[str]) -> Optional[List[str]]:
    """SHA-256 hash each rotation-quantized string concatenated with the blocking key.

    Args:
        rotation_values: Space-separated bin-index strings, one per rotation matrix.
        blocking_key: SHA-256 T1 blocking key appended to each rotation value before hashing,
            or None when the key cannot be computed.

    Returns:
        List of SHA-256 hex digest strings, or None when no blocking key is available.
    """
    if not blocking_key:
        return None
    return [
        hashlib.sha256((rotation_value + blocking_key).encode("utf-8")).hexdigest()
        for rotation_value in rotation_values
    ]


def _build_rotation_signature(rotation_values: List[str], blocking_key: Optional[str]) -> str:
    """Build a hashed rotation signature or return the canonical blank token."""
    hashed_values = _hash_rotation_values(rotation_values, blocking_key)
    return Token.BLANK if hashed_values is None else ",".join(hashed_values)


# Ordered field name mapping for ML1 payload.
# Order matches generate_embeddings.py: PostalCode, Birthdate, GivenName, Surname, Gender.
_ML1_FIELDS = [
    (PostalCodeAttribute, "PostalCode"),
    (BirthDateAttribute, "Birthdate"),
    (FirstNameAttribute, "GivenName"),
    (LastNameAttribute, "Surname"),
    (SexAttribute, "Gender"),
]

# Pre-built attribute instances for ML1 validation and normalization — reused across all calls.
_ML1_ATTRIBUTE_INSTANCES = {attr_cls: attr_cls() for attr_cls, _ in _ML1_FIELDS}


class ML1OnnxSignatureProvider:
    """ONNX-backed implementation of InferenceSignatureProvider for ML1 tokens."""

    # Class-level rotation transformer cache so expensive matrix generation
    # (O(N^3) for N=embedding_dim) is paid only once per process lifetime.
    _rotation_transformer: ClassVar[Optional[RotationEmbeddingTransformer]] = None
    _rotation_transformer_lock: ClassVar[Lock] = Lock()

    def get_token_id(self) -> str:
        """Return the registry identifier for the ML1 inference provider."""
        return ML1Token.TOKEN_ID

    def is_enabled(self) -> bool:
        """Return whether ML1 inference is enabled in the runtime configuration."""
        return ML1InferenceConfig.is_enabled()

    @classmethod
    def _get_rotation_transformer(cls, embedding_dim: int) -> Optional[RotationEmbeddingTransformer]:
        """Return the (lazily built) rotation transformer, or None if rotation is disabled."""
        if not RotationConfig.is_enabled():
            return None
        if cls._rotation_transformer is None:
            with cls._rotation_transformer_lock:
                if cls._rotation_transformer is None:
                    cls._rotation_transformer = RotationEmbeddingTransformer(
                        iv=RotationConfig.get_rotation_iv(),
                        rotation_count=RotationConfig.get_rotation_count(),
                        dimension=embedding_dim,
                        hash_dimension=RotationConfig.get_hash_dimension(),
                        bias=RotationConfig.get_dimension_bias(),
                        bin_width=RotationConfig.get_bin_width(),
                        min_val=RotationConfig.get_min_val(),
                        max_val=RotationConfig.get_max_val(),
                    )
        return cls._rotation_transformer

    def generate_signature(self, person_attributes: Dict[Type[Attribute], str]) -> Optional[str]:
        """Generate a single ML1 signature via ONNX inference.

        Pipeline: ONNX embed → rotate → quantize → SHA-256 hash with T1 signature.
        Falls back to raw hex embedding string when rotation is disabled.
        """
        result = TokenGeneratorResult()
        payload_json = self.build_ml1_payload(person_attributes, result)
        if payload_json is None:
            return None
        try:
            sig, embedding = ML1OnnxSignatureGenerator._generate_signature_with_embedding(payload_json)
            if RotationConfig.is_enabled() and embedding is not None:
                transformer = self._get_rotation_transformer(len(embedding))
                if transformer is not None:
                    rotation_values: List[str] = transformer.transform(list(embedding))
                    blocking_key = _compute_blocking_key(person_attributes)
                    return _build_rotation_signature(rotation_values, blocking_key)
            return sig
        except Exception as error:
            logger.error("Error generating ML1 signature", exc_info=error)
            return None

    def generate_batch(self, rows: List[Dict[Type[Attribute], str]]) -> InferenceBatchResult:
        """Generate ML1 signatures for a batch of records.

        Pipeline per record: ONNX embed → rotate → quantize → SHA-256 hash with T1 signature.
        Falls back to raw hex embedding string when rotation is disabled.
        """
        payloads: List[Optional[str]] = []
        valid_indices: List[int] = []

        for i, row in enumerate(rows):
            result = TokenGeneratorResult()
            payload = self.build_ml1_payload(row, result)
            payloads.append(payload)
            if payload is not None:
                valid_indices.append(i)

        valid_payload_list = [payloads[i] for i in valid_indices]

        signatures: List[Optional[str]] = [None] * len(rows)
        if valid_payload_list:
            batch_sigs, batch_embs = ML1OnnxSignatureGenerator._generate_signatures_with_embeddings(valid_payload_list)

            # Resolve the rotation transformer once for this batch (cached across calls).
            first_emb = next((e for e in batch_embs if e is not None), None)
            transformer: Optional[RotationEmbeddingTransformer] = (
                self._get_rotation_transformer(len(first_emb)) if first_emb is not None else None
            )

            for vi, original_index in enumerate(valid_indices):
                embedding = batch_embs[vi]
                if transformer is not None and embedding is not None:
                    rotation_values: List[str] = transformer.transform(list(embedding))
                    blocking_key = _compute_blocking_key(rows[original_index])
                    signatures[original_index] = _build_rotation_signature(rotation_values, blocking_key)
                else:
                    signatures[original_index] = batch_sigs[vi]

        return InferenceBatchResult(signatures=signatures)

    def build_ml1_payload(
        self,
        person_attributes: Dict[Type[Attribute], str],
        result: TokenGeneratorResult,
    ) -> Optional[str]:
        """Build the deterministic JSON payload for ML1 inference.

        Returns None if any required field is missing, fails validation, or normalizes to empty.
        Field order: PostalCode, Birthdate, GivenName, Surname, Gender.
        """
        payload: Dict[str, str] = {}
        for attr_cls, field_name in _ML1_FIELDS:
            value = person_attributes.get(attr_cls)
            if not value:
                result.invalid_attributes.add(attr_cls.__name__)
                return None
            attr = _ML1_ATTRIBUTE_INSTANCES[attr_cls]
            if not attr.validate(value):
                result.invalid_attributes.add(attr_cls.__name__)
                return None
            normalized = attr.normalize(value)
            if not normalized:
                result.invalid_attributes.add(attr_cls.__name__)
                return None
            payload[field_name] = normalized
        return ml1_payload_to_json(payload)
