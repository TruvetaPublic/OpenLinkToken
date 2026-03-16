"""
Copyright (c) Truveta. All rights reserved.
"""

import json
from pathlib import Path

import pytest
from jwcrypto import jwe, jwk

from opentoken.ec_key_utils import fingerprint_to_kid, generate_key_pair, public_key_fingerprint
from opentoken.exchange_config import (
    derive_transport_encryption_key,
    load_exchange_config,
    resolve_exchange_config,
    resolve_exchange_config_inputs,
    resolve_exchange_config_private_key,
)
from opentoken.exchange_jwe import (
    EXCHANGE_JWE_CONTENT_TYPE,
    EXCHANGE_JWE_ENCRYPTION,
    EXCHANGE_JWE_RECIPIENT_ALGORITHM,
    EXCHANGE_JWE_TYPE,
    build_exchange_envelope,
    decrypt_exchange_envelope,
    resolve_private_key_by_kid,
)


def test_fingerprint_to_kid_normalizes_sha256_fingerprint():
    """Fingerprint-based recipient ids use lowercase hyphenated sha256 values."""
    assert fingerprint_to_kid("AA:BB:CC:DD:EE:FF") == "sha256:aa-bb-cc-dd-ee-ff"


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
        "recipientPublicKey": recipient_public_pem.decode("utf-8"),
        "senderKeyFingerprint": public_key_fingerprint(sender_public_pem),
        "senderPublicKey": sender_public_pem.decode("utf-8"),
    }

    recipient_headers = [entry["header"] for entry in envelope["recipients"]]
    assert envelope["version"] == 1
    assert {header["kid"] for header in recipient_headers} == {
        "sha256:" + public_key_fingerprint(sender_public_pem).lower().replace(":", "-"),
        "sha256:" + public_key_fingerprint(recipient_public_pem).lower().replace(":", "-"),
    }


def test_resolve_private_key_by_kid_uses_matching_public_key_basename(tmp_path: Path):
    """Kid resolution maps a matching public key file back to its private key PEM."""
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


def test_resolve_exchange_config_decodes_hashing_secret_and_identifies_sender_role(tmp_path: Path):
    """Resolved exchange configs expose raw hashing-secret bytes and the active participant role."""
    sender_private_pem, sender_public_pem = generate_key_pair("P-256")
    _, recipient_public_pem = generate_key_pair("P-256")
    exchange_config_path = tmp_path / "exchange.exchange.json"
    exchange_config_path.write_text(
        json.dumps(
            build_exchange_envelope(
                exchange_name="shared-exchange",
                hashing_secret=b"shared-hashing-secret",
                sender_public_pem=sender_public_pem,
                recipient_public_pem=recipient_public_pem,
                curve="P-256",
                created_at="2026-03-12T00:00:00Z",
                exchange_id="exchange-456",
            )
        ),
        encoding="utf-8",
    )

    resolved = resolve_exchange_config(exchange_config_path, sender_private_pem)

    assert resolved.path == exchange_config_path
    assert resolved.version == 1
    assert resolved.private_key_pem == sender_private_pem
    assert resolved.private_key_role == "sender"
    assert resolved.hashing_secret == b"shared-hashing-secret"
    assert resolved.payload["exchangeId"] == "exchange-456"


def test_derive_transport_encryption_key_matches_for_both_participants(tmp_path: Path):
    """Sender and recipient should derive the same 32-byte transport key from the same config."""
    sender_private_pem, sender_public_pem = generate_key_pair("P-256")
    recipient_private_pem, recipient_public_pem = generate_key_pair("P-256")
    exchange_config_path = tmp_path / "exchange.exchange.json"
    exchange_config_path.write_text(
        json.dumps(
            build_exchange_envelope(
                exchange_name="shared-exchange",
                hashing_secret=b"shared-hashing-secret",
                sender_public_pem=sender_public_pem,
                recipient_public_pem=recipient_public_pem,
                curve="P-256",
                created_at="2026-03-12T00:00:00Z",
                exchange_id="exchange-789",
            )
        ),
        encoding="utf-8",
    )

    sender_exchange = resolve_exchange_config(exchange_config_path, sender_private_pem)
    recipient_exchange = resolve_exchange_config(exchange_config_path, recipient_private_pem)

    assert derive_transport_encryption_key(sender_exchange) == derive_transport_encryption_key(recipient_exchange)
    assert len(derive_transport_encryption_key(sender_exchange)) == 32


