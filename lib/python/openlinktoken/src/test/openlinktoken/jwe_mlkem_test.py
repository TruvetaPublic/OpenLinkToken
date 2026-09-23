# SPDX-License-Identifier: MIT

import base64
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from jwcrypto import jwa
from jwcrypto.common import InvalidJWEOperation

from openlinktoken import jwe_mlkem
from openlinktoken.exchange_key_bundle import generate_exchange_key_bundle
from openlinktoken.jwe_mlkem import (
    AES_KW_WRAPPED_CEK_SIZE,
    CEK_SIZE,
    EXCHANGE_V2_CONTENT_TYPE,
    EXCHANGE_V2_ENCRYPTION,
    EXCHANGE_V2_TYPE,
    EXCHANGE_V2_VERSION,
    HYBRID_KEM_ALGORITHM,
    MLKEM_CIPHERTEXT_SIZE,
    PURE_KEM_ALGORITHM,
    RECIPIENT_ENCRYPTED_KEY_SIZE,
    OpenLinkTokenJWE,
    _algorithm_for_suite,
    _decode_base64url,
    _derive_token_transport_key,
    _load_ec_private_key,
    _load_ec_public_key,
    _load_ephemeral_public_key,
    _MLKEMKeyManagement,
    _validate_epk,
    _validate_header_context,
    _validate_key_and_headers,
    _validate_protected_header,
    _validate_recipient,
    build_v2_jwe,
    decrypt_v2_jwe,
)


def _protected_header(suite_id: str) -> dict[str, object]:
    """Build the protected header used by focused adapter tests."""
    return {
        "typ": EXCHANGE_V2_TYPE,
        "cty": EXCHANGE_V2_CONTENT_TYPE,
        "enc": EXCHANGE_V2_ENCRYPTION,
        "version": EXCHANGE_V2_VERSION,
        "cryptoSuite": suite_id,
        "exchangeId": "exchange-adapter-test",
    }


def _decode(value: str) -> bytes:
    """Decode unpadded base64url test values."""
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def test_v2_token_transport_key_uses_the_documented_hkdf_contract():
    """The v2 transport key uses the CEK, exchange ID salt, and domain-separated info."""
    cek = bytes(range(32))

    transport_key = _derive_token_transport_key(cek, "exchange-id-a1")

    assert transport_key.hex() == "28cf4377e92ac7219f4454c73192e4bd6ca29076a648be934abb74f7350a7d6a"
    assert transport_key == _derive_token_transport_key(cek, "exchange-id-a1")
    assert transport_key != _derive_token_transport_key(cek, "exchange-id-a2")


@pytest.mark.parametrize(
    ("suite_id", "expected_algorithm", "has_epk"),
    [
        ("suite-pq-v1", PURE_KEM_ALGORITHM, False),
        ("suite-pq-shake-v1", PURE_KEM_ALGORITHM, False),
        ("suite-pq-hybrid-v1", HYBRID_KEM_ALGORITHM, True),
    ],
)
def test_build_v2_jwe_uses_standard_general_json_shape(suite_id, expected_algorithm, has_epk):
    """Every v2 suite serializes as a standard two-recipient JWE JSON object."""
    sender = generate_exchange_key_bundle(suite_id)
    recipient = generate_exchange_key_bundle(suite_id)
    envelope = build_v2_jwe(
        b'{"exchangeId":"exchange-adapter-test"}',
        _protected_header(suite_id),
        [sender, recipient],
    )

    assert set(envelope) == {"protected", "recipients", "iv", "ciphertext", "tag"}
    assert len(envelope["recipients"]) == 2
    protected = json.loads(_decode(envelope["protected"]))
    assert protected == _protected_header(suite_id)

    for entry in envelope["recipients"]:
        assert set(entry) == {"header", "encrypted_key"}
        assert "keyManagement" not in entry
        assert "wrappedContentKey" not in entry
        assert entry["header"]["alg"] == expected_algorithm
        assert len(_decode(entry["encrypted_key"])) == MLKEM_CIPHERTEXT_SIZE + AES_KW_WRAPPED_CEK_SIZE
        assert ("epk" in entry["header"]) is has_epk


