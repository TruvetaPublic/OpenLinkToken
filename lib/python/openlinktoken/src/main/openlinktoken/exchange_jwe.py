# SPDX-License-Identifier: MIT
"""
Shared helpers for building and decrypting exchange-config JWE envelopes.

Note: The exchange-config workflow is Python-CLI only. The Java counterpart
(``ExchangeJwe.java``) is a placeholder stub that references this module.
"""

import base64
import json
from pathlib import Path
from typing import Any, Mapping

from jwcrypto import jwe, jwk

from openlinktoken.ec_key_utils import fingerprint_to_kid, public_key_fingerprint

EXCHANGE_JWE_VERSION = 1
EXCHANGE_JWE_TYPE = "openlinktoken-exchange+jwe"
EXCHANGE_JWE_CONTENT_TYPE = "application/openlinktoken-exchange+json"
EXCHANGE_JWE_ENCRYPTION = "A256GCM"
EXCHANGE_JWE_RECIPIENT_ALGORITHM = "ECDH-ES+A256KW"


def build_exchange_envelope(
    exchange_name: str,
    hashing_secret: bytes,
    sender_public_pem: bytes,
    recipient_public_pem: bytes,
    curve: str,
    created_at: str,
    exchange_id: str,
) -> dict[str, Any]:
    """Build a multi-recipient JWE exchange envelope."""
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
    }
    protected_header = {
        "typ": EXCHANGE_JWE_TYPE,
        "cty": EXCHANGE_JWE_CONTENT_TYPE,
        "enc": EXCHANGE_JWE_ENCRYPTION,
    }

    envelope = jwe.JWE(
        json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        protected=json.dumps(protected_header, separators=(",", ":")),
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
    """Decrypt an exchange JWE envelope with a matching private key PEM."""
    envelope = jwe.JWE()
    envelope.deserialize(json.dumps(dict(exchange_config)))
    envelope.decrypt(jwk.JWK.from_pem(private_pem))
    return bytes(envelope.payload)


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


def _recipient_header(public_pem: bytes) -> dict[str, str]:
    """Build the per-recipient JOSE header for the provided public key."""
    return {
        "alg": EXCHANGE_JWE_RECIPIENT_ALGORITHM,
        "kid": fingerprint_to_kid(public_key_fingerprint(public_pem)),
    }
