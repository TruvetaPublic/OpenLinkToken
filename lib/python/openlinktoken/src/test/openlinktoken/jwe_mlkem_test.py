# SPDX-License-Identifier: MIT

import base64
import json

import pytest
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
    MLKEM_CIPHERTEXT_SIZE,
    PURE_KEM_ALGORITHM,
    RECIPIENT_ENCRYPTED_KEY_SIZE,
    OpenLinkTokenJWE,
    _algorithm_for_suite,
    _decode_base64url,
    _derive_token_transport_key,
    _MLKEMKeyManagement,
    _validate_header_context,
    _validate_key_and_headers,
    _validate_protected_header,
    _validate_recipient,
    build_v2_jwe,
    decrypt_v2_jwe,
)


def _protected_header(suite_id: str) -> dict[str, object]:
    """Build the protected header used by adapter tests.

    Args:
        suite_id: Registered version-2 crypto-suite identifier.

    Returns:
        A protected-header mapping with the required version-2 fields.
    """
    return {
        "typ": EXCHANGE_V2_TYPE,
        "cty": EXCHANGE_V2_CONTENT_TYPE,
        "enc": EXCHANGE_V2_ENCRYPTION,
        "version": EXCHANGE_V2_VERSION,
        "cryptoSuite": suite_id,
        "exchangeId": "exchange-adapter-test",
    }


def _decode(value: str) -> bytes:
    """Decode unpadded base64url test values.

    Args:
        value: Base64url-encoded test value.

    Returns:
        The decoded bytes.
    """
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def test_v2_token_transport_key_uses_the_documented_hkdf_contract():
    """The v2 transport key uses the documented HKDF inputs.

    Args:
        None.

    Returns:
        None.
    """
    cek = bytes(range(32))

    transport_key = _derive_token_transport_key(cek, "exchange-id-a1")

    assert transport_key.hex() == "28cf4377e92ac7219f4454c73192e4bd6ca29076a648be934abb74f7350a7d6a"
    assert transport_key == _derive_token_transport_key(cek, "exchange-id-a1")
    assert transport_key != _derive_token_transport_key(cek, "exchange-id-a2")


@pytest.mark.parametrize(
    "suite_id",
    ["mlkem768-sha3-256", "mlkem768-shake256"],
)
def test_build_v2_jwe_uses_standard_general_json_shape(suite_id):
    """Every v2 suite serializes as a standard two-recipient JWE JSON object.

    Args:
        suite_id: Parameterized version-2 crypto-suite identifier.

    Returns:
        None.
    """
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
        assert entry["header"]["alg"] == PURE_KEM_ALGORITHM
        assert len(_decode(entry["encrypted_key"])) == MLKEM_CIPHERTEXT_SIZE + AES_KW_WRAPPED_CEK_SIZE
        assert "epk" not in entry["header"]


@pytest.mark.parametrize("suite_id", ["mlkem768-sha3-256", "mlkem768-shake256"])
def test_v2_jwe_round_trip_derives_transport_key_separately_from_cek(suite_id):
    """Both recipients recover the plaintext and a CEK-derived transport key.

    Args:
        suite_id: Parameterized version-2 crypto-suite identifier.

    Returns:
        None.
    """
    sender = generate_exchange_key_bundle(suite_id)
    recipient = generate_exchange_key_bundle(suite_id)
    envelope = build_v2_jwe(b"adapter-plaintext", _protected_header(suite_id), [sender, recipient])

    sender_plaintext, sender_transport_key = decrypt_v2_jwe(envelope, sender)
    recipient_plaintext, recipient_transport_key = decrypt_v2_jwe(envelope, recipient)

    assert sender_plaintext == b"adapter-plaintext"
    assert recipient_plaintext == sender_plaintext
    assert sender_transport_key == recipient_transport_key
    assert len(sender_transport_key) == 32

    test_only_decryptor = OpenLinkTokenJWE(algs=[PURE_KEM_ALGORITHM, EXCHANGE_V2_ENCRYPTION])
    test_only_decryptor.deserialize(json.dumps(envelope))
    test_only_decryptor.decrypt(sender)
    assert test_only_decryptor.cek is not None
    assert sender_transport_key != test_only_decryptor.cek


def test_custom_handlers_do_not_mutate_jwcrypto_registry():
    """The adapter keeps custom algorithms local to each JWE object.

    Args:
        None.

    Returns:
        None.
    """
    registry_before = dict(jwa.JWA.algorithms_registry)

    sender = generate_exchange_key_bundle("mlkem768-sha3-256")
    recipient = generate_exchange_key_bundle("mlkem768-sha3-256")
    build_v2_jwe(b"registry-test", _protected_header("mlkem768-sha3-256"), [sender, recipient])

    assert jwa.JWA.algorithms_registry == registry_before


def test_custom_handler_dispatch_respects_allowed_algorithms():
    """Custom key-management handlers are dispatched per JWE instance.

    Args:
        None.

    Returns:
        None.
    """
    standard_algorithm = "RSA-OAEP-256"
    token = OpenLinkTokenJWE(algs=[PURE_KEM_ALGORITHM, standard_algorithm])
    assert token._jwa_keymgmt(PURE_KEM_ALGORITHM).algorithm == PURE_KEM_ALGORITHM
    assert token._jwa_keymgmt(standard_algorithm) is not None

    with pytest.raises(InvalidJWEOperation, match="not allowed"):
        OpenLinkTokenJWE(algs=[standard_algorithm])._jwa_keymgmt(PURE_KEM_ALGORITHM)


