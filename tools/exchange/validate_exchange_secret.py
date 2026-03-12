#!/usr/bin/env python3
"""Validate that an OpenToken JWE exchange config can be decrypted by either side."""

from __future__ import annotations

# ruff: noqa: E402
import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "lib" / "python" / "opentoken-cli" / "src" / "main"))
sys.path.insert(0, str(REPO_ROOT / "lib" / "python" / "opentoken" / "src" / "main"))

from jwcrypto.common import JWException

from opentoken_cli.util.ec_key_utils import (
    derive_public_key_from_private_pem,
    fingerprint_to_kid,
    public_key_fingerprint,
)
from opentoken_cli.util.exchange_jwe import decrypt_exchange_envelope, resolve_private_key_by_kid
from opentoken_cli.util.stdin_utils import read_required_stdin_bytes

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
        help="Path to the .exchange.json file produced by `opentoken initiate-exchange`.",
    )
    private_key_group = parser.add_mutually_exclusive_group(required=False)
    private_key_group.add_argument(
        "--private-key",
        required=False,
        help="Optional path to a sender or recipient private key PEM that matches one JWE recipient entry.",
    )
    private_key_group.add_argument(
        "--private-key-stdin",
        action="store_true",
        default=False,
        help="Read a sender or recipient private key PEM from stdin instead of a file path.",
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
    exchange_config = _load_exchange_config(exchange_config_path)
    private_pem = _resolve_private_key_pem(exchange_config, private_key_path, private_key_stdin=private_key_stdin)
    payload = _decrypt_payload(exchange_config, private_pem)
    return _extract_hashing_secret(payload)


def _load_exchange_config(exchange_config_path: Path) -> dict[str, Any]:
    """Load and validate the top-level exchange config structure."""
    exchange_config = json.loads(exchange_config_path.read_text(encoding="utf-8"))
    if not isinstance(exchange_config, dict):
        raise ValueError("Exchange config must be a JSON object.")

    if exchange_config.get("version") != 1:
        raise ValueError("Exchange config must declare top-level version 1.")

    recipients = exchange_config.get("recipients")
    if not isinstance(recipients, list) or not recipients:
        raise ValueError("Exchange config must contain at least one JWE recipient entry.")

    return exchange_config


def _resolve_private_key_pem(
    exchange_config: dict[str, Any],
    private_key_path: Path | None,
    private_key_stdin: bool = False,
) -> bytes:
    """Return the caller-supplied private key or resolve a local key by recipient kid."""
    recipient_kids = _recipient_kids(exchange_config)
    if private_key_path is not None and private_key_stdin:
        raise ValueError("Use either --private-key or --private-key-stdin, not both.")

    if private_key_stdin:
        private_pem = read_required_stdin_bytes("--private-key-stdin", "private key")
        private_key_kid = _kid_for_private_key(private_pem)
        if private_key_kid not in recipient_kids:
            raise ValueError("Provided private key does not match any JWE recipient entry in the exchange config.")
        return private_pem

    if private_key_path is not None:
        private_pem = private_key_path.read_bytes()
        private_key_kid = _kid_for_private_key(private_pem)
        if private_key_kid not in recipient_kids:
            raise ValueError("Provided private key does not match any JWE recipient entry in the exchange config.")
        return private_pem

    opentoken_dir = Path.home() / ".opentoken"
    missing_kids: list[str] = []
    for kid in recipient_kids:
        try:
            return resolve_private_key_by_kid(opentoken_dir, kid)
        except FileNotFoundError:
            missing_kids.append(kid)

    raise ValueError(
        "No local private key could be resolved for any exchange recipient kid "
        f"in {opentoken_dir}: {', '.join(missing_kids)}"
    )


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
    """Derive the fingerprint-based kid for a PEM-encoded private key."""
    public_pem, _ = derive_public_key_from_private_pem(private_pem)
    return fingerprint_to_kid(public_key_fingerprint(public_pem))


def _decrypt_payload(exchange_config: dict[str, Any], private_pem: bytes) -> dict[str, Any]:
    """Decrypt the exchange envelope and parse the payload JSON."""
    try:
        payload_bytes = decrypt_exchange_envelope(exchange_config, private_pem)
    except JWException as error:
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


def main() -> int:
    """Run the helper and print the recovered hashing secret."""
    args = parse_args()
    exchange_config_path = Path(args.exchange_config).expanduser()
    private_key_path = Path(args.private_key).expanduser() if args.private_key is not None else None

    try:
        plaintext_secret = decrypt_exchange_secret(
            exchange_config_path,
            private_key_path,
            private_key_stdin=args.private_key_stdin,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Failed to decrypt exchange secret: {error}", file=sys.stderr)
        return 1

    print(f"Recovered hashing secret ({len(plaintext_secret)} bytes).")
    if args.expected_secret is not None:
        if plaintext_secret != args.expected_secret.encode("utf-8"):
            print("Recovered secret does not match expected secret.", file=sys.stderr)
            return 1
        print("Recovered secret matches expected secret.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
