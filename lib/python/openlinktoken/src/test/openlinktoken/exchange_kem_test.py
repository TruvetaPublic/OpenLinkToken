# SPDX-License-Identifier: MIT

import base64
import json
from copy import deepcopy

import pytest
from jwcrypto import jwe, jwk

from openlinktoken.exchange_config import (
    derive_transport_encryption_key,
    load_exchange_config,
    resolve_loaded_exchange_config,
)
from openlinktoken.exchange_kem import build_exchange_envelope_v2, decrypt_exchange_envelope_v2
from openlinktoken.exchange_key_bundle import ExchangeKeyBundle, KeyBundleError, generate_exchange_key_bundle
from openlinktoken.tokentransformer.jwe_match_token_formatter import JweMatchTokenFormatter


def _decode_protected_header(envelope: dict) -> dict:
    """Decode a standard JWE protected header for assertions."""
    protected = envelope["protected"]
    return json.loads(base64.urlsafe_b64decode(protected + "=" * (-len(protected) % 4)))


@pytest.mark.parametrize("suite_id", ["suite-pq-v1", "suite-pq-shake-v1", "suite-pq-hybrid-v1"])
def test_v2_exchange_round_trips_for_both_participants(suite_id):
    """Pure and hybrid recipients recover the same payload and transport key."""
    sender = generate_exchange_key_bundle(suite_id)
    recipient = generate_exchange_key_bundle(suite_id)
    envelope = build_exchange_envelope_v2(
        exchange_name="pqc-exchange",
        hashing_secret=b"0123456789abcdef0123456789abcdef",
        sender_bundle=sender,
        recipient_bundle=recipient,
        created_at="2026-03-12T00:00:00Z",
        exchange_id="exchange-pqc-123",
        rotation_iv=b"rotation-iv",
        rotation_count=3,
        dimension_bias=[0.1, -0.2],
    )

    sender_plaintext, sender_transport_key = decrypt_exchange_envelope_v2(
        envelope, sender.to_json(include_private=True)
    )
    recipient_plaintext, recipient_transport_key = decrypt_exchange_envelope_v2(
        envelope, recipient.to_json(include_private=True)
    )

    assert sender_plaintext == recipient_plaintext
    assert sender_transport_key == recipient_transport_key
    _, repeated_transport_key = decrypt_exchange_envelope_v2(envelope, sender.to_json(include_private=True))
    assert sender_transport_key == repeated_transport_key
    assert len(sender_transport_key) == 32
    assert set(envelope) == {"protected", "recipients", "iv", "ciphertext", "tag"}
    assert _decode_protected_header(envelope) == {
        "typ": "openlinktoken-exchange+jwe",
        "cty": "application/openlinktoken-exchange+json",
        "enc": "A256GCM",
        "version": 2,
        "cryptoSuite": suite_id,
        "exchangeId": "exchange-pqc-123",
    }
    assert all("alg" in recipient_entry["header"] for recipient_entry in envelope["recipients"])


def test_v2_exchange_rejects_short_kmac_hashing_secret():
    """The v2 envelope boundary rejects KMAC secrets shorter than its required key size."""
    sender = generate_exchange_key_bundle("suite-pq-shake-v1")
    recipient = generate_exchange_key_bundle("suite-pq-shake-v1")

    with pytest.raises(ValueError, match="suite-pq-shake-v1.*32 bytes"):
        build_exchange_envelope_v2(
            exchange_name="short-kmac-secret",
            hashing_secret=b"x" * 31,
            sender_bundle=sender,
            recipient_bundle=recipient,
            created_at="2026-03-12T00:00:00Z",
            exchange_id="exchange-short-kmac-secret",
        )


@pytest.mark.parametrize("suite_id", ["suite-pq-v1", "suite-pq-shake-v1", "suite-pq-hybrid-v1"])
def test_v2_transport_key_encrypts_and_decrypts_match_tokens(suite_id):
    """The derived v2 transport key works with the standard match-token formatter."""
    sender = generate_exchange_key_bundle(suite_id)
    recipient = generate_exchange_key_bundle(suite_id)
    envelope = build_exchange_envelope_v2(
        "token-round-trip",
        b"0123456789abcdef0123456789abcdef",
        sender,
        recipient,
        "2026-03-12T00:00:00Z",
        "exchange-token-round-trip",
    )
    resolved = resolve_loaded_exchange_config(
        load_exchange_config(exchange_config_value=envelope),
        sender.to_json(include_private=True),
    )
    transport_key = derive_transport_encryption_key(resolved)

    encrypted_token = JweMatchTokenFormatter(transport_key, "transport-ring", "T1").transform("test-ppid")
    token = jwe.JWE()
    token.deserialize(encrypted_token.removeprefix("olt.V1."))
    key_b64 = base64.urlsafe_b64encode(transport_key).decode("ascii").rstrip("=")
    token.decrypt(jwk.JWK(kty="oct", k=key_b64))
    payload = json.loads(token.payload)

    assert payload["ppid"] == ["test-ppid"]
    assert payload["rid"] == "transport-ring"
    assert payload["rlid"] == "T1"


def test_v2_exchange_resolves_suite_and_transport_key():
    """The shared exchange-config resolver exposes v2 metadata to consumers."""
    sender = generate_exchange_key_bundle("suite-pq-v1")
    recipient = generate_exchange_key_bundle("suite-pq-v1")
    envelope = build_exchange_envelope_v2(
        "resolver-test",
        b"hash-secret",
        sender,
        recipient,
        "2026-03-12T00:00:00Z",
        "exchange-resolver",
    )

    loaded = load_exchange_config(exchange_config_value=envelope)
    resolved = resolve_loaded_exchange_config(loaded, sender.to_json(include_private=True))

    assert loaded.version == 2
    assert resolved.version == 2
    assert resolved.private_key_role == "sender"
    assert resolved.hashing_secret == b"hash-secret"
    assert derive_transport_encryption_key(resolved) == resolved.transport_encryption_key


