"""
Copyright (c) Truveta. All rights reserved.

Shared helpers for loading and consuming initiate-exchange config files.
"""

import base64
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from opentoken_cli.util.ec_key_utils import derive_public_key_from_private_pem, public_key_fingerprint
from opentoken_cli.util.exchange_jwe import decrypt_exchange_envelope, resolve_private_key_by_kid
from opentoken_cli.util.stdin_utils import read_required_env_bytes

SUPPORTED_EXCHANGE_CONFIG_VERSIONS = {1, 2}
TRANSPORT_KEY_INFO = b"opentoken:token-encryption:v1"


@dataclass(frozen=True)
class ResolvedExchangeConfig:
    """Resolved exchange-config inputs for consumer commands."""

    path: Path
    version: int
    config: Mapping[str, Any]
    payload: Mapping[str, Any]
    private_key_pem: bytes
    private_key_role: str
    hashing_secret: bytes


def default_exchange_config_path() -> Path:
    """Return the default date-based exchange-config path."""
    return Path(f"./opentoken-{date.today().isoformat()}.exchange.json")


def resolve_exchange_config(
    exchange_config_path: str | None,
    private_key_path: str | None = None,
    private_key_env: str | None = None,
) -> ResolvedExchangeConfig:
    """Load, validate, and decrypt an exchange config plus its hashing secret."""
    config_path = Path(exchange_config_path) if exchange_config_path else default_exchange_config_path()
    if not config_path.exists():
        raise FileNotFoundError(
            f"Exchange config '{config_path}' was not found. "
            "Provide --exchange-config or run 'opentoken initiate-exchange' to create it."
        )
    if not config_path.is_file():
        raise OSError(f"Exchange config path '{config_path}' is not a readable file.")

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Exchange config '{config_path}' is not valid JSON: {error}") from error

    version = config.get("version")
    if version not in SUPPORTED_EXCHANGE_CONFIG_VERSIONS:
        raise ValueError(
            f"Unsupported exchange config version '{version}'. "
            f"Supported versions: {', '.join(str(item) for item in sorted(SUPPORTED_EXCHANGE_CONFIG_VERSIONS))}."
        )

    private_pem = _resolve_private_key(config, private_key_path=private_key_path, private_key_env=private_key_env)
    try:
        payload = json.loads(decrypt_exchange_envelope(config, private_pem))
    except Exception as error:
        raise ValueError(f"Failed to decrypt exchange config '{config_path}': {error}") from error

    if not isinstance(payload, dict):
        raise ValueError(f"Exchange config '{config_path}' decrypted to an invalid payload.")

    return ResolvedExchangeConfig(
        path=config_path,
        version=version,
        config=config,
        payload=payload,
        private_key_pem=private_pem,
        private_key_role=_resolve_private_key_role(private_pem, payload),
        hashing_secret=_decode_hashing_secret(payload),
    )


def derive_transport_encryption_key(exchange: ResolvedExchangeConfig) -> bytes:
    """Derive the shared 32-byte transport key defined by the exchange config contract."""
    sender_public_key = exchange.payload.get("senderPublicKey")
    recipient_public_key = exchange.payload.get("recipientPublicKey")
    exchange_id = exchange.payload.get("exchangeId")
    if exchange.version < 2 or not sender_public_key or not recipient_public_key:
        raise ValueError(
            "This exchange config does not include the public keys required for token encryption/decryption. "
            "Regenerate it with 'opentoken initiate-exchange'."
        )
    if not exchange_id:
        raise ValueError("Exchange config payload is missing exchangeId required for key derivation.")

    other_public_key_pem = recipient_public_key if exchange.private_key_role == "sender" else sender_public_key

    try:
        private_key = serialization.load_pem_private_key(exchange.private_key_pem, password=None)
        public_key = serialization.load_pem_public_key(other_public_key_pem.encode("utf-8"))
        shared_secret = private_key.exchange(ec.ECDH(), public_key)
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=exchange_id.encode("utf-8"),
            info=TRANSPORT_KEY_INFO,
        ).derive(shared_secret)
    except Exception as error:
        raise ValueError(f"Failed to derive the transport encryption key: {error}") from error


def _resolve_private_key(
    exchange_config: Mapping[str, Any],
    private_key_path: str | None,
    private_key_env: str | None,
) -> bytes:
    if private_key_path and private_key_env:
        raise ValueError("Cannot combine --private-key and --private-key-env.")

    if private_key_path:
        path = Path(private_key_path)
        if not path.exists():
            raise FileNotFoundError(f"Private key file not found: {path}")
        return path.read_bytes()

    if private_key_env:
        return read_required_env_bytes("--private-key-env", private_key_env, "private key")

    opentoken_dir = Path.home() / ".opentoken"
    for kid in _recipient_kids(exchange_config):
        try:
            return resolve_private_key_by_kid(opentoken_dir, kid)
        except FileNotFoundError:
            continue

    raise FileNotFoundError(
        f"No private key matching this exchange config was found in {opentoken_dir}. "
        "Provide --private-key or --private-key-env."
    )


def _recipient_kids(exchange_config: Mapping[str, Any]) -> list[str]:
    recipients = exchange_config.get("recipients")
    if not isinstance(recipients, list) or not recipients:
        raise ValueError("Exchange config is missing recipient entries needed for private-key resolution.")

    kids: list[str] = []
    for recipient in recipients:
        if not isinstance(recipient, dict):
            continue
        header = recipient.get("header")
        if isinstance(header, dict) and header.get("kid"):
            kids.append(header["kid"])
    if not kids:
        raise ValueError("Exchange config recipients do not include key identifiers for private-key resolution.")
    return kids


def _resolve_private_key_role(private_pem: bytes, payload: Mapping[str, Any]) -> str:
    public_pem, _ = derive_public_key_from_private_pem(private_pem)
    fingerprint = public_key_fingerprint(public_pem)
    if fingerprint == payload.get("senderKeyFingerprint"):
        return "sender"
    if fingerprint == payload.get("recipientKeyFingerprint"):
        return "recipient"
    raise ValueError("Resolved private key does not match the sender or recipient fingerprint in the exchange config.")


def _decode_hashing_secret(payload: Mapping[str, Any]) -> bytes:
    encoding = payload.get("hashingSecretEncoding")
    value = payload.get("hashingSecret")
    if encoding != "base64url":
        raise ValueError(f"Unsupported hashingSecretEncoding '{encoding}'.")
    if not isinstance(value, str) or not value:
        raise ValueError("Exchange config payload is missing hashingSecret.")

    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except Exception as error:
        raise ValueError(f"hashingSecret is not valid base64url data: {error}") from error
