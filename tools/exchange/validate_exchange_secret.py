#!/usr/bin/env python3
"""Validate that an Open Link Token JWE exchange config can be decrypted by either side."""

from __future__ import annotations

# ruff: noqa: E402
import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "lib" / "python" / "openlinktoken-cli" / "src" / "main"))
sys.path.insert(0, str(REPO_ROOT / "lib" / "python" / "openlinktoken" / "src" / "main"))

from jwcrypto.common import JWException

from openlinktoken.exchange_config import (
    load_exchange_config as load_shared_exchange_config,
)
from openlinktoken.exchange_config import (
    resolve_exchange_config_private_key,
)
from openlinktoken.exchange_jwe import decrypt_exchange_envelope
from openlinktoken.exchange_kem import decrypt_exchange_envelope_v2
from openlinktoken.exchange_key_bundle import ExchangeKeyBundle, KeyBundleError
from openlinktoken_cli.util.ec_key_utils import (
    derive_public_key_from_private_pem,
    fingerprint_to_kid,
    public_key_fingerprint,
)
from openlinktoken_cli.util.stdin_utils import read_required_stdin_bytes

PROGRAM = "validate_exchange_secret.py"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for exchange validation."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="Decrypt an initiate-exchange JWE envelope with either matching private key.",
    )
    parser.add_argument(
        "--exchange-config",
        required=True,
        help="Path to the .exchange.json file produced by `olt initiate-exchange`.",
    )
    private_key_group = parser.add_mutually_exclusive_group(required=False)
    private_key_group.add_argument(
        "--private-key",
        required=False,
        help="Optional path to a sender or recipient private PEM or JSON bundle that matches one JWE recipient entry.",
    )
    private_key_group.add_argument(
        "--private-key-stdin",
        action="store_true",
        default=False,
        help="Read a sender or recipient private PEM or JSON bundle from stdin instead of a file path.",
    )
    parser.add_argument(
        "--expected-secret",
        required=False,
        help="Optional plaintext secret to compare against the decrypted value.",
    )
    return parser.parse_args()


def decrypt_exchange_secret(
    exchange_config_path: Path,
    private_key_path: Path | None,
    private_key_stdin: bool = False,
) -> bytes:
    """Recover the plaintext hashing secret bytes from a JWE exchange config."""
    exchange_config = load_exchange_config(exchange_config_path)
    private_material = resolve_private_key_pem(
        exchange_config,
        private_key_path,
        private_key_stdin=private_key_stdin,
    )
    payload = decrypt_exchange_payload(exchange_config, private_material)
    return _extract_hashing_secret(payload)


def load_exchange_config(exchange_config_path: Path) -> dict[str, Any]:
    """Load and validate an exchange config through the shared resolver."""
    return dict(load_shared_exchange_config(exchange_config_path).config)


def resolve_private_key_pem(
    exchange_config: dict[str, Any],
    private_key_path: Path | None,
    private_key_stdin: bool = False,
) -> bytes:
    """Return caller-supplied private material or resolve it by recipient kid."""
    if private_key_path is not None and private_key_stdin:
        raise ValueError("Use either --private-key or --private-key-stdin, not both.")

    loaded_exchange = load_shared_exchange_config(exchange_config_value=exchange_config)
    if private_key_stdin:
        private_material = resolve_exchange_config_private_key(
            loaded_exchange,
            private_key_value=read_required_stdin_bytes("--private-key-stdin", "private key"),
        )
        _require_recipient_key(exchange_config, private_material)
        return private_material

    if private_key_path is not None:
        private_material = resolve_exchange_config_private_key(
            loaded_exchange,
            private_key_value=private_key_path.read_bytes(),
        )
        _require_recipient_key(exchange_config, private_material)
        return private_material

    return resolve_exchange_config_private_key(
        loaded_exchange,
        openlinktoken_dir=Path.home() / ".openlinktoken",
    )


def _require_recipient_key(exchange_config: dict[str, Any], private_material: bytes) -> None:
    """Reject direct key material that cannot target a listed recipient."""
    if _kid_for_private_key(private_material) not in _recipient_kids(exchange_config):
        raise ValueError("Provided private key does not match any JWE recipient entry in the exchange config.")


