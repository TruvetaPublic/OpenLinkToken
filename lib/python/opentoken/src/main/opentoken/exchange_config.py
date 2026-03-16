"""
Copyright (c) Truveta. All rights reserved.

Shared helpers for loading and consuming initiate-exchange config files.

Note: The exchange-config workflow is Python-CLI only. The Java counterpart
(``ExchangeConfig.java``) is a placeholder stub that references this module.
"""

import base64
import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from opentoken.ec_key_utils import derive_public_key_from_private_pem, public_key_fingerprint
from opentoken.exchange_jwe import decrypt_exchange_envelope, resolve_private_key_by_kid

SUPPORTED_EXCHANGE_CONFIG_VERSIONS = {1}
TRANSPORT_KEY_INFO = b"opentoken:token-encryption:v1"


@dataclass(frozen=True)
class LoadedExchangeConfig:
    """Validated exchange-config envelope loaded from disk."""

    path: Path
    version: int
    config: Mapping[str, Any]


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


def load_exchange_config(
    exchange_config_path: str | Path | None = None,
    exchange_config_value: str | bytes | Mapping[str, Any] | None = None,
) -> LoadedExchangeConfig:
    """Load and validate an exchange-config envelope from disk or an in-memory value."""
    if exchange_config_path and exchange_config_value is not None:
        raise ValueError("Cannot combine an exchange config path and a direct exchange config value.")

    if exchange_config_value is not None:
        config_path = Path("<provided exchange config>")
        config = _parse_exchange_config_value(exchange_config_value)
    else:
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
        supported_versions = ", ".join(str(item) for item in sorted(SUPPORTED_EXCHANGE_CONFIG_VERSIONS))
        raise ValueError(f"Unsupported exchange config version '{version}'. Supported versions: {supported_versions}.")

    return LoadedExchangeConfig(path=config_path, version=version, config=config)


def resolve_exchange_config(
    exchange_config_path: str | Path | None,
    private_key_pem: bytes,
) -> ResolvedExchangeConfig:
    """Load, validate, and decrypt an exchange config using the provided private key PEM."""
    return resolve_loaded_exchange_config(load_exchange_config(exchange_config_path), private_key_pem)


def resolve_exchange_config_inputs(
    exchange_config_path: str | Path | None = None,
    private_key_path: str | Path | None = None,
    private_key_env: str | None = None,
    exchange_config_value: str | bytes | Mapping[str, Any] | None = None,
    private_key_value: str | bytes | None = None,
) -> ResolvedExchangeConfig:
    """Resolve exchange-config inputs into decrypted exchange state."""
    loaded_exchange = load_exchange_config(
        exchange_config_path=exchange_config_path,
        exchange_config_value=exchange_config_value,
    )
    private_key_pem = resolve_exchange_config_private_key(
        loaded_exchange,
        private_key_path=private_key_path,
        private_key_env=private_key_env,
        private_key_value=private_key_value,
    )
    return resolve_loaded_exchange_config(loaded_exchange, private_key_pem)


def resolve_exchange_config_private_key(
    exchange_config: LoadedExchangeConfig,
    private_key_path: str | Path | None = None,
    private_key_env: str | None = None,
    private_key_value: str | bytes | None = None,
    opentoken_dir: Path | None = None,
    environment: Mapping[str, str] | None = None,
) -> bytes:
    """Resolve private-key PEM bytes for a loaded exchange config."""
    provided_private_key_inputs = [
        private_key_path is not None,
        private_key_env is not None,
        private_key_value is not None,
    ]
    if sum(provided_private_key_inputs) > 1:
        raise ValueError("Cannot combine private key path, environment variable, and direct private key value inputs.")

    if private_key_path:
        return _read_private_key_path(private_key_path)

    if private_key_env:
        return _read_private_key_env(private_key_env, environment=environment)

    if private_key_value is not None:
        return _read_private_key_value(private_key_value)

    resolved_opentoken_dir = opentoken_dir if opentoken_dir else Path.home() / ".opentoken"
    for kid in _recipient_kids(exchange_config.config):
        try:
            return resolve_private_key_by_kid(resolved_opentoken_dir, kid)
        except FileNotFoundError:
            continue

    raise FileNotFoundError(
        f"No private key matching this exchange config was found in {resolved_opentoken_dir}. "
        "Provide a private key path, environment variable, or direct value."
    )


