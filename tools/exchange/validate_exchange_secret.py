#!/usr/bin/env python3
"""Validate that an OpenToken exchange config can be decrypted by either side."""

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ec import ECDH
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_private_key,
    load_pem_public_key,
)

PROGRAM = "validate_exchange_secret.py"
HKDF_INFO = b"opentoken-exchange-v1"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for exchange validation."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="Decrypt an initiate-exchange config with either matching private key.",
    )
    parser.add_argument(
        "--exchange-config",
        required=True,
        help="Path to the .exchange.json file produced by `opentoken initiate-exchange`.",
    )
    parser.add_argument(
        "--private-key",
        required=False,
        help=(
            "Optional path to a sender or recipient private key PEM that matches one of the public keys in the config."
        ),
    )
    parser.add_argument(
        "--counterparty-public-key",
        required=False,
        help="Optional public key PEM for older configs that do not embed partnerKey.publicKey.",
    )
    parser.add_argument(
        "--expected-secret",
        required=False,
        help="Optional plaintext secret to compare against the decrypted value.",
    )
    return parser.parse_args()


def _serialize_public_key(private_key) -> bytes:
    """Return the PEM-encoded public key corresponding to a private key."""
    return private_key.public_key().public_bytes(
        encoding=Encoding.PEM,
        format=PublicFormat.SubjectPublicKeyInfo,
    )


def _normalize_fingerprint(fingerprint: str) -> str:
    """Normalize a fingerprint string for comparison."""
    return fingerprint.replace(":", "").replace(" ", "").upper()


def _fingerprint_public_key_pem(public_key_pem: bytes) -> str:
    """Return a SHA-256 fingerprint for a PEM-encoded public key."""
    public_key = load_pem_public_key(public_key_pem)
    public_key_der = public_key.public_bytes(
        encoding=Encoding.DER,
        format=PublicFormat.SubjectPublicKeyInfo,
    )
    digest = hashlib.sha256(public_key_der).hexdigest().upper()
    return ":".join(digest[index : index + 2] for index in range(0, len(digest), 2))


def _resolve_local_key(exchange_config: dict) -> dict:
    """Return the nested local-key object with a legacy fallback."""
    local_key = exchange_config.get("localKey", exchange_config.get("local_key", {}))
    if not isinstance(local_key, dict):
        raise ValueError("Exchange config localKey must be an object.")
    return local_key


def _resolve_partner_key(exchange_config: dict) -> dict:
    """Return the nested partner-key object with a legacy fallback."""
    partner_key = exchange_config.get("partnerKey", exchange_config.get("partner_key", {}))
    if not isinstance(partner_key, dict):
        raise ValueError("Exchange config partnerKey must be an object.")
    return partner_key


def _resolve_local_public_key_pem(exchange_config: dict) -> bytes:
    """Return the local public key PEM from the current or legacy exchange schema."""
    local_key = _resolve_local_key(exchange_config)
    local_public_key = local_key.get("publicKey", local_key.get("public_key", exchange_config.get("local_public_key")))
    if local_public_key is None:
        raise ValueError("Exchange config does not include local public key material.")
    return local_public_key.encode("utf-8")


def _resolve_partner_public_key_pem(exchange_config: dict) -> bytes | None:
    """Return the partner public key PEM from the current or legacy exchange schema when present."""
    partner_key = _resolve_partner_key(exchange_config)
    partner_public_key = partner_key.get(
        "publicKey",
        exchange_config.get("partnerPublicKey", exchange_config.get("partner_public_key")),
    )
    return partner_public_key.encode("utf-8") if partner_public_key else None


def _validate_public_key_fingerprint(field_name: str, public_key_pem: bytes, fingerprint: str | None) -> None:
    """Validate a bundled public-key fingerprint when one is present."""
    if fingerprint is None:
        return

    actual_fingerprint = _fingerprint_public_key_pem(public_key_pem)
    if _normalize_fingerprint(actual_fingerprint) != _normalize_fingerprint(fingerprint):
        raise ValueError(
            f"{field_name} does not match the bundled public key. Expected {actual_fingerprint}, found {fingerprint}."
        )


