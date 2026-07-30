# SPDX-License-Identifier: MIT

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, runtime_checkable


@dataclass
class InferenceBatchResult:
    """Results of a batched inference pass.

    Attributes:
        signatures: Hex-encoded token signatures in the same order as the input rows.
    """

    signatures: List[str] = field(default_factory=list)


@runtime_checkable
class InferenceSignatureProvider(Protocol):
    """Protocol for inference-based token signature generation.

    Implementations are discovered at runtime via
    ``importlib.metadata.entry_points(group="openlinktoken.inference_providers")``.
    When no implementation is installed, inference-based tokens are silently
    disabled and only standard attribute-expression tokens (T1–T5) are generated.

    Each provider is responsible for one token identifier (e.g. ``"ML1"``) and
    reports it via :meth:`get_token_id`.
    """

    def get_token_id(self) -> str:
        """Return the token identifier this provider handles (e.g. ``"ML1"``)."""
        ...

    def is_enabled(self) -> bool:
        """Return whether this provider is currently enabled and configured."""
        ...

    def generate_signature(self, person_attributes: Dict[str, str]) -> Optional[str]:
        """Generate a single inference-based token signature.

        Args:
            person_attributes: Field-ID map for one record.

        Returns:
            Hex-encoded signature string, or ``None`` if the record is invalid.
        """
        ...

    def generate_batch(self, rows: List[Dict[str, str]]) -> InferenceBatchResult:
        """Generate inference-based signatures for a batch of records in one pass.

        Args:
            rows: List of field-ID maps, one per record.

        Returns:
            :class:`InferenceBatchResult` with signatures in input row order.
        """
        ...
