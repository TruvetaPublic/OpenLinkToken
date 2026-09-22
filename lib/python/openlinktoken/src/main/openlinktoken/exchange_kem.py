# SPDX-License-Identifier: MIT
"""Version-2 exchange facade backed by standard JWE JSON Serialization."""

from __future__ import annotations

import base64
import json
from typing import Any, Mapping

from openlinktoken.crypto_suite import CryptoSuite
from openlinktoken.exchange_key_bundle import ExchangeKeyBundle
from openlinktoken.jwe_mlkem import (
    EXCHANGE_V2_CONTENT_TYPE,
    EXCHANGE_V2_ENCRYPTION,
    EXCHANGE_V2_TYPE,
    EXCHANGE_V2_VERSION,
    build_v2_jwe,
    decrypt_v2_jwe,
)


def build_exchange_envelope_v2(
    exchange_name: str,
    hashing_secret: bytes,
    sender_bundle: ExchangeKeyBundle,
    recipient_bundle: ExchangeKeyBundle,
    created_at: str,
    exchange_id: str,
    rotation_iv: bytes = b"",
    rotation_count: int = 0,
    bin_width: float = 0.05,
    dimension_bias: list[float] | None = None,
) -> dict[str, Any]:
    """Build a version-2 exchange config as a standard general JWE JSON object."""
    if sender_bundle.suite != recipient_bundle.suite:
        raise ValueError("Sender and recipient key bundles must use the same crypto suite.")
    suite = sender_bundle.suite
    if suite.exchange_config_version != EXCHANGE_V2_VERSION:
        raise ValueError(f"Suite '{suite.suite_id}' does not use exchange configuration version 2.")
    if not exchange_name or not exchange_id:
        raise ValueError("Exchange name and exchange ID must be non-empty.")
    if not isinstance(hashing_secret, bytes):
        raise TypeError("Hashing secret must be bytes.")
    if not isinstance(rotation_iv, bytes):
        raise TypeError("Rotation IV must be bytes.")
    if rotation_count < 0:
        raise ValueError("Rotation count must be non-negative.")
    if bin_width <= 0:
        raise ValueError("Bin width must be positive.")

    protected_header = {
        "typ": EXCHANGE_V2_TYPE,
        "cty": EXCHANGE_V2_CONTENT_TYPE,
        "enc": EXCHANGE_V2_ENCRYPTION,
        "version": EXCHANGE_V2_VERSION,
        "cryptoSuite": suite.suite_id,
        "exchangeId": exchange_id,
    }
    payload = {
        "exchangeName": exchange_name,
        "cryptoSuite": suite.suite_id,
        "hashingSecret": _encode(hashing_secret),
        "hashingSecretEncoding": "base64url",
        "senderKeyId": sender_bundle.kid,
        "recipientKeyId": recipient_bundle.kid,
        "senderKeyBundle": sender_bundle.to_mapping(),
        "recipientKeyBundle": recipient_bundle.to_mapping(),
        "createdAt": created_at,
        "exchangeId": exchange_id,
        "rotationIv": _encode(rotation_iv),
        "rotationIvEncoding": "base64url",
        "rotationCount": rotation_count,
        "binWidth": bin_width,
        "dimensionBias": dimension_bias if dimension_bias is not None else [],
    }
    return build_v2_jwe(
        _canonical_json(payload),
        protected_header,
        [sender_bundle, recipient_bundle],
    )


def decrypt_exchange_envelope_v2(
    exchange_config: Mapping[str, Any],
    private_bundle_value: bytes | str | Mapping[str, Any] | ExchangeKeyBundle,
) -> tuple[bytes, bytes]:
    """Decrypt a standard version-2 exchange config and return plaintext plus transport key."""
    private_bundle = _parse_private_bundle(private_bundle_value)
    plaintext, transport_key = decrypt_v2_jwe(exchange_config, private_bundle)
    protected_header = _decode_protected_header(exchange_config.get("protected"))
    suite = CryptoSuite.from_id(protected_header["cryptoSuite"])
    payload = _parse_payload(plaintext)
    _validate_payload(payload, suite, protected_header)
    return plaintext, transport_key


def decrypt_exchange_envelope(
    exchange_config: Mapping[str, Any],
    private_bundle_value: bytes | str | Mapping[str, Any] | ExchangeKeyBundle,
) -> bytes:
    """Decrypt a version-2 exchange config and return only its plaintext."""
    plaintext, _ = decrypt_exchange_envelope_v2(exchange_config, private_bundle_value)
    return plaintext


def _parse_private_bundle(
    value: bytes | str | Mapping[str, Any] | ExchangeKeyBundle,
) -> ExchangeKeyBundle:
    """Parse and validate private version-2 key material."""
    if isinstance(value, ExchangeKeyBundle):
        bundle = value
    elif isinstance(value, Mapping):
        bundle = ExchangeKeyBundle.from_mapping(value, require_private=True)
    else:
        bundle = ExchangeKeyBundle.from_json(value, require_private=True)
    return bundle


def _parse_payload(value: bytes) -> dict[str, Any]:
    """Parse the decrypted exchange payload as a JSON object."""
    try:
        payload = json.loads(value)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Version-2 exchange payload is not valid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("Version-2 exchange payload must be a JSON object.")
    return payload


def _validate_payload(
    payload: Mapping[str, Any],
    suite: CryptoSuite,
    protected_header: Mapping[str, Any],
) -> None:
    """Validate payload identity fields against the authenticated protected header."""
    if payload.get("cryptoSuite") != suite.suite_id:
        raise ValueError("Version-2 exchange payload suite does not match the protected header.")
    if payload.get("exchangeId") != protected_header.get("exchangeId"):
        raise ValueError("Version-2 exchange payload exchangeId does not match the protected header.")

    for field_name in ("senderKeyId", "recipientKeyId"):
        if not isinstance(payload.get(field_name), str) or not payload[field_name]:
            raise ValueError(f"Version-2 exchange payload is missing {field_name}.")

    for field_name, expected_kid in (
        ("senderKeyBundle", payload["senderKeyId"]),
        ("recipientKeyBundle", payload["recipientKeyId"]),
    ):
        bundle_value = payload.get(field_name)
        if not isinstance(bundle_value, Mapping):
            raise ValueError(f"Version-2 exchange payload is missing {field_name}.")
        bundle = ExchangeKeyBundle.from_mapping(bundle_value)
        if bundle.suite != suite or bundle.kid != expected_kid:
            raise ValueError(f"Version-2 exchange payload {field_name} does not match its key ID or suite.")


def _decode_protected_header(value: Any) -> dict[str, Any]:
    """Decode the protected header needed for payload consistency validation."""
    protected_bytes = _decode(value, "protected")
    try:
        header = json.loads(protected_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Protected version-2 exchange header is not valid JSON: {error}") from error
    if not isinstance(header, dict):
        raise ValueError("Protected version-2 exchange header must be a JSON object.")
    return header


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    """Serialize a mapping deterministically for the JWE plaintext."""
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _encode(value: bytes) -> str:
    """Encode bytes as unpadded base64url text."""
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: Any, field_name: str) -> bytes:
    """Decode a required base64url field."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be non-empty base64url data.")
    try:
        padding = "=" * (-len(value) % 4)
        return base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError) as error:
        raise ValueError(f"{field_name} is not valid base64url data: {error}") from error
