"""ONNX-backed T6 signature provider for OpenToken."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type

from opentoken.attributes.attribute import Attribute
from opentoken.attributes.person.birth_date_attribute import BirthDateAttribute
from opentoken.attributes.person.first_name_attribute import FirstNameAttribute
from opentoken.attributes.person.last_name_attribute import LastNameAttribute
from opentoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from opentoken.attributes.person.sex_attribute import SexAttribute
from opentoken.tokens.inference_signature_provider import InferenceBatchResult, InferenceSignatureProvider
from opentoken.tokens.token_generator_result import TokenGeneratorResult
from opentoken_core_ai.tokens.t6_inference_config import T6InferenceConfig
from opentoken_core_ai.tokens.t6_onnx_signature_generator import T6OnnxSignatureGenerator, t6_payload_to_json

logger = logging.getLogger(__name__)

# Ordered field name mapping for T6 payload
_T6_FIELDS = [
    (PostalCodeAttribute, "PostalCode"),
    (BirthDateAttribute, "Birthdate"),
    (FirstNameAttribute, "GivenName"),
    (LastNameAttribute, "Surname"),
    (SexAttribute, "Gender"),
]


class OnnxT6SignatureProvider:
    """ONNX-backed implementation of InferenceSignatureProvider for T6 tokens."""

    def get_token_id(self) -> str:
        return "T6"

    def is_enabled(self) -> bool:
        return T6InferenceConfig.is_enabled()

    def generate_signature(self, person_attributes: Dict[Type[Attribute], str]) -> Optional[str]:
        """Generate a single T6 signature via ONNX inference."""
        result = TokenGeneratorResult()
        payload_json = self.build_t6_payload(person_attributes, result)
        if payload_json is None:
            return None
        try:
            return T6OnnxSignatureGenerator.generate_signature(payload_json)
        except Exception as error:
            logger.error("Error generating T6 signature", exc_info=error)
            return None

    def generate_batch(self, rows: List[Dict[Type[Attribute], str]]) -> InferenceBatchResult:
        """Generate T6 signatures + raw embeddings for a batch of records."""
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
            for vi, original_index in enumerate(valid_indices):
                signatures[original_index] = batch_sigs[vi]
                raw_embeddings[original_index] = batch_embs[vi]

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
            payload[field_name] = value
        return t6_payload_to_json(payload)