def _recipient_kids(exchange_config: dict[str, Any]) -> list[str]:
    """Return the ordered list of recipient kid values from the JWE envelope."""
    recipient_kids: list[str] = []
    for index, recipient in enumerate(exchange_config["recipients"]):
        if not isinstance(recipient, dict):
            raise ValueError(f"Exchange recipient at index {index} must be an object.")

        header = recipient.get("header")
        if not isinstance(header, dict):
            raise ValueError(f"Exchange recipient at index {index} must include a JOSE header object.")

        kid = header.get("kid")
        if not isinstance(kid, str) or not kid:
            raise ValueError(f"Exchange recipient at index {index} must include a non-empty header.kid.")

        recipient_kids.append(kid)

    return recipient_kids


def _kid_for_private_key(private_pem: bytes) -> str:
    """Derive the key identifier for PEM or JSON-bundle private material."""
    try:
        return ExchangeKeyBundle.from_json(private_pem, require_private=True).kid
    except (KeyBundleError, UnicodeDecodeError, json.JSONDecodeError):
        pass
    public_pem, _ = derive_public_key_from_private_pem(private_pem)
    return fingerprint_to_kid(public_key_fingerprint(public_pem))


def decrypt_exchange_payload(exchange_config: dict[str, Any], private_pem: bytes) -> dict[str, Any]:
    """Decrypt the exchange envelope and parse the payload JSON."""
    loaded_exchange = load_shared_exchange_config(exchange_config_value=exchange_config)
    try:
        if loaded_exchange.version == 2:
            payload_bytes, _ = decrypt_exchange_envelope_v2(exchange_config, private_pem)
        else:
            payload_bytes = decrypt_exchange_envelope(exchange_config, private_pem)
    except (JWException, ValueError, KeyError, TypeError) as error:
        raise ValueError("Provided key material does not decrypt the exchange config.") from error

    payload = json.loads(payload_bytes)
    if not isinstance(payload, dict):
        raise ValueError("Exchange payload must be a JSON object.")
    return payload


def _extract_hashing_secret(payload: dict[str, Any]) -> bytes:
    """Decode the hashing secret from the decrypted exchange payload."""
    encoding = payload.get("hashingSecretEncoding")
    hashing_secret = payload.get("hashingSecret")

    if encoding != "base64url":
        raise ValueError(f"Unsupported hashingSecretEncoding '{encoding}'.")
    if not isinstance(hashing_secret, str) or not hashing_secret:
        raise ValueError("Exchange payload must include a non-empty hashingSecret string.")

    padding = "=" * (-len(hashing_secret) % 4)
    return base64.urlsafe_b64decode(hashing_secret + padding)


def _extract_rotation_iv(payload: dict[str, Any]) -> bytes:
    """Decode the rotation IV from the decrypted exchange payload, or return empty bytes if not set."""
    encoding = payload.get("rotationIvEncoding")
    value = payload.get("rotationIv")
    if value is None:
        return b""
    if encoding != "base64url":
        raise ValueError(f"Unsupported rotationIvEncoding '{encoding}'.")
    if not isinstance(value, str) or not value:
        return b""
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def main() -> int:
    """Run the helper and print the recovered hashing secret and rotation parameters."""
    args = parse_args()
    exchange_config_path = Path(args.exchange_config).expanduser()
    private_key_path = Path(args.private_key).expanduser() if args.private_key is not None else None

    try:
        exchange_config = load_exchange_config(exchange_config_path)
        private_pem = resolve_private_key_pem(
            exchange_config, private_key_path, private_key_stdin=args.private_key_stdin
        )
        payload = decrypt_exchange_payload(exchange_config, private_pem)
        plaintext_secret = _extract_hashing_secret(payload)
        rotation_iv = _extract_rotation_iv(payload)
        rotation_count = payload.get("rotationCount") or 0
        bin_width = payload.get("binWidth") or 0.05
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Failed to decrypt exchange secret: {error}", file=sys.stderr)
        return 1

    print(f"Recovered hashing secret ({len(plaintext_secret)} bytes).")
    if rotation_iv:
        print(f"Rotation IV ({len(rotation_iv)} bytes): {rotation_iv.hex()}")
    else:
        print("Rotation IV: (not set)")
    print(f"Rotation count: {rotation_count}")
    print(f"Bin width: {bin_width}")

    if args.expected_secret is not None:
        if plaintext_secret != args.expected_secret.encode("utf-8"):
            print("Recovered secret does not match expected secret.", file=sys.stderr)
            return 1
        print("Recovered secret matches expected secret.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