@pytest.mark.parametrize("suite_id", ["suite-pq-v1", "suite-pq-shake-v1", "suite-pq-hybrid-v1"])
def test_v2_jwe_round_trip_derives_transport_key_separately_from_cek(suite_id):
    """Both recipients recover the plaintext and a CEK-derived transport key."""
    sender = generate_exchange_key_bundle(suite_id)
    recipient = generate_exchange_key_bundle(suite_id)
    envelope = build_v2_jwe(b"adapter-plaintext", _protected_header(suite_id), [sender, recipient])

    sender_plaintext, sender_transport_key = decrypt_v2_jwe(envelope, sender)
    recipient_plaintext, recipient_transport_key = decrypt_v2_jwe(envelope, recipient)

    assert sender_plaintext == b"adapter-plaintext"
    assert recipient_plaintext == sender_plaintext
    assert sender_transport_key == recipient_transport_key
    assert len(sender_transport_key) == 32

    test_only_decryptor = OpenLinkTokenJWE(algs=[PURE_KEM_ALGORITHM, HYBRID_KEM_ALGORITHM, EXCHANGE_V2_ENCRYPTION])
    test_only_decryptor.deserialize(json.dumps(envelope))
    test_only_decryptor.decrypt(sender)
    assert test_only_decryptor.cek is not None
    assert sender_transport_key != test_only_decryptor.cek


def test_custom_handlers_do_not_mutate_jwcrypto_registry():
    """The adapter keeps custom algorithms local to each JWE object."""
    registry_before = dict(jwa.JWA.algorithms_registry)

    sender = generate_exchange_key_bundle("suite-pq-v1")
    recipient = generate_exchange_key_bundle("suite-pq-v1")
    build_v2_jwe(b"registry-test", _protected_header("suite-pq-v1"), [sender, recipient])

    assert jwa.JWA.algorithms_registry == registry_before


def test_custom_handler_dispatch_respects_allowed_algorithms():
    """Custom key-management handlers are dispatched per JWE instance."""
    standard_algorithm = "RSA-OAEP-256"
    token = OpenLinkTokenJWE(algs=[PURE_KEM_ALGORITHM, standard_algorithm])
    assert token._jwa_keymgmt(PURE_KEM_ALGORITHM).algorithm == PURE_KEM_ALGORITHM
    assert token._jwa_keymgmt(standard_algorithm) is not None

    with pytest.raises(InvalidJWEOperation, match="not allowed"):
        token._jwa_keymgmt(HYBRID_KEM_ALGORITHM)


@pytest.mark.parametrize(
    ("cek", "exchange_id", "exception", "message"),
    [
        ("not-bytes", "exchange-id", TypeError, "CEK must be bytes"),
        (b"x" * (CEK_SIZE - 1), "exchange-id", ValueError, "CEK must be 32 bytes"),
        (b"x" * CEK_SIZE, "", ValueError, "exchange ID"),
    ],
)
def test_transport_key_derivation_rejects_invalid_inputs(cek, exchange_id, exception, message):
    """Transport-key derivation validates CEK and exchange identity inputs."""
    with pytest.raises(exception, match=message):
        _derive_token_transport_key(cek, exchange_id)


def test_key_management_validates_sizes_and_wrap_errors(monkeypatch):
    """The custom key-management adapter rejects malformed CEKs and wrapped keys."""
    sender = generate_exchange_key_bundle("suite-pq-v1")
    headers = {
        **_protected_header("suite-pq-v1"),
        "alg": PURE_KEM_ALGORITHM,
        "kid": sender.kid,
    }
    handler = _MLKEMKeyManagement(PURE_KEM_ALGORITHM)

    wrapped = handler.wrap(sender, CEK_SIZE * 8, None, headers)
    assert len(wrapped["cek"]) == CEK_SIZE
    assert len(wrapped["ek"]) == RECIPIENT_ENCRYPTED_KEY_SIZE

    with pytest.raises(ValueError, match="256-bit CEK"):
        handler.wrap(sender, 128, b"x" * CEK_SIZE, headers)
    with pytest.raises(ValueError, match="CEK must be 32 bytes"):
        handler.wrap(sender, CEK_SIZE * 8, b"x" * (CEK_SIZE - 1), headers)
    with pytest.raises(ValueError, match="256-bit CEK"):
        handler.unwrap(sender, 128, wrapped["ek"], headers)
    with pytest.raises(ValueError, match="encrypted_key"):
        handler.unwrap(sender, CEK_SIZE * 8, b"x", headers)

    monkeypatch.setattr(jwe_mlkem, "aes_key_wrap", lambda *_args: (_ for _ in ()).throw(ValueError("wrap failed")))
    with pytest.raises(ValueError, match="Failed to wrap"):
        handler.wrap(sender, CEK_SIZE * 8, b"x" * CEK_SIZE, headers)

    monkeypatch.setattr(
        jwe_mlkem,
        "aes_key_unwrap",
        lambda *_args: (_ for _ in ()).throw(ValueError("unwrap failed")),
    )
    with pytest.raises(ValueError, match="Failed to unwrap"):
        handler.unwrap(sender, CEK_SIZE * 8, wrapped["ek"], headers)


