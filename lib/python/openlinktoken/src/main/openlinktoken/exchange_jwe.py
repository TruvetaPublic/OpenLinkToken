# SPDX-License-Identifier: MIT
"""Shared helpers for building and decrypting exchange-config JWE envelopes.

The envelope helpers are shared-library functionality. CLI-only path,
environment, and file-permission policies remain in the Python CLI layer.
"""

import base64
import json
from pathlib import Path
from typing import Any, Mapping

from jwcrypto import jwe, jwk
from jwcrypto.common import JWSEHeaderParameter

from openlinktoken.crypto.crypto_suite import CryptoSuite
from openlinktoken.ec_key_utils import fingerprint_to_kid, public_key_fingerprint

EXCHANGE_JWE_VERSION = 1
EXCHANGE_JWE_TYPE = "openlinktoken-exchange+jwe"
EXCHANGE_JWE_CONTENT_TYPE = "application/openlinktoken-exchange+json"
EXCHANGE_JWE_ENCRYPTION = CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM
EXCHANGE_JWE_RECIPIENT_ALGORITHM = "ECDH-ES+A256KW"
_HEADER_REGISTRY = {
    "cryptoSuite": JWSEHeaderParameter("Open Link Token crypto suite", True, True, None),
}


def build_exchange_envelope(
    exchange_name: str,
    hashing_secret: bytes,
    sender_public_pem: bytes,
    recipient_public_pem: bytes,
    curve: str,
    created_at: str,
    exchange_id: str,
    rotation_iv: bytes = b"",
    rotation_count: int = 0,
    bin_width: float = 0.05,
    dimension_bias: list[float] | None = None,
    crypto_suite: CryptoSuite | None = None,
) -> dict[str, Any]:
    """Build a multi-recipient JWE exchange envelope.

    Args:
        exchange_name: Human-readable name for the exchange.
        hashing_secret: Secret bytes used to derive token hashes.
        sender_public_pem: Sender's public EC key in PEM format.
        recipient_public_pem: Recipient's public EC key in PEM format.
        curve: Open Link Token curve name shared by both public keys.
        created_at: Exchange creation timestamp.
        exchange_id: Stable identifier for this exchange.
        rotation_iv: Optional rotation-matrix initialization vector.
        rotation_count: Optional number of rotation matrices.
        bin_width: Optional rotation quantization bin width.
        dimension_bias: Optional rotation dimension-bias values.
        crypto_suite: Optional registered v1 ECDH suite; defaults to the default suite.

    Returns:
        A serialized general-JSON JWE exchange envelope.
    """
    selected_suite = crypto_suite or CryptoSuite.default()
    registered_suite = CryptoSuite.from_id(selected_suite.suite_id)
    if registered_suite != selected_suite:
        raise ValueError(f"Crypto suite '{selected_suite.suite_id}' does not match its registered definition.")
    selected_suite = registered_suite
    if (
        selected_suite.exchange_config_version != EXCHANGE_JWE_VERSION
        or selected_suite.exchange_key_agreement != CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH
    ):
        raise ValueError(
            f"Version 1 exchange envelopes require a registered v1 ECDH suite; "
            f"suite '{selected_suite.suite_id}' cannot be encoded."
        )
    selected_suite.validate_hashing_secret(hashing_secret)
    payload = {
        "exchangeName": exchange_name,
        "hashingSecret": _base64url_encode(hashing_secret),
        "hashingSecretEncoding": "base64url",
        "senderKeyFingerprint": public_key_fingerprint(sender_public_pem),
        "recipientKeyFingerprint": public_key_fingerprint(recipient_public_pem),
        "senderPublicKey": sender_public_pem.decode("utf-8"),
        "recipientPublicKey": recipient_public_pem.decode("utf-8"),
        "curve": curve,
        "createdAt": created_at,
        "exchangeId": exchange_id,
        "rotationIv": _base64url_encode(rotation_iv),
        "rotationIvEncoding": "base64url",
        "rotationCount": rotation_count,
        "binWidth": bin_width,
        "dimensionBias": dimension_bias if dimension_bias is not None else [],
    }
    protected_header = {
        "typ": EXCHANGE_JWE_TYPE,
        "cty": EXCHANGE_JWE_CONTENT_TYPE,
        "enc": EXCHANGE_JWE_ENCRYPTION,
    }
    if selected_suite != CryptoSuite.default():
        protected_header["cryptoSuite"] = selected_suite.suite_id
        protected_header["crit"] = ["cryptoSuite"]

    envelope = jwe.JWE(
        json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        protected=json.dumps(protected_header, separators=(",", ":")),
        header_registry=_HEADER_REGISTRY,
    )
    envelope.add_recipient(
        jwk.JWK.from_pem(sender_public_pem),
        header=json.dumps(_recipient_header(sender_public_pem), separators=(",", ":")),
    )
    envelope.add_recipient(
        jwk.JWK.from_pem(recipient_public_pem),
        header=json.dumps(_recipient_header(recipient_public_pem), separators=(",", ":")),
    )

    serialized = json.loads(envelope.serialize(compact=False))
    serialized["version"] = EXCHANGE_JWE_VERSION
    return serialized


