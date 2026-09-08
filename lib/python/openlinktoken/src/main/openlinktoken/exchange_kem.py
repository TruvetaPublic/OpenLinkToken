# SPDX-License-Identifier: MIT
"""Generic version-2 exchange envelopes backed by ML-KEM and hybrid ECDH."""

from __future__ import annotations

import base64
import json
import os
from typing import Any, Mapping

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from openlinktoken.crypto_suite import CryptoSuite
from openlinktoken.exchange_key_bundle import ExchangeKeyBundle, KeyBundleError

EXCHANGE_V2_VERSION = 2
EXCHANGE_V2_TYPE = "openlinktoken-exchange"
EXCHANGE_V2_CONTENT_TYPE = "application/openlinktoken-exchange+json"
EXCHANGE_V2_ENCRYPTION = "A256GCM"
KDF_ALGORITHM = "HKDF-SHA256"
TRANSPORT_KEY_LENGTH = 32


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: Any, field_name: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be non-empty base64url data.")
    try:
        padding = "=" * (-len(value) % 4)
        return base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except Exception as error:
        raise ValueError(f"{field_name} is not valid base64url data: {error}") from error


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


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
    """Build a generic v2 envelope for pure ML-KEM or hybrid ECDH+ML-KEM."""
    if sender_bundle.suite != recipient_bundle.suite:
        raise ValueError("Sender and recipient key bundles must use the same crypto suite.")
    suite = sender_bundle.suite
    if suite.exchange_config_version != 2:
        raise ValueError(f"Suite '{suite.suite_id}' does not use exchange configuration version 2.")
    if not exchange_name or not exchange_id:
        raise ValueError("Exchange name and exchange ID must be non-empty.")

    protected_header = {
        "typ": EXCHANGE_V2_TYPE,
        "cty": EXCHANGE_V2_CONTENT_TYPE,
        "enc": EXCHANGE_V2_ENCRYPTION,
        "cryptoSuite": suite.suite_id,
        "exchangeId": exchange_id,
    }
    protected = _encode(_canonical_json(protected_header))
    content_key = os.urandom(TRANSPORT_KEY_LENGTH)
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
    outer_iv = os.urandom(12)
    encrypted_payload = AESGCM(content_key).encrypt(outer_iv, _canonical_json(payload), protected.encode("ascii"))
    outer_ciphertext, outer_tag = encrypted_payload[:-16], encrypted_payload[-16:]

    recipients = [
        _build_recipient(sender_bundle, suite, protected, exchange_id, content_key),
        _build_recipient(recipient_bundle, suite, protected, exchange_id, content_key),
    ]
    return {
        "version": EXCHANGE_V2_VERSION,
        "type": EXCHANGE_V2_TYPE,
        "cryptoSuite": suite.suite_id,
        "protected": protected,
        "recipients": recipients,
        "iv": _encode(outer_iv),
        "ciphertext": _encode(outer_ciphertext),
        "tag": _encode(outer_tag),
    }