def test_v2_exchange_rejects_tampered_recipient_algorithm():
    """Recipient algorithms must remain bound to the protected suite."""
    sender = generate_exchange_key_bundle("suite-pq-v1")
    recipient = generate_exchange_key_bundle("suite-pq-v1")
    envelope = build_exchange_envelope_v2(
        "tamper-test",
        b"hash-secret",
        sender,
        recipient,
        "2026-03-12T00:00:00Z",
        "exchange-tamper",
    )
    tampered = deepcopy(envelope)
    tampered["recipients"][0]["header"]["alg"] = "UNKNOWN-KEM"

    with pytest.raises(ValueError, match="algorithm"):
        decrypt_exchange_envelope_v2(tampered, sender.to_json(include_private=True))


def test_v2_exchange_rejects_wrong_private_bundle():
    """A bundle for another recipient cannot unwrap this envelope."""
    sender = generate_exchange_key_bundle("suite-pq-v1")
    recipient = generate_exchange_key_bundle("suite-pq-v1")
    unrelated = generate_exchange_key_bundle("suite-pq-v1")
    envelope = build_exchange_envelope_v2(
        "wrong-key-test",
        b"hash-secret",
        sender,
        recipient,
        "2026-03-12T00:00:00Z",
        "exchange-wrong-key",
    )

    with pytest.raises(ValueError, match="No unique recipient"):
        decrypt_exchange_envelope_v2(envelope, unrelated.to_json(include_private=True))


def test_v2_exchange_rejects_wrong_protected_version():
    """The protected version is authenticated and required for v2."""
    sender = generate_exchange_key_bundle("suite-pq-v1")
    recipient = generate_exchange_key_bundle("suite-pq-v1")
    envelope = build_exchange_envelope_v2(
        "version-test",
        b"hash-secret",
        sender,
        recipient,
        "2026-03-12T00:00:00Z",
        "exchange-version",
    )
    protected = _decode_protected_header(envelope)
    protected["version"] = 1
    envelope["protected"] = (
        base64.urlsafe_b64encode(json.dumps(protected, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )

    with pytest.raises(ValueError, match="version"):
        decrypt_exchange_envelope_v2(envelope, sender.to_json(include_private=True))


def test_v2_exchange_rejects_v1_crypto_suite():
    """Version-1 suites cannot be used in version-2 protected headers."""
    sender = generate_exchange_key_bundle("suite-pq-v1")
    recipient = generate_exchange_key_bundle("suite-pq-v1")
    envelope = build_exchange_envelope_v2(
        "suite-test",
        b"hash-secret",
        sender,
        recipient,
        "2026-03-12T00:00:00Z",
        "exchange-suite",
    )
    protected = _decode_protected_header(envelope)
    protected["cryptoSuite"] = "suite-sha256-v1"
    envelope["protected"] = (
        base64.urlsafe_b64encode(json.dumps(protected, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        .decode("ascii")
        .rstrip("=")
    )

    with pytest.raises(ValueError, match="exchange configuration version 2|suite"):
        decrypt_exchange_envelope_v2(envelope, sender.to_json(include_private=True))


def test_v2_exchange_rejects_missing_recipient_header():
    """Standard JWE recipients must carry their JOSE header object."""
    sender = generate_exchange_key_bundle("suite-pq-v1")
    recipient = generate_exchange_key_bundle("suite-pq-v1")
    envelope = build_exchange_envelope_v2(
        "header-test",
        b"hash-secret",
        sender,
        recipient,
        "2026-03-12T00:00:00Z",
        "exchange-header",
    )
    envelope["recipients"][0].pop("header")

    with pytest.raises(ValueError, match="header"):
        decrypt_exchange_envelope_v2(envelope, sender.to_json(include_private=True))


def test_key_bundle_rejects_public_fingerprint_mismatch():
    """A bundle must not accept a public key under another key's fingerprint."""
    bundle = generate_exchange_key_bundle("suite-pq-v1").to_mapping(include_private=True)
    bundle["keys"]["mlkem"]["fingerprint"] = "00:" * 31 + "00"

    with pytest.raises(KeyBundleError, match="fingerprint"):
        ExchangeKeyBundle.from_mapping(bundle, require_private=True)


def test_key_bundle_requires_private_material():
    """Private-key consumers reject public-only bundles."""
    bundle = generate_exchange_key_bundle("suite-pq-v1")

    with pytest.raises(KeyBundleError, match="private material"):
        ExchangeKeyBundle.from_mapping(bundle.to_mapping(), require_private=True)


def test_key_bundle_rejects_unsupported_version():
    """Bundles with an unsupported version fail structural validation."""
    bundle = generate_exchange_key_bundle("suite-pq-v1").to_mapping(include_private=True)
    bundle["version"] = 2

    with pytest.raises(KeyBundleError, match="Unsupported or missing"):
        ExchangeKeyBundle.from_mapping(bundle, require_private=True)


def test_key_bundle_rejects_missing_keys_object():
    """Bundles without a keys object fail structural validation."""
    bundle = generate_exchange_key_bundle("suite-pq-v1").to_mapping(include_private=True)
    del bundle["keys"]

    with pytest.raises(KeyBundleError, match="missing its keys object"):
        ExchangeKeyBundle.from_mapping(bundle, require_private=True)


def test_key_bundle_rejects_non_v2_suite():
    """Version-1 suites cannot generate version-2 key bundles."""
    with pytest.raises(KeyBundleError, match="does not require a version-2 key bundle"):
        generate_exchange_key_bundle("suite-sha256-v1")