def decrypt_exchange_envelope(exchange_config: Mapping[str, Any], private_pem: bytes) -> bytes:
    """Decrypt an exchange JWE envelope with a matching private key PEM.

    Args:
        exchange_config: General-JSON JWE exchange envelope.
        private_pem: Matching recipient private key in PEM format.

    Returns:
        Decrypted UTF-8 JSON payload bytes.
    """
    envelope = jwe.JWE(header_registry=_HEADER_REGISTRY)
    envelope.deserialize(json.dumps(dict(exchange_config)))
    envelope.decrypt(jwk.JWK.from_pem(private_pem))
    resolve_v1_exchange_crypto_suite(exchange_config)
    return bytes(envelope.payload)


def resolve_v1_exchange_crypto_suite(exchange_config: Mapping[str, Any]) -> CryptoSuite:
    """Resolve a v1 suite from its authenticated critical protected-header marker.

    Args:
        exchange_config: General-JSON v1 JWE exchange envelope.

    Returns:
        The registered version-one ECDH crypto suite selected by the envelope.
    """
    protected_header = _decode_protected_header(exchange_config.get("protected"))
    if _has_unprotected_suite_marker(exchange_config):
        raise ValueError("Version 1 cryptoSuite must appear only in the protected header.")

    critical_headers = protected_header.get("crit", [])
    if not isinstance(critical_headers, list) or any(not isinstance(value, str) for value in critical_headers):
        raise ValueError("Version 1 protected-header crit must be an array of strings.")
    if any(value != "cryptoSuite" for value in critical_headers):
        raise ValueError("Version 1 protected header contains an unsupported critical parameter.")

    if "cryptoSuite" not in protected_header:
        if "cryptoSuite" in critical_headers:
            raise ValueError("Version 1 protected header marks missing cryptoSuite as critical.")
        return CryptoSuite.default()
    if "cryptoSuite" not in critical_headers:
        raise ValueError("Version 1 cryptoSuite must be listed in the protected crit header.")

    suite_id = protected_header.get("cryptoSuite", CryptoSuite.default().suite_id)
    if not isinstance(suite_id, str) or not suite_id.strip():
        raise ValueError("Version 1 protected-header cryptoSuite must be a non-empty string.")

    suite = CryptoSuite.from_id(suite_id)
    if (
        suite.exchange_config_version != EXCHANGE_JWE_VERSION
        or suite.exchange_key_agreement != CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH
    ):
        raise ValueError(f"Crypto suite '{suite.suite_id}' is incompatible with version 1 ECDH exchange.")
    return suite


def resolve_private_key_by_kid(openlinktoken_dir: Path, kid: str) -> bytes:
    """Resolve a private key by matching a fingerprint-derived recipient ``kid``."""
    for public_key_path in sorted(openlinktoken_dir.glob("*.public.pem")):
        public_pem = public_key_path.read_bytes()
        if fingerprint_to_kid(public_key_fingerprint(public_pem)) != kid:
            continue

        basename = public_key_path.name[: -len(".public.pem")]
        private_key_path = public_key_path.with_name(f"{basename}.private.pem")
        if not private_key_path.exists():
            raise FileNotFoundError(
                f"Resolved recipient kid '{kid}' to {public_key_path}, but {private_key_path} does not exist."
            )
        return private_key_path.read_bytes()

    raise FileNotFoundError(f"No private key found for recipient kid '{kid}' in {openlinktoken_dir}.")


def _base64url_encode(value: bytes) -> str:
    """Encode bytes as unpadded base64url text."""
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _decode_protected_header(value: Any) -> dict[str, Any]:
    """Decode a JWE protected header from unpadded base64url JSON.

    Args:
        value: Unpadded base64url text containing a JSON protected header.

    Returns:
        The decoded protected-header mapping.
    """
    if not isinstance(value, str) or not value:
        raise ValueError("Exchange config is missing its protected header.")

    try:
        padding = "=" * (-len(value) % 4)
        protected_bytes = base64.b64decode(value + padding, altchars=b"-_", validate=True)
        header = json.loads(protected_bytes)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Exchange config protected header is not valid base64url JSON: {error}") from error

    if not isinstance(header, dict):
        raise ValueError("Exchange config protected header must be a JSON object.")
    return header


def _has_unprotected_suite_marker(exchange_config: Mapping[str, Any]) -> bool:
    """Check whether a suite marker appears in an unprotected header.

    Args:
        exchange_config: General-JSON JWE exchange envelope.

    Returns:
        ``True`` if an unprotected header contains ``cryptoSuite``; otherwise ``False``.
    """
    for header_name in ("unprotected", "header"):
        header = exchange_config.get(header_name)
        if isinstance(header, Mapping) and "cryptoSuite" in header:
            return True

    recipients = exchange_config.get("recipients")
    if isinstance(recipients, list):
        for recipient in recipients:
            if isinstance(recipient, Mapping):
                header = recipient.get("header")
                if isinstance(header, Mapping) and "cryptoSuite" in header:
                    return True
    return False


def _recipient_header(public_pem: bytes) -> dict[str, str]:
    """Build the per-recipient JOSE header for the provided public key."""
    return {
        "alg": EXCHANGE_JWE_RECIPIENT_ALGORITHM,
        "kid": fingerprint_to_kid(public_key_fingerprint(public_pem)),
    }