def decrypt_exchange_envelope_v2(
    exchange_config: Mapping[str, Any],
    private_bundle_value: bytes | str | Mapping[str, Any],
) -> tuple[bytes, bytes]:
    """Decrypt a v2 envelope and return its plaintext plus transport key."""
    if exchange_config.get("version") != EXCHANGE_V2_VERSION:
        raise ValueError("Exchange config is not version 2.")
    suite = CryptoSuite.from_id(exchange_config.get("cryptoSuite"))
    if suite.exchange_config_version != EXCHANGE_V2_VERSION:
        raise ValueError(f"Suite '{suite.suite_id}' is not valid for exchange configuration version 2.")

    private_bundle = (
        private_bundle_value
        if isinstance(private_bundle_value, ExchangeKeyBundle)
        else ExchangeKeyBundle.from_mapping(private_bundle_value, require_private=True)
        if isinstance(private_bundle_value, Mapping)
        else ExchangeKeyBundle.from_json(private_bundle_value, require_private=True)
    )
    if private_bundle.suite != suite:
        raise ValueError("Private key bundle suite does not match the exchange config suite.")

    protected = exchange_config.get("protected")
    protected_bytes = _decode(protected, "protected")
    try:
        protected_header = json.loads(protected_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Protected exchange header is not valid JSON: {error}") from error
    if not isinstance(protected_header, Mapping):
        raise ValueError("Protected exchange header must be a JSON object.")
    if protected_header.get("cryptoSuite") != suite.suite_id:
        raise ValueError("Protected exchange header suite does not match the envelope suite.")
    exchange_id = protected_header.get("exchangeId")
    if not isinstance(exchange_id, str) or not exchange_id:
        raise ValueError("Protected exchange header is missing exchangeId.")

    recipients = exchange_config.get("recipients")
    if not isinstance(recipients, list):
        raise ValueError("Version-2 exchange config is missing recipients.")
    matching = [
        recipient
        for recipient in recipients
        if isinstance(recipient, Mapping) and recipient.get("kid") == private_bundle.kid
    ]
    if len(matching) != 1:
        raise ValueError("No unique recipient entry matches the supplied private key bundle.")
    recipient = matching[0]
    content_key = _unwrap_content_key(recipient, private_bundle, suite, protected, exchange_id)

    outer_iv = _decode(exchange_config.get("iv"), "iv")
    ciphertext = _decode(exchange_config.get("ciphertext"), "ciphertext")
    tag = _decode(exchange_config.get("tag"), "tag")
    try:
        plaintext = AESGCM(content_key).decrypt(
            outer_iv,
            ciphertext + tag,
            protected.encode("ascii"),
        )
    except Exception as error:
        raise ValueError(f"Failed to decrypt version-2 exchange payload: {error}") from error
    return plaintext, content_key


def decrypt_exchange_envelope(
    exchange_config: Mapping[str, Any],
    private_bundle_value: bytes | str | Mapping[str, Any],
) -> bytes:
    """Decrypt a version-2 exchange envelope and return only its plaintext."""
    plaintext, _ = decrypt_exchange_envelope_v2(exchange_config, private_bundle_value)
    return plaintext


def _build_recipient(
    recipient_bundle: ExchangeKeyBundle,
    suite: CryptoSuite,
    protected: str,
    exchange_id: str,
    content_key: bytes,
) -> dict[str, Any]:
    shared_secret_parts: list[bytes] = []
    components: list[dict[str, Any]] = []

    if suite.exchange_key_agreement == "ECDH+ML-KEM-768":
        recipient_public_key = serialization.load_pem_public_key(recipient_bundle.ec_public_pem or b"")
        if not isinstance(recipient_public_key, ec.EllipticCurvePublicKey):
            raise KeyBundleError("Hybrid recipient bundle does not contain an EC public key.")
        ephemeral_private = ec.generate_private_key(ec.SECP256R1())
        ephemeral_public = ephemeral_private.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        shared_secret_parts.append(ephemeral_private.exchange(ec.ECDH(), recipient_public_key))
        components.append(
            {
                "algorithm": "ECDH-P256",
                "payload": {"ephemeralPublicKey": _encode(ephemeral_public), "encoding": "der-spki"},
            }
        )

    try:
        mlkem_public_key = mlkem_public_key_from_bytes(recipient_bundle.mlkem_public_key)
        mlkem_shared_secret, encapsulated_key = mlkem_public_key.encapsulate()
    except Exception as error:
        raise ValueError(f"ML-KEM encapsulation failed: {error}") from error
    shared_secret_parts.append(mlkem_shared_secret)
    components.append(
        {
            "algorithm": "ML-KEM-768",
            "payload": {"encapsulatedKey": _encode(encapsulated_key), "encoding": "raw"},
        }
    )

    salt = exchange_id.encode("utf-8")
    info = f"openlinktoken:exchange:v2:{suite.suite_id}:{recipient_bundle.kid}".encode("utf-8")
    kek = _derive_key(b"".join(shared_secret_parts), salt, info)
    wrapped_iv = os.urandom(12)
    aad = _recipient_aad(protected, recipient_bundle.kid, components)
    wrapped = AESGCM(kek).encrypt(wrapped_iv, content_key, aad)
    return {
        "kid": recipient_bundle.kid,
        "keyManagement": {
            "mode": "hybrid" if suite.exchange_key_agreement == "ECDH+ML-KEM-768" else "kem",
            "components": components,
            "kdf": {
                "algorithm": KDF_ALGORITHM,
                "salt": _encode(salt),
                "info": _encode(info),
            },
            "wrappedContentKey": {
                "algorithm": EXCHANGE_V2_ENCRYPTION,
                "iv": _encode(wrapped_iv),
                "ciphertext": _encode(wrapped[:-16]),
                "tag": _encode(wrapped[-16:]),
            },
        },
    }


def _unwrap_content_key(
    recipient: Mapping[str, Any],
    private_bundle: ExchangeKeyBundle,
    suite: CryptoSuite,
    protected: str,
    exchange_id: str,
) -> bytes:
    key_management = recipient.get("keyManagement")
    if not isinstance(key_management, Mapping):
        raise ValueError("Recipient is missing keyManagement.")
    expected_mode = "hybrid" if suite.exchange_key_agreement == "ECDH+ML-KEM-768" else "kem"
    if key_management.get("mode") != expected_mode:
        raise ValueError("Recipient key-management mode does not match the suite.")
    components = key_management.get("components")
    if not isinstance(components, list):
        raise ValueError("Recipient keyManagement.components must be a list.")
    expected_algorithms = ["ECDH-P256", "ML-KEM-768"] if expected_mode == "hybrid" else ["ML-KEM-768"]
    actual_algorithms = [component.get("algorithm") for component in components if isinstance(component, Mapping)]
    if actual_algorithms != expected_algorithms:
        raise ValueError("Recipient key-management component ordering does not match the suite.")

    shared_secret_parts: list[bytes] = []
    for component in components:
        if not isinstance(component, Mapping) or not isinstance(component.get("payload"), Mapping):
            raise ValueError("Recipient key-management component is malformed.")
        algorithm = component.get("algorithm")
        payload = component["payload"]
        if algorithm == "ECDH-P256":
            if private_bundle.ec_private_pem is None or payload.get("encoding") != "der-spki":
                raise ValueError("Hybrid recipient is missing its EC private key or ephemeral encoding.")
            private_ec = serialization.load_pem_private_key(private_bundle.ec_private_pem, password=None)
            ephemeral_der = _decode(payload.get("ephemeralPublicKey"), "ephemeralPublicKey")
            ephemeral_public = serialization.load_der_public_key(ephemeral_der)
            if not isinstance(private_ec, ec.EllipticCurvePrivateKey) or not isinstance(
                ephemeral_public, ec.EllipticCurvePublicKey
            ):
                raise ValueError("Hybrid ECDH component does not contain P-256 keys.")
            shared_secret_parts.append(private_ec.exchange(ec.ECDH(), ephemeral_public))
        elif algorithm == "ML-KEM-768":
            if private_bundle.mlkem_private_seed is None or payload.get("encoding") != "raw":
                raise ValueError("Recipient is missing its ML-KEM private seed or ciphertext encoding.")
            ciphertext = _decode(payload.get("encapsulatedKey"), "encapsulatedKey")
            try:
                shared_secret_parts.append(
                    mlkem_private_key_from_seed(private_bundle.mlkem_private_seed).decapsulate(ciphertext)
                )
            except Exception as error:
                raise ValueError(f"ML-KEM decapsulation failed: {error}") from error
        else:
            raise ValueError(f"Unsupported recipient component algorithm '{algorithm}'.")

    kdf = key_management.get("kdf")
    wrapped = key_management.get("wrappedContentKey")
    if not isinstance(kdf, Mapping) or not isinstance(wrapped, Mapping):
        raise ValueError("Recipient keyManagement is missing kdf or wrappedContentKey.")
    if kdf.get("algorithm") != KDF_ALGORITHM:
        raise ValueError(f"Unsupported key-management KDF '{kdf.get('algorithm')}'.")
    salt = _decode(kdf.get("salt"), "kdf.salt")
    info = _decode(kdf.get("info"), "kdf.info")
    expected_info = f"openlinktoken:exchange:v2:{suite.suite_id}:{private_bundle.kid}".encode("utf-8")
    if salt != exchange_id.encode("utf-8") or info != expected_info:
        raise ValueError("Recipient KDF transcript does not match the protected exchange context.")
    kek = _derive_key(b"".join(shared_secret_parts), salt, info)
    if wrapped.get("algorithm") != EXCHANGE_V2_ENCRYPTION:
        raise ValueError(f"Unsupported wrapped content-key algorithm '{wrapped.get('algorithm')}'.")
    wrapped_iv = _decode(wrapped.get("iv"), "wrappedContentKey.iv")
    wrapped_ciphertext = _decode(wrapped.get("ciphertext"), "wrappedContentKey.ciphertext")
    wrapped_tag = _decode(wrapped.get("tag"), "wrappedContentKey.tag")
    try:
        return AESGCM(kek).decrypt(
            wrapped_iv,
            wrapped_ciphertext + wrapped_tag,
            _recipient_aad(protected, private_bundle.kid, components),
        )
    except Exception as error:
        raise ValueError(f"Failed to unwrap the exchange content key: {error}") from error


def mlkem_public_key_from_bytes(value: bytes | None):
    """Load a raw ML-KEM-768 public key using the configured provider."""
    if value is None:
        raise ValueError("ML-KEM public key is missing.")
    from cryptography.hazmat.primitives.asymmetric import mlkem

    return mlkem.MLKEM768PublicKey.from_public_bytes(value)


def mlkem_private_key_from_seed(value: bytes):
    """Load an ML-KEM-768 private key from its raw 64-byte seed."""
    from cryptography.hazmat.primitives.asymmetric import mlkem

    return mlkem.MLKEM768PrivateKey.from_seed_bytes(value)


def _derive_key(shared_secret: bytes, salt: bytes, info: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=TRANSPORT_KEY_LENGTH, salt=salt, info=info).derive(shared_secret)


def _recipient_aad(protected: str, kid: str, components: list[Mapping[str, Any]]) -> bytes:
    return _canonical_json(
        {
            "protected": protected,
            "kid": kid,
            "components": components,
        }
    )