def _validate_bundled_fingerprints(exchange_config: dict) -> None:
    """Validate any public-key fingerprints bundled in the exchange config."""
    local_key = _resolve_local_key(exchange_config)
    local_public_pem = _resolve_local_public_key_pem(exchange_config)
    _validate_public_key_fingerprint(
        "localKey.publicKeyFingerprint",
        local_public_pem,
        local_key.get("publicKeyFingerprint", exchange_config.get("localPublicKeyFingerprint")),
    )

    partner_key = _resolve_partner_key(exchange_config)
    partner_public_pem = _resolve_partner_public_key_pem(exchange_config)
    if partner_public_pem is None:
        return

    _validate_public_key_fingerprint(
        "partnerKey.publicKeyFingerprint",
        partner_public_pem,
        partner_key.get(
            "publicKeyFingerprint",
            exchange_config.get(
                "partnerPublicKeyFingerprint",
                exchange_config.get("partner_public_key_fingerprint"),
            ),
        ),
    )


def _resolve_peer_public_key_pem(
    exchange_config: dict, private_key, counterparty_public_key_path: Path | None
) -> bytes:
    """Select the peer public key needed to derive the shared secret for the supplied private key."""
    if counterparty_public_key_path is not None:
        return counterparty_public_key_path.read_bytes()

    local_public_pem = _resolve_local_public_key_pem(exchange_config)
    partner_public_pem = _resolve_partner_public_key_pem(exchange_config)
    caller_public_pem = _serialize_public_key(private_key)

    if caller_public_pem == local_public_pem:
        if partner_public_pem is None:
            raise ValueError(
                "Exchange config does not include partnerKey.publicKey. "
                "Provide --counterparty-public-key for older files."
            )
        return partner_public_pem

    if partner_public_pem is not None and caller_public_pem == partner_public_pem:
        return local_public_pem

    if partner_public_pem is None:
        return local_public_pem

    raise ValueError("Provided private key does not match either public key in the exchange config.")


def _resolve_private_key_pem(exchange_config: dict, private_key_path: Path | None) -> bytes:
    """Return the caller-supplied private key, or the embedded local private key when present."""
    if private_key_path is not None:
        return private_key_path.read_bytes()

    local_key = _resolve_local_key(exchange_config)
    embedded_private_key = local_key.get(
        "privateKey",
        local_key.get("private_key", exchange_config.get("local_private_key")),
    )
    if embedded_private_key is None:
        raise ValueError("Exchange config does not include localKey.privateKey. Provide --private-key.")

    return embedded_private_key.encode("utf-8")


def decrypt_exchange_secret(
    exchange_config_path: Path,
    private_key_path: Path | None,
    counterparty_public_key_path: Path | None = None,
) -> bytes:
    """Recover the plaintext hashing secret bytes from an exchange config."""
    exchange_config = json.loads(exchange_config_path.read_text(encoding="utf-8"))
    _validate_bundled_fingerprints(exchange_config)
    caller_private_key = load_pem_private_key(
        _resolve_private_key_pem(exchange_config, private_key_path),
        password=None,
    )
    peer_public_key_pem = _resolve_peer_public_key_pem(
        exchange_config, caller_private_key, counterparty_public_key_path
    )
    peer_public_key = load_pem_public_key(peer_public_key_pem)

    shared_secret = caller_private_key.exchange(ECDH(), peer_public_key)
    aes_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=HKDF_INFO).derive(shared_secret)

    nonce = base64.b64decode(exchange_config["encryption"]["nonce"])
    encrypted_hashing_secret = exchange_config.get("encryptedHashingSecret")
    if encrypted_hashing_secret is None:
        encrypted_hashing_secret = exchange_config["encrypted_hashing_secret"]

    ciphertext = base64.b64decode(encrypted_hashing_secret)
    return AESGCM(aes_key).decrypt(nonce, ciphertext, None)


def main() -> int:
    """Run the helper and print the recovered hashing secret."""
    args = parse_args()
    exchange_config_path = Path(args.exchange_config).expanduser()
    private_key_path = Path(args.private_key).expanduser() if args.private_key is not None else None
    counterparty_public_key_path = (
        Path(args.counterparty_public_key).expanduser() if args.counterparty_public_key is not None else None
    )

    try:
        plaintext_secret = decrypt_exchange_secret(exchange_config_path, private_key_path, counterparty_public_key_path)
    except InvalidTag:
        print(
            "Failed to decrypt exchange secret: provided key material does not match the exchange config.",
            file=sys.stderr,
        )
        return 1
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Failed to decrypt exchange secret: {error}", file=sys.stderr)
        return 1

    print(f"Recovered hashing secret (base64): {base64.b64encode(plaintext_secret).decode('ascii')}")
    if args.expected_secret is not None:
        if plaintext_secret != args.expected_secret.encode("utf-8"):
            print("Recovered secret does not match expected secret.", file=sys.stderr)
            return 1
        print("Recovered secret matches expected secret.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
