# SPDX-License-Identifier: MIT

import base64
import json
from copy import deepcopy

import pytest
from jwcrypto import jwe, jwk

from openlinktoken.crypto.crypto_suite import CryptoSuite
from openlinktoken.exchange_config import (
    derive_transport_encryption_key,
    load_exchange_config,
    resolve_loaded_exchange_config,
)
from openlinktoken.exchange_kem import (
    _decode,
    _parse_payload,
    _validate_payload,
    build_exchange_envelope_v2,
    decrypt_exchange_envelope_v2,
)
from openlinktoken.exchange_kem import (
    _decode_protected_header as decode_exchange_protected_header,
)
from openlinktoken.exchange_key_bundle import (
    ExchangeKeyBundle,
    KeyBundleError,
    generate_exchange_key_bundle,
    resolve_private_bundle_by_kid,
)
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


def test_v2_exchange_rejects_invalid_build_inputs():
    """The v2 facade validates suite, payload, and rotation settings before encryption."""
    sender = generate_exchange_key_bundle("suite-pq-v1")
    recipient = generate_exchange_key_bundle("suite-pq-hybrid-v1")
    with pytest.raises(ValueError, match="same crypto suite"):
        build_exchange_envelope_v2("name", b"secret", sender, recipient, "now", "id")

    v1_bundle = ExchangeKeyBundle(CryptoSuite.from_id("suite-sha256-v1"))
    with pytest.raises(ValueError, match="version 2"):
        build_exchange_envelope_v2("name", b"secret", v1_bundle, v1_bundle, "now", "id")

    recipient = generate_exchange_key_bundle("suite-pq-v1")
    invalid_inputs = (
        (("", b"secret", b"", 0, 0.05), "non-empty"),
        (("name", "secret", b"", 0, 0.05), "bytes"),
        (("name", b"secret", "not-bytes", 0, 0.05), "bytes"),
        (("name", b"secret", b"", -1, 0.05), "non-negative"),
        (("name", b"secret", b"", 0, 0), "positive"),
    )
    for (name, secret, rotation_iv, rotation_count, bin_width), message in invalid_inputs:
        with pytest.raises((TypeError, ValueError), match=message):
            build_exchange_envelope_v2(
                name,
                secret,
                generate_exchange_key_bundle("suite-pq-v1"),
                recipient,
                "now",
                "id",
                rotation_iv=rotation_iv,
                rotation_count=rotation_count,
                bin_width=bin_width,
            )


def test_v2_exchange_accepts_bundle_mapping_and_object_inputs():
    """Private bundles can be supplied as mappings or already parsed objects."""
    sender = generate_exchange_key_bundle("suite-pq-v1")
    recipient = generate_exchange_key_bundle("suite-pq-v1")
    envelope = build_exchange_envelope_v2("mapping-input", b"secret", sender, recipient, "now", "mapping-id")

    mapping_plaintext, _ = decrypt_exchange_envelope_v2(
        envelope,
        sender.to_mapping(include_private=True),
    )
    object_plaintext, _ = decrypt_exchange_envelope_v2(envelope, sender)

    assert mapping_plaintext == object_plaintext


def test_v2_exchange_payload_helpers_reject_malformed_values():
    """Payload and protected-header helpers reject malformed or inconsistent values."""
    sender = generate_exchange_key_bundle("suite-pq-v1")
    recipient = generate_exchange_key_bundle("suite-pq-v1")
    envelope = build_exchange_envelope_v2("payload-test", b"secret", sender, recipient, "now", "payload-id")
    protected = json.loads(base64.urlsafe_b64decode(envelope["protected"] + "=" * (-len(envelope["protected"]) % 4)))
    payload, _ = decrypt_exchange_envelope_v2(envelope, sender)
    payload_mapping = json.loads(payload)
    suite = CryptoSuite.from_id("suite-pq-v1")

    with pytest.raises(ValueError, match="not valid JSON"):
        _parse_payload(b"not-json")
    with pytest.raises(ValueError, match="JSON object"):
        _parse_payload(b"[]")
    with pytest.raises(ValueError, match="not valid JSON"):
        decode_exchange_protected_header(base64.urlsafe_b64encode(b"not-json").decode("ascii"))
    with pytest.raises(ValueError, match="JSON object"):
        decode_exchange_protected_header(base64.urlsafe_b64encode(b"[]").decode("ascii"))
    with pytest.raises(ValueError, match="non-empty"):
        _decode(None, "field")
    with pytest.raises(ValueError, match="not valid"):
        _decode("not base64!", "field")

    invalid_payloads = (
        ({"cryptoSuite": "suite-pq-hybrid-v1"}, "suite"),
        ({"exchangeId": "other-id"}, "exchangeId"),
        ({"senderKeyId": ""}, "senderKeyId"),
        ({"recipientKeyId": ""}, "recipientKeyId"),
        ({"senderKeyBundle": None}, "senderKeyBundle"),
        ({"recipientKeyBundle": None}, "recipientKeyBundle"),
    )
    for updates, message in invalid_payloads:
        candidate = dict(payload_mapping)
        candidate.update(updates)
        with pytest.raises(ValueError, match=message):
            _validate_payload(candidate, suite, protected)

    candidate = dict(payload_mapping)
    candidate["senderKeyBundle"] = recipient.to_mapping()
    with pytest.raises(ValueError, match="senderKeyBundle"):
        _validate_payload(candidate, suite, protected)


