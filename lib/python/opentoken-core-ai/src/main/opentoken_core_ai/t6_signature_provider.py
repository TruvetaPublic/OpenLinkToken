"""ONNX-backed T6 signature provider for OpenToken."""

from __future__ import annotations

import hashlib
import logging
from threading import Lock
from typing import ClassVar, Dict, List, Optional, Type

from opentoken.attributes.attribute import Attribute
from opentoken.attributes.person.birth_date_attribute import BirthDateAttribute
from opentoken.attributes.person.first_name_attribute import FirstNameAttribute
from opentoken.attributes.person.last_name_attribute import LastNameAttribute
from opentoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from opentoken.attributes.person.sex_attribute import SexAttribute
from opentoken.tokens.definitions.t1_token import T1Token
from opentoken.tokens.inference_signature_provider import InferenceBatchResult
from opentoken.tokens.token_generator_result import TokenGeneratorResult
from opentoken_core_ai.tokens.rotation_config import RotationConfig
from opentoken_core_ai.tokens.t6_inference_config import T6InferenceConfig
from opentoken_core_ai.tokens.t6_onnx_signature_generator import T6OnnxSignatureGenerator, t6_payload_to_json
from opentoken_core_ai.tokentransformer.rotation.rotation_embedding_transformer import RotationEmbeddingTransformer

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


def _hash_rotation_values(rotation_values: List[str], t1_signature: str) -> List[str]:
    """SHA-256 hash each rotation-quantized string concatenated with the T1 signature.

    Args:
        rotation_values: Space-separated bin-index strings, one per rotation matrix.
        t1_signature: Raw T1 token signature appended to each rotation value before hashing.

    Returns:
        List of SHA-256 hex digest strings, one per rotation value.
    """
    return [hashlib.sha256((rv + t1_signature).encode("utf-8")).hexdigest() for rv in rotation_values]


# Ordered field name mapping for T6 payload
_T6_FIELDS = [
    (PostalCodeAttribute, "PostalCode"),
    (BirthDateAttribute, "Birthdate"),
    (FirstNameAttribute, "GivenName"),
    (LastNameAttribute, "Surname"),
    (SexAttribute, "Gender"),
]

# Pre-built attribute instances for T6 validation and normalization — reused across all calls.
_T6_ATTRIBUTE_INSTANCES = {attr_cls: attr_cls() for attr_cls, _ in _T6_FIELDS}


class OnnxT6SignatureProvider:
    """ONNX-backed implementation of InferenceSignatureProvider for T6 tokens."""

    # Class-level rotation transformer cache so expensive matrix generation
    # (O(N^3) for N=embedding_dim) is paid only once per process lifetime.
    _rotation_transformer: ClassVar[Optional[RotationEmbeddingTransformer]] = None
    _rotation_transformer_lock: ClassVar[Lock] = Lock()

    def get_token_id(self) -> str:
        return "T6"

    def is_enabled(self) -> bool:
        return T6InferenceConfig.is_enabled()

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
                        bin_width=RotationConfig.get_bin_width(),
                        min_val=RotationConfig.get_min_val(),
                        max_val=RotationConfig.get_max_val(),
                    )
        return cls._rotation_transformer

    def generate_signature(self, person_attributes: Dict[Type[Attribute], str]) -> Optional[str]:
        """Generate a single T6 signature via ONNX inference.

        Pipeline: ONNX embed → rotate → quantize → SHA-256 hash with T1 signature.
        Falls back to raw hex embedding string when rotation is disabled.
        """
        result = TokenGeneratorResult()
        payload_json = self.build_t6_payload(person_attributes, result)
        if payload_json is None:
            return None
        try:
            sig, embedding = T6OnnxSignatureGenerator.generate_signature_with_raw_embedding(payload_json)
            if RotationConfig.is_enabled() and embedding is not None:
                transformer = self._get_rotation_transformer(len(embedding))
                if transformer is not None:
                    rotation_values: List[str] = transformer.transform(list(embedding))
                    t1_sig = _compute_t1_signature(person_attributes)
                    if t1_sig:
                        rotation_values = _hash_rotation_values(rotation_values, t1_sig)
                    return ",".join(rotation_values)
            return sig
        except Exception as error:
            logger.error("Error generating T6 signature", exc_info=error)
            return None

    def generate_batch(self, rows: List[Dict[Type[Attribute], str]]) -> InferenceBatchResult:
        """Generate T6 signatures for a batch of records.

        Pipeline per record: ONNX embed → rotate → quantize → SHA-256 hash with T1 signature.
        Falls back to raw hex embedding string when rotation is disabled.
        """
        payloads: List[Optional[str]] = []
        valid_indices: List[int] = []

        for i, row in enumerate(rows):
            result = TokenGeneratorResult()
            payload = self.build_t6_payload(row, result)
            payloads.append(payload)
            if payload is not None:
                valid_indices.append(i)

        valid_payload_list = [payloads[i] for i in valid_indices]

        signatures: List[Optional[str]] = [None] * len(rows)
        raw_embeddings = [None] * len(rows)

        if valid_payload_list:
            batch_sigs, batch_embs = T6OnnxSignatureGenerator.generate_signatures_with_raw_embeddings(
                valid_payload_list
            )

            # Resolve the rotation transformer once for this batch (cached across calls).
            first_emb = next((e for e in batch_embs if e is not None), None)
            transformer: Optional[RotationEmbeddingTransformer] = (
                self._get_rotation_transformer(len(first_emb)) if first_emb is not None else None
            )

            for vi, original_index in enumerate(valid_indices):
                embedding = batch_embs[vi]
                raw_embeddings[original_index] = embedding
                if transformer is not None and embedding is not None:
                    rotation_values: List[str] = transformer.transform(list(embedding))
                    t1_sig = _compute_t1_signature(rows[original_index])
                    if t1_sig:
                        rotation_values = _hash_rotation_values(rotation_values, t1_sig)
                    signatures[original_index] = ",".join(rotation_values)
                else:
                    signatures[original_index] = batch_sigs[vi]

        return InferenceBatchResult(signatures=signatures, raw_embeddings=raw_embeddings)

    def build_t6_payload(
        self,
        person_attributes: Dict[Type[Attribute], str],
        result: TokenGeneratorResult,
    ) -> Optional[str]:
        """Build the deterministic JSON payload for T6 inference.

        Returns None if any required field is missing or fails validation.
        Each of the 5 fields (PostalCode, Birthdate, GivenName, Surname, Gender)
        must be present and non-empty.
        """
        payload: Dict[str, str] = {}
        for attr_cls, field_name in _T6_FIELDS:
            value = person_attributes.get(attr_cls)
            if not value:
                result.invalid_attributes.add(attr_cls.__name__)
                return None
            attr = _T6_ATTRIBUTE_INSTANCES[attr_cls]
            if not attr.validate(value):
                result.invalid_attributes.add(attr_cls.__name__)
                return None
            normalized = attr.normalize(value)
            if not normalized:
                result.invalid_attributes.add(attr_cls.__name__)
                return None
            payload[field_name] = normalized
        return t6_payload_to_json(payload)