def test_load_exchange_config_rejects_future_v2_exchange_config(tmp_path: Path):
    """Exchange-config version 2 should fail validation during load."""
    sender_private_pem, sender_public_pem = generate_key_pair("P-256")
    _, recipient_public_pem = generate_key_pair("P-256")
    payload = {
        "exchangeName": "legacy",
        "hashingSecret": "bGVnYWN5LWhhc2hpbmctc2VjcmV0",
        "hashingSecretEncoding": "base64url",
        "senderKeyFingerprint": public_key_fingerprint(sender_public_pem),
        "recipientKeyFingerprint": public_key_fingerprint(recipient_public_pem),
        "curve": "P-256",
        "createdAt": "2026-03-12T00:00:00Z",
        "exchangeId": "exchange-legacy",
    }
    protected = {
        "typ": EXCHANGE_JWE_TYPE,
        "cty": EXCHANGE_JWE_CONTENT_TYPE,
        "enc": EXCHANGE_JWE_ENCRYPTION,
    }
    envelope = jwe.JWE(
        json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        protected=json.dumps(protected, separators=(",", ":")),
    )
    for public_pem in (sender_public_pem, recipient_public_pem):
        envelope.add_recipient(
            jwk.JWK.from_pem(public_pem),
            header=json.dumps(
                {
                    "alg": EXCHANGE_JWE_RECIPIENT_ALGORITHM,
                    "kid": fingerprint_to_kid(public_key_fingerprint(public_pem)),
                },
                separators=(",", ":"),
            ),
        )

    exchange_config_path = tmp_path / "future.exchange.json"
    serialized = json.loads(envelope.serialize(compact=False))
    serialized["version"] = 2
    exchange_config_path.write_text(json.dumps(serialized), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported exchange config version '2'. Supported versions: 1."):
        load_exchange_config(exchange_config_path)


def test_resolve_exchange_config_private_key_reads_explicit_private_key_path(tmp_path: Path):
    """Explicit private-key paths should be read directly without keyring lookup."""
    exchange_config_path, sender_private_pem = _write_current_exchange_config(tmp_path)
    loaded_exchange = load_exchange_config(exchange_config_path)
    private_key_path = tmp_path / "provided.private.pem"
    private_key_path.write_bytes(sender_private_pem)

    resolved_private_pem = resolve_exchange_config_private_key(loaded_exchange, private_key_path=private_key_path)

    assert resolved_private_pem == sender_private_pem


def test_resolve_exchange_config_private_key_reads_private_key_env(tmp_path: Path, monkeypatch):
    """Named environment variables should supply private-key PEM bytes."""
    exchange_config_path, sender_private_pem = _write_current_exchange_config(tmp_path)
    loaded_exchange = load_exchange_config(exchange_config_path)
    monkeypatch.setenv("OPENTOKEN_TEST_PRIVATE_KEY", sender_private_pem.decode("utf-8"))

    resolved_private_pem = resolve_exchange_config_private_key(
        loaded_exchange,
        private_key_env="OPENTOKEN_TEST_PRIVATE_KEY",
    )

    assert resolved_private_pem == sender_private_pem


def test_resolve_exchange_config_private_key_falls_back_to_opentoken_kid_lookup(tmp_path: Path, monkeypatch):
    """Recipient kids should resolve against ~/.opentoken when no path or env is supplied."""
    exchange_config_path, sender_private_pem = _write_current_exchange_config(tmp_path)
    loaded_exchange = load_exchange_config(exchange_config_path)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    resolved_private_pem = resolve_exchange_config_private_key(loaded_exchange)

    assert resolved_private_pem == sender_private_pem


def test_resolve_exchange_config_inputs_loads_and_decrypts_from_private_key_env(tmp_path: Path, monkeypatch):
    """Convenience helpers should load the config, resolve the private key, and decrypt the payload."""
    exchange_config_path, sender_private_pem = _write_current_exchange_config(tmp_path)
    monkeypatch.setenv("OPENTOKEN_TEST_PRIVATE_KEY", sender_private_pem.decode("utf-8"))

    resolved_exchange = resolve_exchange_config_inputs(
        exchange_config_path=exchange_config_path,
        private_key_env="OPENTOKEN_TEST_PRIVATE_KEY",
    )

    assert resolved_exchange.path == exchange_config_path
    assert resolved_exchange.private_key_pem == sender_private_pem
    assert resolved_exchange.private_key_role == "sender"
    assert resolved_exchange.hashing_secret == b"shared-hashing-secret"


def test_resolve_exchange_config_inputs_accepts_direct_exchange_config_and_private_key_values(tmp_path: Path):
    """Direct exchange-config JSON and private-key PEM values should be accepted without temp files or env vars."""
    exchange_config_path, sender_private_pem = _write_current_exchange_config(tmp_path)

    resolved_exchange = resolve_exchange_config_inputs(
        exchange_config_value=exchange_config_path.read_text(encoding="utf-8"),
        private_key_value=sender_private_pem.decode("utf-8"),
    )

    assert resolved_exchange.version == 1
    assert resolved_exchange.private_key_pem == sender_private_pem
    assert resolved_exchange.private_key_role == "sender"
    assert resolved_exchange.hashing_secret == b"shared-hashing-secret"


def _write_current_exchange_config(tmp_path: Path) -> tuple[Path, bytes]:
    """Create a version 1 exchange config plus matching ~/.opentoken sender key material."""
    sender_private_pem, sender_public_pem = generate_key_pair("P-256")
    _, recipient_public_pem = generate_key_pair("P-256")
    exchange_config_path = tmp_path / "current.exchange.json"
    exchange_config_path.write_text(
        json.dumps(
            build_exchange_envelope(
                exchange_name="shared-exchange",
                hashing_secret=b"shared-hashing-secret",
                sender_public_pem=sender_public_pem,
                recipient_public_pem=recipient_public_pem,
                curve="P-256",
                created_at="2026-03-12T00:00:00Z",
                exchange_id="exchange-helpers",
            )
        ),
        encoding="utf-8",
    )

    key_dir = tmp_path / ".opentoken"
    key_dir.mkdir()
    key_dir.joinpath("current.private.pem").write_bytes(sender_private_pem)
    key_dir.joinpath("current.public.pem").write_bytes(sender_public_pem)
    return exchange_config_path, sender_private_pem