def test_key_bundle_rejects_malformed_sections():
    """Key bundles validate every encoded key section and key relationship."""
    pure = generate_exchange_key_bundle("suite-pq-v1").to_mapping(include_private=True)
    invalid_pure_sections = (
        ({"mlkem": None}, "requires an mlkem"),
        ({"mlkem": {**pure["keys"]["mlkem"], "algorithm": "wrong"}}, "algorithm"),
        ({"mlkem": {**pure["keys"]["mlkem"], "publicKey": "AA"}}, "publicKey must be"),
        (
            {"mlkem": {**pure["keys"]["mlkem"], "privateKeyEncoding": "pem"}},
            "privateKeyEncoding",
        ),
        ({"mlkem": {**pure["keys"]["mlkem"], "privateKey": "AA"}}, "privateKey must be"),
    )
    for keys, message in invalid_pure_sections:
        candidate = deepcopy(pure)
        candidate["keys"].update(keys)
        with pytest.raises(KeyBundleError, match=message):
            ExchangeKeyBundle.from_mapping(candidate, require_private=True)

    hybrid = generate_exchange_key_bundle("suite-pq-hybrid-v1").to_mapping(include_private=True)
    invalid_hybrid_sections = (
        ({"ec": None}, "requires an ec"),
        ({"ec": {**hybrid["keys"]["ec"], "algorithm": "wrong"}}, "algorithm"),
        ({"ec": {**hybrid["keys"]["ec"], "publicKeyEncoding": "der"}}, "publicKeyEncoding"),
        ({"ec": {**hybrid["keys"]["ec"], "publicKey": ""}}, "publicKey"),
        ({"ec": {**hybrid["keys"]["ec"], "publicKey": "not-pem"}}, "not valid PEM"),
        ({"ec": {**hybrid["keys"]["ec"], "privateKeyEncoding": "der"}}, "privateKeyEncoding"),
        ({"ec": {**hybrid["keys"]["ec"], "privateKey": ""}}, "privateKey"),
        ({"ec": {**hybrid["keys"]["ec"], "privateKey": "not-pem"}}, "not valid PEM"),
    )
    for keys, message in invalid_hybrid_sections:
        candidate = deepcopy(hybrid)
        candidate["keys"].update(keys)
        with pytest.raises(KeyBundleError, match=message):
            ExchangeKeyBundle.from_mapping(candidate, require_private=True)

    mismatched_private = deepcopy(hybrid)
    other_hybrid = generate_exchange_key_bundle("suite-pq-hybrid-v1").to_mapping(include_private=True)
    mismatched_private["keys"]["ec"]["privateKey"] = other_hybrid["keys"]["ec"]["privateKey"]
    with pytest.raises(KeyBundleError, match="does not match"):
        ExchangeKeyBundle.from_mapping(mismatched_private, require_private=True)


def test_key_bundle_rejects_invalid_json_kid_and_private_serialization():
    """JSON, key identifiers, and private serialization boundaries are validated."""
    bundle = generate_exchange_key_bundle("suite-pq-v1")
    mapping = bundle.to_mapping(include_private=True)

    with pytest.raises(KeyBundleError, match="not valid UTF-8 JSON"):
        ExchangeKeyBundle.from_json(b"not-json")
    with pytest.raises(KeyBundleError, match="JSON object"):
        ExchangeKeyBundle.from_json("[]")

    invalid_kid = deepcopy(mapping)
    invalid_kid["kid"] = "wrong"
    with pytest.raises(KeyBundleError, match="kid"):
        ExchangeKeyBundle.from_mapping(invalid_kid, require_private=True)

    with pytest.raises(KeyBundleError, match="private seed"):
        ExchangeKeyBundle(bundle.suite, mlkem_public_key=bundle.mlkem_public_key).to_mapping(include_private=True)

    hybrid = generate_exchange_key_bundle("suite-pq-hybrid-v1")
    with pytest.raises(KeyBundleError, match="EC private key"):
        ExchangeKeyBundle(
            hybrid.suite,
            mlkem_public_key=hybrid.mlkem_public_key,
            mlkem_private_seed=hybrid.mlkem_private_seed,
            ec_public_pem=hybrid.ec_public_pem,
        ).to_mapping(include_private=True)


def test_private_bundle_resolution_finds_matching_kid(tmp_path):
    """Private bundle discovery returns the matching bundle and rejects unknown IDs."""
    bundle = generate_exchange_key_bundle("suite-pq-v1")
    matching_path = tmp_path / "matching.private.bundle.json"
    matching_path.write_bytes(bundle.to_json(include_private=True))
    (tmp_path / "unrelated.private.bundle.json").write_bytes(
        generate_exchange_key_bundle("suite-pq-v1").to_json(include_private=True)
    )

    assert resolve_private_bundle_by_kid(tmp_path, bundle.kid) == matching_path.read_bytes()
    with pytest.raises(FileNotFoundError, match="No private key bundle"):
        resolve_private_bundle_by_kid(tmp_path, "sha256:missing")
