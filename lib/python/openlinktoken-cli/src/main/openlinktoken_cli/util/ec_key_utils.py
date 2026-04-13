"""
Copyright (c) Truveta. All rights reserved.

Backwards-compatible re-exports for shared EC key helpers.
"""

from openlinktoken.ec_key_utils import (
    SUPPORTED_CURVES,
    derive_public_key_from_private_pem,
    ensure_directory,
    fingerprint_to_kid,
    generate_key_pair,
    get_curve_class,
    public_key_fingerprint,
    resolve_key_name,
    write_key,
)

__all__ = [
    "SUPPORTED_CURVES",
    "derive_public_key_from_private_pem",
    "ensure_directory",
    "fingerprint_to_kid",
    "generate_key_pair",
    "get_curve_class",
    "public_key_fingerprint",
    "resolve_key_name",
    "write_key",
]
