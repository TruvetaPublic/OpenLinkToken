# SPDX-License-Identifier: MIT
"""Explicit public/private key bundles for version-2 exchange suites."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives.asymmetric import mlkem

from openlinktoken.crypto.crypto_suite import CryptoSuite

BUNDLE_VERSION = 1
BUNDLE_TYPE = "openlinktoken-key-bundle"
MLKEM_ALGORITHM = CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768
MLKEM_PUBLIC_KEY_SIZE = 1184
MLKEM_PRIVATE_SEED_SIZE = 64


class KeyBundleError(ValueError):
    """Raised when a key bundle is malformed or does not match its suite.

    Args:
        message: Explanation of the key-bundle validation failure.

    Returns:
        A ``KeyBundleError`` instance carrying the validation failure.
    """


def _encode(value: bytes) -> str:
    """Encode bytes as unpadded base64url text for bundle fields.

    Args:
        value: Bytes to encode.

    Returns:
        The base64url-encoded ASCII text without padding.
    """
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: Any, field_name: str) -> bytes:
    """Decode a required base64url field.

    Args:
        value: Base64url text from a key-bundle field.
        field_name: Field name included in validation errors.

    Returns:
        The decoded field bytes.
    """
    if not isinstance(value, str) or not value:
        raise KeyBundleError(f"{field_name} must be a non-empty base64url string.")
    try:
        padding = "=" * (-len(value) % 4)
        return base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except Exception as error:
        raise KeyBundleError(f"{field_name} is not valid base64url data: {error}") from error


def _sha256_fingerprint(value: bytes) -> str:
    """Return an uppercase, colon-delimited SHA-256 fingerprint.

    Args:
        value: Public key material to fingerprint.

    Returns:
        The SHA-256 fingerprint in uppercase colon-delimited hexadecimal form.
    """
    digest = hashlib.sha256(value).hexdigest().upper()
    return ":".join(digest[index : index + 2] for index in range(0, len(digest), 2))


def _fingerprint_to_kid(fingerprint: str) -> str:
    """Convert a display fingerprint into the bundle's stable key identifier.

    Args:
        fingerprint: Colon-delimited SHA-256 fingerprint.

    Returns:
        The lowercase ``sha256:`` key identifier.
    """
    return f"sha256:{fingerprint.lower().replace(':', '-')}"


@dataclass(frozen=True)
class ExchangeKeyBundle:
    """Key material for a version-2 exchange, with private values kept local.

    Args:
        suite: Crypto suite selecting the key-agreement algorithms.
        mlkem_public_key: Optional ML-KEM public key bytes.
        mlkem_private_seed: Optional local ML-KEM private seed bytes.

    Returns:
        A frozen ``ExchangeKeyBundle`` containing the supplied key material.
    """

    suite: CryptoSuite
    mlkem_public_key: bytes | None = None
    mlkem_private_seed: bytes | None = None

    @property
    def kid(self) -> str:
        """Return a stable identifier for the complete public key bundle.

        Args:
            None.

        Returns:
            The ``sha256:`` key identifier derived from this bundle's suite and
            public keys.
        """
        fingerprint_input = b"openlinktoken:key-bundle:v1:" + self.suite.suite_id.encode("ascii")
        if self.mlkem_public_key is not None:
            fingerprint_input += b":mlkem:" + self.mlkem_public_key
        return _fingerprint_to_kid(_sha256_fingerprint(fingerprint_input))

    @property
    def has_private_material(self) -> bool:
        """Return whether the bundle has all private material for its suite.

        Args:
            None.

        Returns:
            ``True`` when all private keys required by the exchange suite are
            present; otherwise, ``False``.
        """
        return (
            self.suite.exchange_key_agreement == CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768
            and self.mlkem_private_seed is not None
        )

    def to_mapping(self, include_private: bool = False) -> dict[str, Any]:
        """Serialize this bundle into its JSON-compatible mapping.

        Args:
            include_private: Whether to include available local private-key
                material in the mapping.

        Returns:
            A mapping containing the bundle version, type, suite, key ID, and
            encoded key sections.
        """
        keys: dict[str, Any] = {}
        if self.mlkem_public_key is not None:
            mlkem_section: dict[str, Any] = {
                "algorithm": MLKEM_ALGORITHM,
                "publicKeyEncoding": "base64url",
                "publicKey": _encode(self.mlkem_public_key),
                "fingerprint": _sha256_fingerprint(self.mlkem_public_key),
            }
            if include_private:
                if self.mlkem_private_seed is None:
                    raise KeyBundleError("ML-KEM private seed is missing.")
                mlkem_section.update(
                    {
                        "privateKeyEncoding": "base64url",
                        "privateKey": _encode(self.mlkem_private_seed),
                    }
                )
            keys["mlkem"] = mlkem_section

        return {
            "version": BUNDLE_VERSION,
            "type": BUNDLE_TYPE,
            "suite": self.suite.suite_id,
            "kid": self.kid,
            "keys": keys,
        }

    def to_json(self, include_private: bool = False) -> bytes:
        """Serialize this bundle as deterministic UTF-8 JSON.

        Args:
            include_private: Whether to include available local private-key
                material in the JSON.

        Returns:
            Deterministically formatted UTF-8 JSON bytes.
        """
        return json.dumps(self.to_mapping(include_private), sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_json(cls, value: bytes | str, require_private: bool = False) -> "ExchangeKeyBundle":
        """Parse and validate a JSON key bundle.

        Args:
            value: UTF-8 JSON bytes or JSON text describing the bundle.
            require_private: Whether the parsed bundle must contain all private
                key material required by its suite.

        Returns:
            The validated ``ExchangeKeyBundle`` represented by the JSON.
        """
        try:
            raw = value.decode("utf-8") if isinstance(value, bytes) else value
            mapping = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise KeyBundleError(f"Key bundle is not valid UTF-8 JSON: {error}") from error
        if not isinstance(mapping, Mapping):
            raise KeyBundleError("Key bundle must be a JSON object.")
        return cls.from_mapping(mapping, require_private=require_private)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any], require_private: bool = False) -> "ExchangeKeyBundle":
        """Parse and validate a JSON-compatible key-bundle mapping.

        Args:
            mapping: Mapping containing the bundle version, suite, key ID, and
                encoded key sections.
            require_private: Whether the bundle must contain all required
                private key material.

        Returns:
            The validated ``ExchangeKeyBundle`` represented by the mapping.
        """
        if mapping.get("version") != BUNDLE_VERSION or mapping.get("type") != BUNDLE_TYPE:
            raise KeyBundleError("Unsupported or missing key-bundle version/type.")
        suite = CryptoSuite.from_id(mapping.get("suite"))
        if suite.exchange_config_version != 2:
            raise KeyBundleError(f"Suite '{suite.suite_id}' does not use key-bundle exchange configuration.")

        keys = mapping.get("keys")
        if not isinstance(keys, Mapping):
            raise KeyBundleError("Key bundle is missing its keys object.")
        for key in keys:
            if key != "mlkem":
                raise KeyBundleError(f"Key bundle contains an unsupported key section '{key}'.")

        mlkem_section = keys.get("mlkem")
        mlkem_public_key = None
        mlkem_private_seed = None
        if suite.exchange_key_agreement == CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768:
            if not isinstance(mlkem_section, Mapping):
                raise KeyBundleError("The selected suite requires an mlkem key section.")
            if mlkem_section.get("algorithm") != MLKEM_ALGORITHM:
                raise KeyBundleError(f"Unsupported ML-KEM algorithm '{mlkem_section.get('algorithm')}'.")
            mlkem_public_key = _decode(mlkem_section.get("publicKey"), "mlkem.publicKey")
            if len(mlkem_public_key) != MLKEM_PUBLIC_KEY_SIZE:
                raise KeyBundleError(f"mlkem.publicKey must be {MLKEM_PUBLIC_KEY_SIZE} bytes.")
            expected_fingerprint = _sha256_fingerprint(mlkem_public_key)
            if mlkem_section.get("fingerprint") != expected_fingerprint:
                raise KeyBundleError("mlkem.fingerprint does not match mlkem.publicKey.")
            if "privateKey" in mlkem_section:
                if mlkem_section.get("privateKeyEncoding") != "base64url":
                    raise KeyBundleError("mlkem.privateKeyEncoding must be base64url.")
                mlkem_private_seed = _decode(mlkem_section.get("privateKey"), "mlkem.privateKey")
                if len(mlkem_private_seed) != MLKEM_PRIVATE_SEED_SIZE:
                    raise KeyBundleError(f"mlkem.privateKey must be {MLKEM_PRIVATE_SEED_SIZE} bytes.")
                try:
                    mlkem_private_key = mlkem.MLKEM768PrivateKey.from_seed_bytes(mlkem_private_seed)
                except (TypeError, ValueError) as error:
                    raise KeyBundleError(f"mlkem.privateKey is not a valid ML-KEM-768 seed: {error}") from error
                if mlkem_private_key.public_key().public_bytes_raw() != mlkem_public_key:
                    raise KeyBundleError("mlkem.privateKey does not match mlkem.publicKey.")

        bundle = cls(
            suite=suite,
            mlkem_public_key=mlkem_public_key,
            mlkem_private_seed=mlkem_private_seed,
        )
        if mapping.get("kid") != bundle.kid:
            raise KeyBundleError("Key-bundle kid does not match its public key material.")
        if require_private and not bundle.has_private_material:
            raise KeyBundleError("Key bundle does not contain the private material required by its suite.")
        return bundle


def generate_exchange_key_bundle(suite_id: str) -> ExchangeKeyBundle:
    """Generate a private key bundle for a version-2 exchange suite.

    Args:
        suite_id: Registered version-2 crypto-suite identifier.

    Returns:
        A validated ``ExchangeKeyBundle`` containing generated private and
        public key material.
    """
    suite = CryptoSuite.from_id(suite_id)
    if suite.exchange_config_version != 2:
        raise KeyBundleError(f"Suite '{suite_id}' does not require a version-2 key bundle.")

    try:
        mlkem_private = mlkem.MLKEM768PrivateKey.generate()
    except Exception as error:
        raise KeyBundleError(
            f"{CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768} is unavailable "
            f"from the configured cryptography provider: {error}"
        ) from error

    return ExchangeKeyBundle(
        suite=suite,
        mlkem_public_key=mlkem_private.public_key().public_bytes_raw(),
        mlkem_private_seed=mlkem_private.private_bytes_raw(),
    )


def resolve_private_bundle_by_kid(directory: Path, kid: str) -> bytes:
    """Find a private JSON key bundle whose public material matches ``kid``.

    Args:
        directory: Directory containing private key-bundle JSON files.
        kid: Recipient key identifier to match.

    Returns:
        The matching private key-bundle JSON bytes.

    Raises:
        KeyBundleError: If invalid candidates were encountered and no valid
            bundle matched ``kid``.
        FileNotFoundError: If no candidate matched ``kid`` and all candidates
            were valid.
    """
    invalid_candidates: list[str] = []
    for path in sorted(directory.glob("*.private.bundle.json")):
        bundle_bytes = path.read_bytes()
        try:
            bundle = ExchangeKeyBundle.from_json(bundle_bytes, require_private=True)
        except ValueError as error:
            invalid_candidates.append(f"{path}: {error}")
            continue
        if bundle.kid == kid:
            return bundle_bytes
    if invalid_candidates:
        invalid_candidate_details = "; ".join(invalid_candidates)
        raise KeyBundleError(
            f"No private key bundle found for recipient kid '{kid}' in {directory}; "
            f"invalid bundle candidates: {invalid_candidate_details}"
        )
    raise FileNotFoundError(f"No private key bundle found for recipient kid '{kid}' in {directory}.")
