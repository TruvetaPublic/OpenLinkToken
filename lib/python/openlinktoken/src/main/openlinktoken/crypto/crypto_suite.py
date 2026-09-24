# SPDX-License-Identifier: MIT
"""Validated crypto-suite definitions shared by token and exchange consumers."""

from dataclasses import dataclass
from typing import ClassVar


class CryptoSuiteError(ValueError):
    """Raised when a crypto suite identifier or combination is not supported."""


@dataclass(frozen=True)
class CryptoSuite:
    """Immutable contract for token primitives and exchange key establishment."""

    TOKEN_DIGEST_SHA256: ClassVar[str] = "SHA-256"
    TOKEN_DIGEST_SHA3_256: ClassVar[str] = "SHA3-256"
    TOKEN_DIGEST_SHAKE256_256: ClassVar[str] = "SHAKE256-256"
    TOKEN_MAC_HS256: ClassVar[str] = "HS256"
    TOKEN_MAC_HS3_256: ClassVar[str] = "HS3-256"
    TOKEN_MAC_KMAC256_256: ClassVar[str] = "KMAC256-256"
    TOKEN_MAC_KMAC256_PREFIX: ClassVar[str] = "KMAC256"
    TOKEN_CONTENT_ENCRYPTION_A256GCM: ClassVar[str] = "A256GCM"
    EXCHANGE_KEY_AGREEMENT_ECDH: ClassVar[str] = "ECDH"
    EXCHANGE_KEY_AGREEMENT_MLKEM768: ClassVar[str] = "ML-KEM-768"
    EXCHANGE_KEY_AGREEMENT_ECDH_MLKEM768: ClassVar[str] = "ECDH+ML-KEM-768"
    EXCHANGE_KEY_AGREEMENT_MLKEM_PREFIX: ClassVar[str] = "ML-KEM"

    suite_id: str
    token_digest_algorithm: str
    token_mac_algorithm: str
    token_content_encryption: str
    exchange_key_agreement: str
    exchange_config_version: int

    SUITE_SHA256_V1: ClassVar["CryptoSuite"]
    SUITE_SHA3_V1: ClassVar["CryptoSuite"]
    SUITE_PQ_SHAKE_V1: ClassVar["CryptoSuite"]
    SUITE_PQ_V1: ClassVar["CryptoSuite"]
    SUITE_PQ_HYBRID_V1: ClassVar["CryptoSuite"]
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
        return cls.SUITE_SHA256_V1

    @classmethod
    def all(cls) -> tuple["CryptoSuite", ...]:
        """Return all registered suites in stable identifier order."""
        return tuple(cls._REGISTRY.values())

    @property
    def is_post_quantum(self) -> bool:
        """Return whether the exchange agreement includes ML-KEM."""
        return self.EXCHANGE_KEY_AGREEMENT_MLKEM_PREFIX in self.exchange_key_agreement

    @property
    def minimum_mac_key_length(self) -> int:
        """Return the minimum hashing-secret length required by this suite's MAC."""
        return 32 if self.token_mac_algorithm.startswith(self.TOKEN_MAC_KMAC256_PREFIX) else 0

    def validate_hashing_secret(self, hashing_secret: bytes) -> bytes:
        """Validate and return hashing-secret bytes for this suite's MAC."""
        if not isinstance(hashing_secret, bytes):
            raise TypeError(f"Crypto suite '{self.suite_id}' requires hashing secret bytes.")

        minimum_length = self.minimum_mac_key_length
        if len(hashing_secret) < minimum_length:
            if self.token_mac_algorithm.startswith(self.TOKEN_MAC_KMAC256_PREFIX):
                raise CryptoSuiteError(
                    f"Crypto suite '{self.suite_id}': {self.TOKEN_MAC_KMAC256_PREFIX} requires a hashing secret "
                    f"of at least {minimum_length} bytes."
                )
            raise CryptoSuiteError(f"Crypto suite '{self.suite_id}' requires a non-empty hashing secret.")
        return hashing_secret

    def validate(self) -> "CryptoSuite":
        """Validate the suite's internal algorithm and version combination."""
        if self.token_content_encryption != self.TOKEN_CONTENT_ENCRYPTION_A256GCM:
            raise CryptoSuiteError(f"Unsupported token content encryption '{self.token_content_encryption}'.")
        if self.exchange_config_version == 1 and self.exchange_key_agreement != self.EXCHANGE_KEY_AGREEMENT_ECDH:
            raise CryptoSuiteError("Exchange configuration version 1 only supports ECDH.")
        if self.exchange_config_version == 2 and self.exchange_key_agreement == self.EXCHANGE_KEY_AGREEMENT_ECDH:
            raise CryptoSuiteError("Exchange configuration version 2 requires a non-ECDH key agreement.")
        if self.exchange_config_version not in {1, 2}:
            raise CryptoSuiteError(f"Unsupported exchange configuration version '{self.exchange_config_version}'.")
        return self


CryptoSuite.SUITE_SHA256_V1 = CryptoSuite(
    suite_id="suite-sha256-v1",
    token_digest_algorithm=CryptoSuite.TOKEN_DIGEST_SHA256,
    token_mac_algorithm=CryptoSuite.TOKEN_MAC_HS256,
    token_content_encryption=CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM,
    exchange_key_agreement=CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH,
    exchange_config_version=1,
)
CryptoSuite.SUITE_SHA3_V1 = CryptoSuite(
    suite_id="suite-sha3-v1",
    token_digest_algorithm=CryptoSuite.TOKEN_DIGEST_SHA3_256,
    token_mac_algorithm=CryptoSuite.TOKEN_MAC_HS3_256,
    token_content_encryption=CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM,
    exchange_key_agreement=CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH,
    exchange_config_version=1,
)
CryptoSuite.SUITE_PQ_SHAKE_V1 = CryptoSuite(
    suite_id="suite-pq-shake-v1",
    token_digest_algorithm=CryptoSuite.TOKEN_DIGEST_SHAKE256_256,
    token_mac_algorithm=CryptoSuite.TOKEN_MAC_KMAC256_256,
    token_content_encryption=CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM,
    exchange_key_agreement=CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768,
    exchange_config_version=2,
)
CryptoSuite.SUITE_PQ_V1 = CryptoSuite(
    suite_id="suite-pq-v1",
    token_digest_algorithm=CryptoSuite.TOKEN_DIGEST_SHA3_256,
    token_mac_algorithm=CryptoSuite.TOKEN_MAC_HS3_256,
    token_content_encryption=CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM,
    exchange_key_agreement=CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768,
    exchange_config_version=2,
)
CryptoSuite.SUITE_PQ_HYBRID_V1 = CryptoSuite(
    suite_id="suite-pq-hybrid-v1",
    token_digest_algorithm=CryptoSuite.TOKEN_DIGEST_SHA3_256,
    token_mac_algorithm=CryptoSuite.TOKEN_MAC_HS3_256,
    token_content_encryption=CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM,
    exchange_key_agreement=CryptoSuite.EXCHANGE_KEY_AGREEMENT_ECDH_MLKEM768,
    exchange_config_version=2,
)

CryptoSuite._REGISTRY = {
    suite.suite_id: suite
    for suite in (
        CryptoSuite.SUITE_SHA256_V1,
        CryptoSuite.SUITE_SHA3_V1,
        CryptoSuite.SUITE_PQ_SHAKE_V1,
        CryptoSuite.SUITE_PQ_V1,
        CryptoSuite.SUITE_PQ_HYBRID_V1,
    )
}

for _suite in CryptoSuite._REGISTRY.values():
    _suite.validate()
