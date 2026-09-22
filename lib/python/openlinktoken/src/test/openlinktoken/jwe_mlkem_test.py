# SPDX-License-Identifier: MIT

import base64
import json

import pytest
from jwcrypto import jwa

from openlinktoken.exchange_key_bundle import generate_exchange_key_bundle
from openlinktoken.jwe_mlkem import (
    AES_KW_WRAPPED_CEK_SIZE,
    EXCHANGE_V2_CONTENT_TYPE,
    EXCHANGE_V2_ENCRYPTION,
    EXCHANGE_V2_TYPE,
    EXCHANGE_V2_VERSION,
    HYBRID_KEM_ALGORITHM,
    MLKEM_CIPHERTEXT_SIZE,
    PURE_KEM_ALGORITHM,
    OpenLinkTokenJWE,
    _derive_token_transport_key,
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
