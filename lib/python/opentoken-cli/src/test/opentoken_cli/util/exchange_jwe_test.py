"""
Copyright (c) Truveta. All rights reserved.
"""

import json
from pathlib import Path

from opentoken_cli.util.ec_key_utils import generate_key_pair, public_key_fingerprint
from opentoken_cli.util.exchange_jwe import (
    build_exchange_envelope,
    decrypt_exchange_envelope,
    resolve_private_key_by_kid,
)


def test_fingerprint_to_kid_normalizes_sha256_fingerprint():
    """Fingerprint-based recipient ids use lowercase hyphenated sha256 values."""
    from opentoken_cli.util.ec_key_utils import fingerprint_to_kid

    fingerprint = "AA:BB:CC:DD:EE:FF"

    assert fingerprint_to_kid(fingerprint) == "sha256:aa-bb-cc-dd-ee-ff"


def test_build_exchange_envelope_round_trips_for_either_private_key():
    """Either intended recipient private key can decrypt the same exchange envelope."""
    sender_private_pem, sender_public_pem = generate_key_pair("P-256")
    recipient_private_pem, recipient_public_pem = generate_key_pair("P-256")

    envelope = build_exchange_envelope(
        exchange_name="demo-exchange",
        hashing_secret=b"shared-hashing-secret",
        sender_public_pem=sender_public_pem,
        recipient_public_pem=recipient_public_pem,
        curve="P-256",
        created_at="2026-03-11T00:00:00Z",
        exchange_id="exchange-123",
    )

    sender_payload = json.loads(decrypt_exchange_envelope(envelope, sender_private_pem))
    recipient_payload = json.loads(decrypt_exchange_envelope(envelope, recipient_private_pem))

    assert sender_payload == recipient_payload
    assert sender_payload == {
        "createdAt": "2026-03-11T00:00:00Z",
        "curve": "P-256",
        "exchangeId": "exchange-123",
        "exchangeName": "demo-exchange",
        "hashingSecret": "c2hhcmVkLWhhc2hpbmctc2VjcmV0",
        "hashingSecretEncoding": "base64url",
        "recipientKeyFingerprint": public_key_fingerprint(recipient_public_pem),
        "senderKeyFingerprint": public_key_fingerprint(sender_public_pem),
    }

    recipient_headers = [entry["header"] for entry in envelope["recipients"]]
    assert envelope["version"] == 1
    assert {header["kid"] for header in recipient_headers} == {
        "sha256:" + public_key_fingerprint(sender_public_pem).lower().replace(":", "-"),
        "sha256:" + public_key_fingerprint(recipient_public_pem).lower().replace(":", "-"),
    }


def test_resolve_private_key_by_kid_uses_matching_public_key_basename(tmp_path: Path):
    """Kid resolution maps a matching public key file back to its private key PEM."""
    from opentoken_cli.util.ec_key_utils import fingerprint_to_kid

    opentoken_dir = tmp_path / ".opentoken"
    opentoken_dir.mkdir()

    expected_private_pem, expected_public_pem = generate_key_pair("P-256")
    expected_prefix = opentoken_dir / "sender-key"
    expected_prefix.with_suffix(".public.pem").write_bytes(expected_public_pem)
    expected_prefix.with_suffix(".private.pem").write_bytes(expected_private_pem)

    other_private_pem, other_public_pem = generate_key_pair("P-256")
    other_prefix = opentoken_dir / "other-key"
    other_prefix.with_suffix(".public.pem").write_bytes(other_public_pem)
    other_prefix.with_suffix(".private.pem").write_bytes(other_private_pem)

    resolved_private_pem = resolve_private_key_by_kid(
        opentoken_dir,
        fingerprint_to_kid(public_key_fingerprint(expected_public_pem)),
    )

    assert resolved_private_pem == expected_private_pem