def resolve_loaded_exchange_config(
    exchange_config: LoadedExchangeConfig, private_key_pem: bytes
) -> ResolvedExchangeConfig:
    """Decrypt a validated exchange-config envelope using the provided private key PEM."""
    try:
        payload = json.loads(decrypt_exchange_envelope(exchange_config.config, private_key_pem))
    except Exception as error:
        raise ValueError(f"Failed to decrypt exchange config '{exchange_config.path}': {error}") from error

    if not isinstance(payload, dict):
        raise ValueError(f"Exchange config '{exchange_config.path}' decrypted to an invalid payload.")

    return ResolvedExchangeConfig(
        path=exchange_config.path,
        version=exchange_config.version,
        config=exchange_config.config,
        payload=payload,
        private_key_pem=private_key_pem,
        private_key_role=_resolve_private_key_role(private_key_pem, payload),
        hashing_secret=_decode_hashing_secret(payload),
    )


def derive_transport_encryption_key(exchange: ResolvedExchangeConfig) -> bytes:
    """Derive the shared 32-byte transport key defined by the exchange config contract."""
    sender_public_key = exchange.payload.get("senderPublicKey")
    recipient_public_key = exchange.payload.get("recipientPublicKey")
    exchange_id = exchange.payload.get("exchangeId")
    if not sender_public_key or not recipient_public_key:
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


def _read_private_key_path(private_key_path: str | Path) -> bytes:
    """Read private-key PEM bytes from disk."""
    path = Path(private_key_path)
    if not path.exists():
        raise FileNotFoundError(f"Private key file not found: {path}")
    if not path.is_file():
        raise OSError(f"Private key path '{path}' is not a readable file.")
    return path.read_bytes()


def _read_private_key_env(
    private_key_env: str,
    environment: Mapping[str, str] | None = None,
) -> bytes:
    """Read private-key PEM bytes from a named environment variable."""
    resolved_environment = os.environ if environment is None else environment
    value = resolved_environment.get(private_key_env)
    if value is None or not value.strip():
        raise ValueError(f"Environment variable {private_key_env} does not contain non-empty private key data.")
    return value.encode("utf-8")


def _read_private_key_value(private_key_value: str | bytes) -> bytes:
    """Read private-key PEM bytes from a direct in-memory value."""
    if isinstance(private_key_value, bytes):
        if not private_key_value.strip():
            raise ValueError("Direct private key value does not contain non-empty private key data.")
        return private_key_value

    if not private_key_value.strip():
        raise ValueError("Direct private key value does not contain non-empty private key data.")
    return private_key_value.encode("utf-8")


def _parse_exchange_config_value(exchange_config_value: str | bytes | Mapping[str, Any]) -> Mapping[str, Any]:
    """Parse an in-memory exchange-config payload."""
    if isinstance(exchange_config_value, Mapping):
        return dict(exchange_config_value)

    try:
        raw_value = (
            exchange_config_value.decode("utf-8") if isinstance(exchange_config_value, bytes) else exchange_config_value
        )
        parsed_value = json.loads(raw_value)
    except UnicodeDecodeError as error:
        raise ValueError(f"Provided exchange config value is not valid UTF-8 JSON: {error}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Provided exchange config value is not valid JSON: {error}") from error

    if not isinstance(parsed_value, dict):
        raise ValueError("Provided exchange config value must decode to a JSON object.")

    return parsed_value


def _recipient_kids(exchange_config: Mapping[str, Any]) -> list[str]:
    """Extract recipient key identifiers from an exchange-config envelope."""
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
