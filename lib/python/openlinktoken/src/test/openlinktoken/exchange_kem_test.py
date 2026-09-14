# SPDX-License-Identifier: MIT

from copy import deepcopy

import pytest

from openlinktoken.exchange_config import (
    derive_transport_encryption_key,
    load_exchange_config,
    resolve_loaded_exchange_config,
)
from openlinktoken.exchange_kem import build_exchange_envelope_v2, decrypt_exchange_envelope_v2
from openlinktoken.exchange_key_bundle import ExchangeKeyBundle, KeyBundleError, generate_exchange_key_bundle


@pytest.mark.parametrize("suite_id", ["suite-pq-v1", "suite-pq-shake-v1", "suite-pq-hybrid-v1"])
def test_v2_exchange_round_trips_for_both_participants(suite_id):
    """Pure and hybrid recipients recover the same payload and transport key."""
    sender = generate_exchange_key_bundle(suite_id)
    recipient = generate_exchange_key_bundle(suite_id)
    envelope = build_exchange_envelope_v2(
        exchange_name="pqc-exchange",
        hashing_secret=b"shared-hashing-secret",
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
    assert len(sender_transport_key) == 32
    assert envelope["version"] == 2
    assert envelope["cryptoSuite"] == suite_id


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

    assert resolved.version == 2
    assert resolved.private_key_role == "sender"
    assert resolved.hashing_secret == b"hash-secret"
    assert derive_transport_encryption_key(resolved) == resolved.transport_encryption_key


def test_key_bundle_rejects_public_fingerprint_mismatch():
    """A bundle must not accept a public key under another key's fingerprint."""
    bundle = generate_exchange_key_bundle("suite-pq-v1").to_mapping(include_private=True)
    bundle["keys"]["mlkem"]["fingerprint"] = "00:" * 31 + "00"

    with pytest.raises(KeyBundleError, match="fingerprint"):
        ExchangeKeyBundle.from_mapping(bundle, require_private=True)


def test_v2_exchange_rejects_unknown_component_algorithm():
    """Unknown component algorithms fail closed instead of being ignored."""
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
    tampered["recipients"][0]["keyManagement"]["components"][0]["algorithm"] = "UNKNOWN-KEM"

    with pytest.raises(ValueError, match="component ordering"):
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


def test_v2_exchange_rejects_non_v2_envelope():
    """Version-1 envelopes cannot be decrypted through the version-2 API."""
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
    envelope["version"] = 1

    with pytest.raises(ValueError, match="not version 2"):
        decrypt_exchange_envelope_v2(envelope, sender.to_json(include_private=True))


def test_v2_exchange_rejects_v1_crypto_suite():
    """Version-1 crypto suites cannot be used in version-2 envelopes."""
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
    envelope["cryptoSuite"] = "suite-sha256-v1"

    with pytest.raises(ValueError, match="not valid for exchange configuration version 2"):
        decrypt_exchange_envelope_v2(envelope, sender.to_json(include_private=True))


def test_v2_exchange_rejects_missing_key_management():
    """Recipients without key-management data are rejected before unwrapping."""
    sender = generate_exchange_key_bundle("suite-pq-v1")
    recipient = generate_exchange_key_bundle("suite-pq-v1")
    envelope = build_exchange_envelope_v2(
        "key-management-test",
        b"hash-secret",
        sender,
        recipient,
        "2026-03-12T00:00:00Z",
        "exchange-key-management",
    )
    envelope["recipients"][0]["keyManagement"] = None

    with pytest.raises(ValueError, match="missing keyManagement"):
        decrypt_exchange_envelope_v2(envelope, sender.to_json(include_private=True))


def test_v2_exchange_rejects_non_list_components():
    """Recipient key-management components must be represented as a list."""
    sender = generate_exchange_key_bundle("suite-pq-v1")
    recipient = generate_exchange_key_bundle("suite-pq-v1")
    envelope = build_exchange_envelope_v2(
        "components-test",
        b"hash-secret",
        sender,
        recipient,
        "2026-03-12T00:00:00Z",
        "exchange-components",
    )
    envelope["recipients"][0]["keyManagement"]["components"] = None

    with pytest.raises(ValueError, match="components must be a list"):
        decrypt_exchange_envelope_v2(envelope, sender.to_json(include_private=True))


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
    """Version-1 suites cannot be used to generate version-2 key bundles."""
    with pytest.raises(KeyBundleError, match="does not require a version-2 key bundle"):
        generate_exchange_key_bundle("suite-sha256-v1")
