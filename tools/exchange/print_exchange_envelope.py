#!/usr/bin/env python3
"""Print the contents of an Open Link Token exchange JWE envelope and payload."""

from __future__ import annotations

# ruff: noqa: E402
import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

from validate_exchange_secret import decrypt_exchange_payload, load_exchange_config, resolve_private_key_pem

PROGRAM = "print_exchange_envelope.py"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for exchange envelope inspection."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="Print an initiate-exchange JWE envelope, decode its protected header, and decrypt its payload.",
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
        help="Optional path to a sender or recipient private key PEM that matches one JWE recipient entry.",
    )
    private_key_group.add_argument(
        "--private-key-stdin",
        action="store_true",
        default=False,
        help="Read a sender or recipient private key PEM from stdin instead of a file path.",
    )
    return parser.parse_args()


def inspect_exchange_envelope(
    exchange_config_path: Path,
    private_key_path: Path | None,
    private_key_stdin: bool = False,
) -> dict[str, Any]:
    """Load an exchange envelope and add decoded header and decrypted payload views."""
    exchange_config = load_exchange_config(exchange_config_path)
    rendered_envelope = dict(exchange_config)
    rendered_envelope["protectedDecoded"] = _decode_protected_header(exchange_config["protected"])
    private_pem = resolve_private_key_pem(exchange_config, private_key_path, private_key_stdin=private_key_stdin)
    rendered_envelope["decryptedPayload"] = decrypt_exchange_payload(exchange_config, private_pem)
    return rendered_envelope


def _decode_protected_header(protected_header: str) -> dict[str, Any]:
    """Decode the base64url-protected JOSE header into a JSON object."""
    padding = "=" * (-len(protected_header) % 4)
    try:
        protected_header_bytes = base64.urlsafe_b64decode(protected_header + padding)
        decoded_header = json.loads(protected_header_bytes)
    except (ValueError, json.JSONDecodeError) as error:
        raise ValueError("Exchange config protected header is not valid base64url JSON.") from error

    if not isinstance(decoded_header, dict):
        raise ValueError("Exchange config protected header must decode to a JSON object.")
    return decoded_header


def main() -> int:
    """Run the helper and print the rendered envelope JSON."""
    args = parse_args()
    exchange_config_path = Path(args.exchange_config).expanduser()
    private_key_path = Path(args.private_key).expanduser() if args.private_key is not None else None

    try:
        rendered_envelope = inspect_exchange_envelope(
            exchange_config_path,
            private_key_path,
            private_key_stdin=args.private_key_stdin,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"Failed to print exchange envelope: {error}", file=sys.stderr)
        return 1

    print(json.dumps(rendered_envelope, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
