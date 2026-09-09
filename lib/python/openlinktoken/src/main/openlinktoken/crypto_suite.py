# SPDX-License-Identifier: MIT
"""Validated crypto-suite definitions shared by token and exchange consumers."""

from dataclasses import dataclass
from typing import ClassVar


class CryptoSuiteError(ValueError):
    """Raised when a crypto suite identifier or combination is not supported."""


@dataclass(frozen=True)
class CryptoSuite:
    """Immutable contract for token primitives and exchange key establishment."""

    suite_id: str
    token_digest_algorithm: str
    token_mac_algorithm: str
    token_content_encryption: str
    exchange_key_agreement: str
    exchange_config_version: int

    _REGISTRY: ClassVar[dict[str, "CryptoSuite"]]

    @classmethod
    def from_id(cls, suite_id: str) -> "CryptoSuite":
        """Resolve a registered suite identifier or raise a validation error."""
        if not isinstance(suite_id, str) or not suite_id.strip():
            raise CryptoSuiteError("Crypto suite ID must be a non-empty string.")

        try:
            return cls._REGISTRY[suite_id]
        except KeyError as error:
            supported = ", ".join(cls._REGISTRY)
            raise CryptoSuiteError(f"Unknown crypto suite '{suite_id}'. Supported suites: {supported}.") from error

    @classmethod
    def default(cls) -> "CryptoSuite":
        """Return the backward-compatible default suite."""
        return cls._REGISTRY["suite-sha256-v1"]

    @classmethod
    def all(cls) -> tuple["CryptoSuite", ...]:
        """Return all registered suites in stable identifier order."""
        return tuple(cls._REGISTRY.values())

    @property
    def is_post_quantum(self) -> bool:
        """Return whether the exchange agreement includes ML-KEM."""
        return "ML-KEM" in self.exchange_key_agreement

    def validate(self) -> "CryptoSuite":
        """Validate the suite's internal algorithm and version combination."""
        if self.token_content_encryption != "A256GCM":
            raise CryptoSuiteError(f"Unsupported token content encryption '{self.token_content_encryption}'.")
        if self.exchange_config_version == 1 and self.exchange_key_agreement != "ECDH":
            raise CryptoSuiteError("Exchange configuration version 1 only supports ECDH.")
        if self.exchange_config_version == 2 and self.exchange_key_agreement == "ECDH":
            raise CryptoSuiteError("Exchange configuration version 2 requires a non-ECDH key agreement.")
        if self.exchange_config_version not in {1, 2}:
            raise CryptoSuiteError(f"Unsupported exchange configuration version '{self.exchange_config_version}'.")
        return self


CryptoSuite._REGISTRY = {
    suite.suite_id: suite
    for suite in (
        CryptoSuite(
            suite_id="suite-sha256-v1",
            token_digest_algorithm="SHA-256",
            token_mac_algorithm="HS256",
            token_content_encryption="A256GCM",
            exchange_key_agreement="ECDH",
            exchange_config_version=1,
        ),
        CryptoSuite(
            suite_id="suite-sha3-v1",
            token_digest_algorithm="SHA3-256",
            token_mac_algorithm="HS3-256",
            token_content_encryption="A256GCM",
            exchange_key_agreement="ECDH",
            exchange_config_version=1,
        ),
        CryptoSuite(
            suite_id="suite-pq-shake-v1",
            token_digest_algorithm="SHAKE256-256",
            token_mac_algorithm="KMAC256-256",
            token_content_encryption="A256GCM",
            exchange_key_agreement="ML-KEM-768",
            exchange_config_version=2,
        ),
        CryptoSuite(
            suite_id="suite-pq-v1",
            token_digest_algorithm="SHA3-256",
            token_mac_algorithm="HS3-256",
            token_content_encryption="A256GCM",
            exchange_key_agreement="ML-KEM-768",
            exchange_config_version=2,
        ),
        CryptoSuite(
            suite_id="suite-pq-hybrid-v1",
            token_digest_algorithm="SHA3-256",
            token_mac_algorithm="HS3-256",
            token_content_encryption="A256GCM",
            exchange_key_agreement="ECDH+ML-KEM-768",
            exchange_config_version=2,
        ),
    )
}

for _suite in CryptoSuite._REGISTRY.values():
    _suite.validate()
