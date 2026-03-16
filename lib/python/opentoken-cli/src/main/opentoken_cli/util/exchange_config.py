"""
Copyright (c) Truveta. All rights reserved.

CLI-facing wrappers around shared exchange-config helpers.
"""

from opentoken.exchange_config import (
    SUPPORTED_EXCHANGE_CONFIG_VERSIONS,
    TRANSPORT_KEY_INFO,
    LoadedExchangeConfig,
    ResolvedExchangeConfig,
    default_exchange_config_path,
    derive_transport_encryption_key,
    resolve_exchange_config_inputs,
)

__all__ = [
    "LoadedExchangeConfig",
    "ResolvedExchangeConfig",
    "SUPPORTED_EXCHANGE_CONFIG_VERSIONS",
    "TRANSPORT_KEY_INFO",
    "default_exchange_config_path",
    "derive_transport_encryption_key",
    "resolve_exchange_config",
]


def resolve_exchange_config(
    exchange_config_path: str | None,
    private_key_path: str | None = None,
    private_key_env: str | None = None,
) -> ResolvedExchangeConfig:
    """Resolve an exchange-config path plus CLI private-key options into shared exchange state."""
    if private_key_path and private_key_env:
        raise ValueError("Cannot combine --private-key and --private-key-env.")

    return resolve_exchange_config_inputs(
        exchange_config_path,
        private_key_path=private_key_path,
        private_key_env=private_key_env,
    )
