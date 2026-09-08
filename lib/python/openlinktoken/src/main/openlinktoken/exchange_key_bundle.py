# SPDX-License-Identifier: MIT
"""Explicit public/private key bundles for version-2 exchange suites."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, mlkem

from openlinktoken.crypto_suite import CryptoSuite

BUNDLE_VERSION = 1
BUNDLE_TYPE = "openlinktoken-key-bundle"
MLKEM_ALGORITHM = "ML-KEM-768"
MLKEM_PUBLIC_KEY_SIZE = 1184
MLKEM_PRIVATE_SEED_SIZE = 64
EC_ALGORITHM = "ECDH-P256"


class KeyBundleError(ValueError):
    """Raised when a key bundle is malformed or does not match its suite."""


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: Any, field_name: str) -> bytes:
    if not isinstance(value, str) or not value:
        raise KeyBundleError(f"{field_name} must be a non-empty base64url string.")
    try:
        padding = "=" * (-len(value) % 4)
        return base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except Exception as error:
        raise KeyBundleError(f"{field_name} is not valid base64url data: {error}") from error


def _sha256_fingerprint(value: bytes) -> str:
    digest = hashlib.sha256(value).hexdigest().upper()
    return ":".join(digest[index : index + 2] for index in range(0, len(digest), 2))


def _fingerprint_to_kid(fingerprint: str) -> str:
    return f"sha256:{fingerprint.lower().replace(':', '-')}"


@dataclass(frozen=True)
class ExchangeKeyBundle:
    """Validated key material with private values kept local to the participant."""

    suite: CryptoSuite
    mlkem_public_key: bytes | None = None
    mlkem_private_seed: bytes | None = None
    ec_public_pem: bytes | None = None
    ec_private_pem: bytes | None = None

    @property
    def kid(self) -> str:
        """Return a stable identifier for the complete public key bundle."""
        fingerprint_input = b"openlinktoken:key-bundle:v1:" + self.suite.suite_id.encode("ascii")
        if self.mlkem_public_key is not None:
            fingerprint_input += b":mlkem:" + self.mlkem_public_key
        if self.ec_public_pem is not None:
            public_key = serialization.load_pem_public_key(self.ec_public_pem)
            ec_der = public_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            fingerprint_input += b":ec:" + ec_der
        return _fingerprint_to_kid(_sha256_fingerprint(fingerprint_input))

    @property
    def has_private_material(self) -> bool:
        """Return whether the bundle contains all private material required by its suite."""
        mlkem_private = self.mlkem_private_seed is not None
        ec_private = self.ec_private_pem is not None
        if self.suite.exchange_key_agreement == "ML-KEM-768":
            return mlkem_private
        if self.suite.exchange_key_agreement == "ECDH+ML-KEM-768":
            return mlkem_private and ec_private
        return False

    def to_mapping(self, include_private: bool = False) -> dict[str, Any]:
        """Serialize this bundle into its explicit JSON-compatible mapping."""
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

        if self.ec_public_pem is not None:
            ec_section: dict[str, Any] = {
                "algorithm": EC_ALGORITHM,
                "publicKeyEncoding": "pem",
                "publicKey": self.ec_public_pem.decode("utf-8"),
            }
            if include_private:
                if self.ec_private_pem is None:
                    raise KeyBundleError("EC private key is missing.")
                ec_section.update(
                    {
                        "privateKeyEncoding": "pem",
                        "privateKey": self.ec_private_pem.decode("utf-8"),
                    }
                )
            keys["ec"] = ec_section

        return {
            "version": BUNDLE_VERSION,
            "type": BUNDLE_TYPE,
            "suite": self.suite.suite_id,
            "kid": self.kid,
            "keys": keys,
        }

    def to_json(self, include_private: bool = False) -> bytes:
        """Serialize this bundle as deterministic UTF-8 JSON."""
        return json.dumps(self.to_mapping(include_private), sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_json(cls, value: bytes | str, require_private: bool = False) -> "ExchangeKeyBundle":
        """Parse and validate a JSON key bundle."""
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
        """Parse and validate a JSON-compatible key bundle mapping."""
        if mapping.get("version") != BUNDLE_VERSION or mapping.get("type") != BUNDLE_TYPE:
            raise KeyBundleError("Unsupported or missing key-bundle version/type.")
        suite = CryptoSuite.from_id(mapping.get("suite"))
        if suite.exchange_config_version != 2:
            raise KeyBundleError(f"Suite '{suite.suite_id}' does not use key-bundle exchange configuration.")

        keys = mapping.get("keys")
        if not isinstance(keys, Mapping):
            raise KeyBundleError("Key bundle is missing its keys object.")

        mlkem_section = keys.get("mlkem")
        mlkem_public_key = None
        mlkem_private_seed = None
        if "ML-KEM" in suite.exchange_key_agreement:
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

        ec_section = keys.get("ec")
        ec_public_pem = None
        ec_private_pem = None
        if suite.exchange_key_agreement == "ECDH+ML-KEM-768":
            if not isinstance(ec_section, Mapping):
                raise KeyBundleError("The selected hybrid suite requires an ec key section.")
            if ec_section.get("algorithm") != EC_ALGORITHM:
                raise KeyBundleError(f"Unsupported EC algorithm '{ec_section.get('algorithm')}'.")
            if ec_section.get("publicKeyEncoding") != "pem":
                raise KeyBundleError("ec.publicKeyEncoding must be pem.")
            ec_public_value = ec_section.get("publicKey")
            if not isinstance(ec_public_value, str) or not ec_public_value:
                raise KeyBundleError("ec.publicKey must be non-empty PEM text.")
            ec_public_pem = ec_public_value.encode("utf-8")
            _validate_ec_public_key(ec_public_pem)
            if "privateKey" in ec_section:
                if ec_section.get("privateKeyEncoding") != "pem":
                    raise KeyBundleError("ec.privateKeyEncoding must be pem.")
                ec_private_value = ec_section.get("privateKey")
                if not isinstance(ec_private_value, str) or not ec_private_value:
                    raise KeyBundleError("ec.privateKey must be non-empty PEM text.")
                ec_private_pem = ec_private_value.encode("utf-8")
                _validate_ec_private_key(ec_private_pem, ec_public_pem)

        bundle = cls(
            suite=suite,
            mlkem_public_key=mlkem_public_key,
            mlkem_private_seed=mlkem_private_seed,
            ec_public_pem=ec_public_pem,
            ec_private_pem=ec_private_pem,
        )
        if mapping.get("kid") != bundle.kid:
            raise KeyBundleError("Key-bundle kid does not match its public key material.")
        if require_private and not bundle.has_private_material:
            raise KeyBundleError("Key bundle does not contain the private material required by its suite.")
        return bundle


def generate_exchange_key_bundle(suite_id: str) -> ExchangeKeyBundle:
    """Generate a validated private key bundle for a version-2 exchange suite."""
    suite = CryptoSuite.from_id(suite_id)
    if suite.exchange_config_version != 2:
        raise KeyBundleError(f"Suite '{suite_id}' does not require a version-2 key bundle.")

    try:
        mlkem_private = mlkem.MLKEM768PrivateKey.generate()
    except Exception as error:
        raise KeyBundleError(f"ML-KEM-768 is unavailable from the configured cryptography provider: {error}") from error

    ec_private_pem = None
    ec_public_pem = None
    if suite.exchange_key_agreement == "ECDH+ML-KEM-768":
        private_ec = ec.generate_private_key(ec.SECP256R1())
        ec_private_pem = private_ec.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        ec_public_pem = private_ec.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    return ExchangeKeyBundle(
        suite=suite,
        mlkem_public_key=mlkem_private.public_key().public_bytes_raw(),
        mlkem_private_seed=mlkem_private.private_bytes_raw(),
        ec_public_pem=ec_public_pem,
        ec_private_pem=ec_private_pem,
    )


def resolve_private_bundle_by_kid(directory: Path, kid: str) -> bytes:
    """Find a private JSON key bundle whose public material matches ``kid``."""
    for path in sorted(directory.glob("*.private.bundle.json")):
        bundle = ExchangeKeyBundle.from_json(path.read_bytes(), require_private=True)
        if bundle.kid == kid:
            return path.read_bytes()
    raise FileNotFoundError(f"No private key bundle found for recipient kid '{kid}' in {directory}.")


def _validate_ec_public_key(public_pem: bytes) -> None:
    try:
        public_key = serialization.load_pem_public_key(public_pem)
    except (ValueError, TypeError) as error:
        raise KeyBundleError(f"ec.publicKey is not valid PEM: {error}") from error
    if not isinstance(public_key, ec.EllipticCurvePublicKey) or public_key.curve.name != "secp256r1":
        raise KeyBundleError("ec.publicKey must be a P-256 public key.")


def _validate_ec_private_key(private_pem: bytes, public_pem: bytes) -> None:
    try:
        private_key = serialization.load_pem_private_key(private_pem, password=None)
    except (ValueError, TypeError) as error:
        raise KeyBundleError(f"ec.privateKey is not valid PEM: {error}") from error
    if not isinstance(private_key, ec.EllipticCurvePrivateKey) or private_key.curve.name != "secp256r1":
        raise KeyBundleError("ec.privateKey must be a P-256 private key.")
    derived_public = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    if derived_public != public_pem:
        raise KeyBundleError("ec.privateKey does not match ec.publicKey.")
