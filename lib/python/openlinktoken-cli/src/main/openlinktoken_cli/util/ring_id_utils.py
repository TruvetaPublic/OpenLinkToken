"""Utility for generating fallback ring identifiers."""

import uuid
from typing import Optional


def resolve_ring_id(ring_id: Optional[str]) -> str:
    """Return *ring_id* as a stripped string, or a freshly generated UUID if it is None/blank."""
    return str(ring_id).strip() if ring_id and str(ring_id).strip() else str(uuid.uuid4())
