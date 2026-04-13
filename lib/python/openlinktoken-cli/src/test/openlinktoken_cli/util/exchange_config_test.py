# SPDX-License-Identifier: MIT

import importlib
from pathlib import Path
from unittest.mock import patch

import pytest

from openlinktoken.exchange_config import ResolvedExchangeConfig
from openlinktoken_cli.util import exchange_config as exchange_config_util


def test_legacy_cli_exchange_jwe_module_is_removed() -> None:
    """The CLI package must not re-expose shared exchange JWE helpers via a legacy shim."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("openlinktoken_cli.util.exchange_jwe")


def test_resolve_exchange_config_rejects_conflicting_cli_private_key_inputs() -> None:
    """CLI wrappers should keep the existing mutual-exclusion message for private-key flags."""
    with pytest.raises(ValueError, match="Cannot combine --private-key and --private-key-env."):
        exchange_config_util.resolve_exchange_config(
            "exchange.json",
            private_key_path="provided.private.pem",
            private_key_env="OPENTOKEN_PRIVATE_KEY",
        )


def test_resolve_exchange_config_delegates_to_shared_core_helper() -> None:
    """CLI wrappers should delegate exchange-config resolution to shared core helpers."""
    expected = ResolvedExchangeConfig(
        path=Path("exchange.json"),
        version=1,
        config={},
        payload={},
        private_key_pem=b"private-key",
        private_key_role="sender",
        hashing_secret=b"hashing-secret",
    )

    with patch(
        "openlinktoken_cli.util.exchange_config.resolve_exchange_config_inputs",
        return_value=expected,
    ) as resolve_exchange_config_inputs:
        resolved = exchange_config_util.resolve_exchange_config(
            "exchange.json",
            private_key_path="provided.private.pem",
        )

    assert resolved is expected
    resolve_exchange_config_inputs.assert_called_once_with(
        "exchange.json",
        private_key_path="provided.private.pem",
        private_key_env=None,
    )
