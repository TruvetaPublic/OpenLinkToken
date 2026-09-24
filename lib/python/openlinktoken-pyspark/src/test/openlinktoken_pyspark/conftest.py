# SPDX-License-Identifier: MIT
"""Shared crypto-suite exchange fixtures for PySpark bridge tests."""

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from openlinktoken.crypto.crypto_suite import CryptoSuite
from openlinktoken.ec_key_utils import generate_key_pair
from openlinktoken.exchange_jwe import build_exchange_envelope
from openlinktoken.exchange_kem import build_exchange_envelope_v2
from openlinktoken.exchange_key_bundle import generate_exchange_key_bundle

HASHING_SECRET = b"shared-hashing-secret-0123456789"


@dataclass(frozen=True)
class ExchangeConfigCase:
    """Exchange configuration and matching private key for one crypto suite.

    Args:
        crypto_suite: Suite used to build the exchange configuration.
        exchange_config_path: Path to the serialized exchange configuration.
        private_key_path: Path to the matching private-key material.
        private_key_value: PEM or key-bundle JSON text for resolving the exchange.

    Returns:
        An immutable ``ExchangeConfigCase`` containing the exchange and key inputs.
    """

    crypto_suite: CryptoSuite
    exchange_config_path: Path
    private_key_path: Path
    private_key_value: str


@pytest.fixture(scope="session", params=CryptoSuite.all(), ids=lambda suite: suite.suite_id)
def exchange_config_case(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
) -> ExchangeConfigCase:
    """Create a valid real exchange configuration for each registered suite.

    Args:
        request: Parameterized pytest request whose parameter is the current suite.
        tmp_path_factory: Factory for creating suite-specific temporary directories.

    Returns:
        Exchange configuration and matching private-key inputs for the requested suite.
    """
    suite = request.param
    fixture_dir = tmp_path_factory.mktemp(suite.suite_id)
    exchange_config_path = fixture_dir / "exchange.json"

    if suite.exchange_config_version == 1:
        sender_private_pem, sender_public_pem = generate_key_pair("P-256")
        _, recipient_public_pem = generate_key_pair("P-256")
        private_key_path = fixture_dir / "sender.private.pem"
        private_key_path.write_bytes(sender_private_pem)
        private_key_value = sender_private_pem.decode("utf-8")
        exchange_config = build_exchange_envelope(
            exchange_name="shared-exchange",
            hashing_secret=HASHING_SECRET,
            sender_public_pem=sender_public_pem,
            recipient_public_pem=recipient_public_pem,
            curve="P-256",
            created_at="2026-03-12T00:00:00Z",
            exchange_id=f"exchange-{suite.suite_id}",
            crypto_suite=suite,
        )
    else:
        sender_bundle = generate_exchange_key_bundle(suite.suite_id)
        recipient_bundle = generate_exchange_key_bundle(suite.suite_id)
        private_key_path = fixture_dir / "sender.private.bundle.json"
        private_key_value = sender_bundle.to_json(include_private=True).decode("utf-8")
        private_key_path.write_text(private_key_value, encoding="utf-8")
        exchange_config = build_exchange_envelope_v2(
            exchange_name="shared-exchange",
            hashing_secret=HASHING_SECRET,
            sender_bundle=sender_bundle,
            recipient_bundle=recipient_bundle,
            created_at="2026-03-12T00:00:00Z",
            exchange_id=f"exchange-{suite.suite_id}",
        )

    exchange_config_path.write_text(json.dumps(exchange_config), encoding="utf-8")
    return ExchangeConfigCase(suite, exchange_config_path, private_key_path, private_key_value)