@pytest.mark.parametrize(
    ("cek", "exchange_id", "exception", "message"),
    [
        ("not-bytes", "exchange-id", TypeError, "CEK must be bytes"),
        (b"x" * (CEK_SIZE - 1), "exchange-id", ValueError, "CEK must be 32 bytes"),
        (b"x" * CEK_SIZE, "", ValueError, "exchange ID"),
    ],
)
def test_transport_key_derivation_rejects_invalid_inputs(cek, exchange_id, exception, message):
    """Transport-key derivation validates its CEK and exchange identity inputs.

    Args:
        cek: Parameterized invalid content-encryption-key value.
        exchange_id: Parameterized invalid exchange identifier.
        exception: Expected exception class.
        message: Expected error-message fragment.

    Returns:
        None.
    """
    with pytest.raises(exception, match=message):
        _derive_token_transport_key(cek, exchange_id)


def test_key_management_validates_sizes_and_wrap_errors(monkeypatch):
    """The key-management adapter rejects malformed CEKs and wrapped keys.

    Args:
        monkeypatch: Pytest fixture used to replace key-wrap and unwrap callables
            with callbacks that accept arbitrary positional arguments and raise
            ``ValueError`` to exercise their error handling.

    Returns:
        None.
    """
    sender = generate_exchange_key_bundle("mlkem768-sha3-256")
    headers = {
        **_protected_header("mlkem768-sha3-256"),
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
    """Protected headers must contain the required authenticated v2 context.

    Args:
        None.

    Returns:
        None.
    """
    valid = _protected_header("mlkem768-sha3-256")
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


def test_recipient_validation_rejects_invalid_members():
    """Recipients reject malformed fields and unsupported ECDH material.

    Args:
        None.

    Returns:
        None.
    """
    sender = generate_exchange_key_bundle("mlkem768-sha3-256")
    envelope = build_v2_jwe(
        b"validation",
        _protected_header("mlkem768-sha3-256"),
        [sender, generate_exchange_key_bundle("mlkem768-sha3-256")],
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
        (
            {"header": {**valid_recipient["header"], "epk": {}}, "encrypted_key": valid_recipient["encrypted_key"]},
            "must not contain epk",
        ),
        (
            {
                "header": {**valid_recipient["header"], "alg": "ECDH-ES+ML-KEM-768"},
                "encrypted_key": valid_recipient["encrypted_key"],
            },
            "algorithm",
        ),
    )
    for recipient, message in invalid_recipients:
        with pytest.raises(ValueError, match=message):
            _validate_recipient(recipient, algorithm)


def test_key_helpers_reject_invalid_material():
    """Key-management helpers reject wrong suites and malformed keys.

    Args:
        None.

    Returns:
        None.
    """
    sender = generate_exchange_key_bundle("mlkem768-sha3-256")
    headers = {
        **_protected_header("mlkem768-sha3-256"),
        "alg": PURE_KEM_ALGORITHM,
        "kid": sender.kid,
    }

    with pytest.raises(ValueError, match="exchange configuration version 2"):
        _algorithm_for_suite(jwe_mlkem.CryptoSuite.from_id("ecdh-sha256"))
    with pytest.raises(ValueError, match="protected cryptoSuite"):
        _validate_header_context({**headers, "cryptoSuite": ""}, PURE_KEM_ALGORITHM)
    with pytest.raises(ValueError, match="ExchangeKeyBundle"):
        _validate_key_and_headers(object(), headers, PURE_KEM_ALGORITHM, require_private=False)
    with pytest.raises(ValueError, match="kid"):
        _validate_key_and_headers(sender, {**headers, "kid": "wrong"}, PURE_KEM_ALGORITHM, require_private=False)
    with pytest.raises(ValueError, match="base64url"):
        _decode_base64url("!", "field")


def _encode(value: bytes) -> str:
    """Encode bytes as unpadded base64url test data.

    Args:
        value: Bytes to encode.

    Returns:
        Base64url text without padding.
    """
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def test_v2_jwe_rejects_tampered_recipient_header_or_suite():
    """Altering a recipient kid/alg or the protected cryptoSuite must fail decryption.

    Args:
        None.

    Returns:
        None.
    """
    import copy

    suite_id = "mlkem768-sha3-256"
    sender = generate_exchange_key_bundle(suite_id)
    recipient = generate_exchange_key_bundle(suite_id)
    envelope = build_v2_jwe(b"payload", _protected_header(suite_id), [sender, recipient])

    bad_alg = copy.deepcopy(envelope)
    for entry in bad_alg["recipients"]:
        entry["header"]["alg"] = "ECDH-ES+A256KW"
    with pytest.raises(Exception):
        decrypt_v2_jwe(bad_alg, sender)

    bad_kid = copy.deepcopy(envelope)
    for entry in bad_kid["recipients"]:
        entry["header"]["kid"] = entry["header"]["kid"] + "x"
    with pytest.raises(Exception):
        decrypt_v2_jwe(bad_kid, sender)

    protected = json.loads(_decode(envelope["protected"]))
    protected["cryptoSuite"] = "mlkem768-shake256"
    bad_suite = copy.deepcopy(envelope)
    bad_suite["protected"] = base64.urlsafe_b64encode(json.dumps(protected).encode()).rstrip(b"=").decode()
    with pytest.raises(Exception):
        decrypt_v2_jwe(bad_suite, sender)


def test_wipe_zeroes_mutable_buffer():
    """The best-effort wipe helper clears a mutable secret buffer.

    Args:
        None.

    Returns:
        None.
    """
    buffer = bytearray(b"secret-key-material")

    jwe_mlkem._wipe(buffer)

    assert buffer == bytearray(len(b"secret-key-material"))