def test_protected_header_validation_rejects_invalid_context():
    """Protected headers must contain only the authenticated v2 context."""
    valid = _protected_header("suite-pq-v1")
    invalid_headers = (
        (None, "JSON object"),
        ({}, "missing fields"),
        ({**valid, "typ": "wrong"}, "typ"),
        ({**valid, "cty": "wrong"}, "cty"),
        ({**valid, "enc": "A128GCM"}, "A256GCM"),
        ({**valid, "version": 1}, "version 2"),
        ({**valid, "cryptoSuite": 1}, "cryptoSuite must be a string"),
        ({**valid, "exchangeId": ""}, "exchangeId"),
        ({**valid, "alg": PURE_KEM_ALGORITHM}, "recipient-specific"),
    )
    for header, message in invalid_headers:
        with pytest.raises(ValueError, match=message):
            _validate_protected_header(header)


def test_recipient_and_ephemeral_key_validation_rejects_invalid_members():
    """Recipient and hybrid ephemeral-key structures are strictly validated."""
    sender = generate_exchange_key_bundle("suite-pq-v1")
    envelope = build_v2_jwe(
        b"validation", _protected_header("suite-pq-v1"), [sender, generate_exchange_key_bundle("suite-pq-v1")]
    )
    valid_recipient = envelope["recipients"][0]
    algorithm = PURE_KEM_ALGORITHM

    invalid_recipients = (
        (None, "header and encrypted_key"),
        ({"header": None, "encrypted_key": valid_recipient["encrypted_key"]}, "header"),
        (
            {"header": {"alg": "wrong", "kid": sender.kid}, "encrypted_key": valid_recipient["encrypted_key"]},
            "algorithm",
        ),
        ({"header": {"alg": algorithm}, "encrypted_key": valid_recipient["encrypted_key"]}, "kid"),
        ({"header": {"alg": algorithm, "kid": sender.kid}, "encrypted_key": "!"}, "not valid"),
        ({"header": {"alg": algorithm, "kid": sender.kid}, "encrypted_key": _encode(b"x")}, "decode"),
    )
    for recipient, message in invalid_recipients:
        with pytest.raises(ValueError, match=message):
            _validate_recipient(recipient, algorithm)

    hybrid = {
        "kty": "EC",
        "crv": "P-256",
        "x": _encode(b"x" * 32),
        "y": _encode(b"y" * 32),
    }
    _validate_epk(hybrid)
    with pytest.raises(ValueError, match="P-256 epk"):
        _validate_epk(None)
    with pytest.raises(ValueError, match="EC JWK"):
        _validate_epk({**hybrid, "crv": "P-384"})
    with pytest.raises(ValueError, match="coordinates"):
        _validate_epk({**hybrid, "x": _encode(b"x")})
    with pytest.raises(ValueError, match="private"):
        _validate_epk({**hybrid, "d": _encode(b"d" * 32)})


def test_key_and_curve_helpers_reject_invalid_material():
    """Key-management helpers reject wrong suites, curves, and malformed keys."""
    sender = generate_exchange_key_bundle("suite-pq-v1")
    headers = {
        **_protected_header("suite-pq-v1"),
        "alg": PURE_KEM_ALGORITHM,
        "kid": sender.kid,
    }

    with pytest.raises(ValueError, match="exchange configuration version 2"):
        _algorithm_for_suite(jwe_mlkem.CryptoSuite.from_id("suite-sha256-v1"))
    with pytest.raises(ValueError, match="protected cryptoSuite"):
        _validate_header_context({**headers, "cryptoSuite": ""}, PURE_KEM_ALGORITHM)
    with pytest.raises(ValueError, match="ExchangeKeyBundle"):
        _validate_key_and_headers(object(), headers, PURE_KEM_ALGORITHM, require_private=False)
    with pytest.raises(ValueError, match="kid"):
        _validate_key_and_headers(sender, {**headers, "kid": "wrong"}, PURE_KEM_ALGORITHM, require_private=False)
    with pytest.raises(ValueError, match="base64url"):
        _decode_base64url("!", "field")
    with pytest.raises(ValueError, match="not a valid P-256"):
        _load_ephemeral_public_key({**_valid_epk(), "x": _encode(b"\xff" * 32)})

    p384 = ec.generate_private_key(ec.SECP384R1())
    p384_public = p384.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    p384_private = p384.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    with pytest.raises(ValueError, match="P-256"):
        _load_ec_public_key(p384_public)
    with pytest.raises(ValueError, match="P-256"):
        _load_ec_private_key(p384_private)
    with pytest.raises(ValueError, match="missing"):
        _load_ec_public_key(None)
    with pytest.raises(ValueError, match="invalid"):
        _load_ec_private_key(b"not-a-key")


def _encode(value: bytes) -> str:
    """Encode bytes as unpadded base64url test data."""
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _valid_epk() -> dict[str, str]:
    """Return a syntactically valid but intentionally replaceable P-256 JWK."""
    return {
        "kty": "EC",
        "crv": "P-256",
        "x": _encode(b"x" * 32),
        "y": _encode(b"y" * 32),
    }
