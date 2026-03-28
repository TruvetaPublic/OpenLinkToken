#!/usr/bin/env python3
"""Print the decrypted contents of an OpenToken JWE exchange config file."""

from __future__ import annotations

# ruff: noqa: E402
import argparse
import base64
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "lib" / "python" / "opentoken-cli" / "src" / "main"))
sys.path.insert(0, str(REPO_ROOT / "lib" / "python" / "opentoken" / "src" / "main"))

from opentoken.exchange_config import (
    ResolvedExchangeConfig,
    resolve_exchange_config_inputs,
)

PROGRAM = "inspect_exchange_config.py"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description=(
            "Decrypt and print the contents of an OpenToken JWE exchange config file.\n\n"
            "The private key is resolved automatically from ~/.opentoken/ when omitted."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--exchange-config",
        required=True,
        metavar="PATH",
        help="Path to the .exchange.json file produced by `opentoken initiate-exchange`.",
    )
    private_key_group = parser.add_mutually_exclusive_group(required=False)
    private_key_group.add_argument(
        "--private-key",
        metavar="PATH",
        help="Path to the sender or recipient private key PEM. Auto-resolved from ~/.opentoken/ when omitted.",
    )
    private_key_group.add_argument(
        "--private-key-env",
        metavar="ENV_VAR",
        help="Read the private key PEM from the named environment variable.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output the full decrypted payload as JSON instead of the human-readable summary.",
    )
    return parser.parse_args()


def _decode_base64url(value: str) -> bytes:
    """Decode an unpadded base64url string."""
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _print_summary(exchange: ResolvedExchangeConfig) -> None:
    """Print a human-readable summary of the resolved exchange config."""
    p = exchange.payload

    print("Exchange Config Summary")
    print("=" * 60)
    print(f"  Exchange name    : {p.get('exchangeName', '(none)')}")
    print(f"  Exchange ID      : {p.get('exchangeId', '(none)')}")
    print(f"  Created at       : {p.get('createdAt', '(none)')}")
    print(f"  Curve            : {p.get('curve', '(none)')}")
    print(f"  Private key role : {exchange.private_key_role}")
    print()

    print("Hashing Secret")
    print("-" * 60)
    secret_hex = exchange.hashing_secret.hex()
    print(f"  Length  : {len(exchange.hashing_secret)} bytes")
    print(f"  Hex     : {secret_hex[:32]}{'...' if len(secret_hex) > 32 else ''}")
    print()

    print("Rotation Parameters")
    print("-" * 60)
    iv_raw = exchange.rotation_iv
    print(f"  IV              : {iv_raw.hex()[:32]}{'...' if len(iv_raw) > 32 else ''} ({len(iv_raw)} bytes)")
    print(f"  Rotation count  : {exchange.rotation_count}")
    print(f"  Bin width       : {exchange.bin_width}")
    if exchange.dimension_bias:
        bias_preview = ", ".join(repr(v) for v in exchange.dimension_bias[:6])
        suffix = f", ... ({len(exchange.dimension_bias)} total)" if len(exchange.dimension_bias) > 6 else ""
        print(f"  Dimension bias  : [{bias_preview}{suffix}]")
    else:
        print("  Dimension bias  : (not set)")
    print()

    print("Key Fingerprints")
    print("-" * 60)
    print(f"  Sender    : {p.get('senderKeyFingerprint', '(none)')}")
    print(f"  Recipient : {p.get('recipientKeyFingerprint', '(none)')}")
    print()


def main() -> int:
    """Decrypt an exchange config and print its contents."""
    args = parse_args()

    try:
        exchange = resolve_exchange_config_inputs(
            exchange_config_path=args.exchange_config,
            private_key_path=args.private_key,
            private_key_env=args.private_key_env,
        )
    except (FileNotFoundError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.output_json:
        print(json.dumps(dict(exchange.payload), indent=2))
    else:
        _print_summary(exchange)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
