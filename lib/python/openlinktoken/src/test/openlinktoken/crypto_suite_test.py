# SPDX-License-Identifier: MIT

import pytest

from openlinktoken.crypto_suite import CryptoSuite, CryptoSuiteError


def test_registered_suites_have_expected_contracts():
    """Every public suite ID resolves to its exact algorithm contract."""
    assert [suite.suite_id for suite in CryptoSuite.all()] == [
        "suite-sha256-v1",
        "suite-sha3-v1",
        "suite-shake-v1",
        "suite-pq-v1",
        "suite-pq-hybrid-v1",
    ]

    assert CryptoSuite.from_id("suite-sha256-v1") == CryptoSuite(
        "suite-sha256-v1", "SHA-256", "HS256", "A256GCM", "ECDH", 1
    )
    assert CryptoSuite.from_id("suite-pq-hybrid-v1").exchange_key_agreement == "ECDH+ML-KEM-768"


def test_shake_suite_declares_fixed_output_and_kmac():
    """SHAKE suite records explicit output lengths for digest and MAC."""
    suite = CryptoSuite.from_id("suite-shake-v1")

    assert suite.token_digest_algorithm == "SHAKE256-256"
    assert suite.token_mac_algorithm == "KMAC256-256"
    assert suite.exchange_key_agreement == "ECDH"
    assert suite.exchange_config_version == 1


def test_default_suite_preserves_legacy_contract():
    """The default suite remains the existing SHA-256/HMAC-SHA256 ECDH profile."""
    suite = CryptoSuite.default()

    assert suite.token_digest_algorithm == "SHA-256"
    assert suite.token_mac_algorithm == "HS256"
    assert suite.token_content_encryption == "A256GCM"
    assert suite.exchange_key_agreement == "ECDH"
    assert suite.exchange_config_version == 1
    assert not suite.is_post_quantum


@pytest.mark.parametrize("suite_id", ["", "unknown", None])
def test_unknown_suite_ids_fail_closed(suite_id):
    """Unknown or malformed IDs must not silently fall back to the default."""
    with pytest.raises(CryptoSuiteError):
        CryptoSuite.from_id(suite_id)
