# SPDX-License-Identifier: MIT
"""Standard JWE JSON helpers for the version-2 ML-KEM exchange suites."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import mlkem
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.keywrap import aes_key_unwrap, aes_key_wrap
from jwcrypto import jwe
from jwcrypto.common import InvalidJWEOperation, JWException

from openlinktoken.crypto.crypto_suite import CryptoSuite
from openlinktoken.exchange_key_bundle import ExchangeKeyBundle

EXCHANGE_V2_VERSION = 2
EXCHANGE_V2_TYPE = "openlinktoken-exchange+jwe"
EXCHANGE_V2_CONTENT_TYPE = "application/openlinktoken-exchange+json"
EXCHANGE_V2_ENCRYPTION = CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM
PURE_KEM_ALGORITHM = CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768
TOKEN_TRANSPORT_KEY_INFO = b"openlinktoken:token-encryption:v2"

CEK_SIZE = 32
MLKEM_CIPHERTEXT_SIZE = 1088
AES_KW_WRAPPED_CEK_SIZE = 40
RECIPIENT_ENCRYPTED_KEY_SIZE = MLKEM_CIPHERTEXT_SIZE + AES_KW_WRAPPED_CEK_SIZE

_ALLOWED_ALGORITHMS = [PURE_KEM_ALGORITHM, EXCHANGE_V2_ENCRYPTION]
_REQUIRED_PROTECTED_FIELDS = {
    "typ",
    "cty",
    "enc",
    "version",
    "cryptoSuite",
    "exchangeId",
}
_JWE_MEMBERS = {"protected", "recipients", "iv", "ciphertext", "tag"}


class OpenLinkTokenJWE(jwe.JWE):
    """JWE object with per-instance dispatch for custom exchange algorithms.

    The constructor follows ``jwcrypto.jwe.JWE`` and accepts its standard
    initialization inputs.

    Args:
        plaintext: Optional plaintext bytes to encrypt.
        protected: Optional protected JWE header.
        unprotected: Optional unprotected JWE header.
        aad: Optional additional authenticated data.
        algs: Optional set of algorithms allowed for this JWE object.
        recipient: Optional initial recipient key or recipient object.
        header: Optional initial recipient-specific header.
        header_registry: Optional registry of recognized JOSE header parameters.

    Returns:
        An ``OpenLinkTokenJWE`` initialized with the supplied JWE state.
    """

    def _jwa_keymgmt(self, name: str):
        """Select a key-management handler for a JOSE algorithm.

        Args:
            name: JOSE key-management algorithm identifier.

        Returns:
            The local ML-KEM handler for an allowed custom algorithm, or the
            handler selected by ``jwcrypto.jwe.JWE`` for other algorithms.
        """
        if name == PURE_KEM_ALGORITHM:
            allowed = self._allowed_algs
            if allowed is None or name not in allowed:
                raise InvalidJWEOperation("Algorithm not allowed")
            return _MLKEMKeyManagement(name)
        return super()._jwa_keymgmt(name)


class _MLKEMKeyManagement:
    """Implement recipient key management for the custom ML-KEM algorithms.

    Args:
        algorithm: JOSE key-management algorithm handled by this instance.

    Returns:
        An ``_MLKEMKeyManagement`` instance configured for ``algorithm``.
    """

    def __init__(self, algorithm: str) -> None:
        """Initialize the handler for one key-management algorithm.

        Args:
            algorithm: JOSE key-management algorithm handled by this instance.

        Returns:
            None.
        """
        self.algorithm = algorithm

    def wrap(
        self,
        key: ExchangeKeyBundle,
        bitsize: int,
        cek: bytes | None,
        headers: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Encapsulate a recipient key and AES-KW-wrap the JWE CEK.

        Args:
            key: Recipient's public version-2 exchange key bundle.
            bitsize: Requested content-encryption-key size in bits.
            cek: Optional content-encryption key bytes to wrap.
            headers: JOSE header values containing the authenticated exchange
                context and recipient key ID.

        Returns:
            A key-management result containing the CEK, combined ML-KEM and
            AES-KW encrypted key.
        """
        _validate_key_and_headers(key, headers, self.algorithm, require_private=False)
        if bitsize != CEK_SIZE * 8:
            raise ValueError(f"Version-2 JWE requires a {CEK_SIZE * 8}-bit CEK, got {bitsize}.")
        if cek is None:
            cek = os.urandom(CEK_SIZE)
        if len(cek) != CEK_SIZE:
            raise ValueError(f"Version-2 JWE CEK must be {CEK_SIZE} bytes.")

        shared_secret, mlkem_ciphertext = _encapsulate(key)
        kek = bytearray(_derive_recipient_kek(shared_secret, headers, mlkem_ciphertext, key.mlkem_public_key or b""))
        try:
            wrapped_cek = aes_key_wrap(bytes(kek), cek)
        except ValueError as error:
            raise ValueError(f"Failed to wrap the version-2 JWE CEK: {error}") from error
        finally:
            _wipe(kek)

        result: dict[str, Any] = {
            "cek": cek,
            "ek": mlkem_ciphertext + wrapped_cek,
        }
        return result

    def unwrap(
        self,
        key: ExchangeKeyBundle,
        bitsize: int,
        encrypted_key: bytes,
        headers: Mapping[str, Any],
    ) -> bytes:
        """Decapsulate a recipient key and AES-KW-unwrap the JWE CEK.

        Args:
            key: Recipient's private version-2 exchange key bundle.
            bitsize: Expected content-encryption-key size in bits.
            encrypted_key: Combined ML-KEM ciphertext and AES-KW-wrapped CEK.
            headers: JOSE header values containing the authenticated exchange
                context and recipient key ID.

        Returns:
            The unwrapped content-encryption key bytes.
        """
        _validate_key_and_headers(key, headers, self.algorithm, require_private=True)
        if bitsize != CEK_SIZE * 8:
            raise ValueError(f"Version-2 JWE requires a {CEK_SIZE * 8}-bit CEK, got {bitsize}.")
        if len(encrypted_key) != RECIPIENT_ENCRYPTED_KEY_SIZE:
            raise ValueError(
                f"Recipient encrypted_key must be {RECIPIENT_ENCRYPTED_KEY_SIZE} bytes, got {len(encrypted_key)}."
            )

        mlkem_ciphertext = encrypted_key[:MLKEM_CIPHERTEXT_SIZE]
        wrapped_cek = encrypted_key[MLKEM_CIPHERTEXT_SIZE:]
        shared_secret = _decapsulate(key, mlkem_ciphertext)
        kek = bytearray(_derive_recipient_kek(shared_secret, headers, mlkem_ciphertext, key.mlkem_public_key or b""))
        try:
            cek = aes_key_unwrap(bytes(kek), wrapped_cek)
        except ValueError as error:
            raise ValueError(f"Failed to unwrap the version-2 JWE CEK: {error}") from error
        finally:
            _wipe(kek)
        if len(cek) != CEK_SIZE:
            raise ValueError(f"Unwrapped version-2 JWE CEK must be {CEK_SIZE} bytes.")
        return cek


def build_v2_jwe(
    plaintext: bytes,
    protected_header: Mapping[str, Any],
    recipients: Sequence[ExchangeKeyBundle],
) -> dict[str, Any]:
    """Build a standard general JWE JSON object for a version-2 exchange.

    Args:
        plaintext: Exchange payload bytes to encrypt.
        protected_header: Authenticated version-2 JWE protected-header values.
        recipients: Public key bundles for the exchange recipients.

    Returns:
        The serialized general-JSON JWE mapping.
    """
    if not isinstance(plaintext, bytes):
        raise TypeError("JWE plaintext must be bytes.")
    _validate_protected_header(protected_header)
    recipient_list = list(recipients)
    if len(recipient_list) < 2:
        raise ValueError("Version-2 general JWE JSON requires at least two recipients.")

    suite = CryptoSuite.from_id(protected_header["cryptoSuite"])
    algorithm = _algorithm_for_suite(suite)
    if len({bundle.kid for bundle in recipient_list}) != len(recipient_list):
        raise ValueError("Version-2 recipients must have unique key identifiers.")

    protected = json.dumps(dict(protected_header), sort_keys=True, separators=(",", ":"))
    token = OpenLinkTokenJWE(
        plaintext=plaintext,
        protected=protected,
        algs=_ALLOWED_ALGORITHMS,
    )
    for bundle in recipient_list:
        if not isinstance(bundle, ExchangeKeyBundle):
            raise TypeError("Version-2 recipients must be ExchangeKeyBundle instances.")
        token.add_recipient(bundle, header={"alg": algorithm, "kid": bundle.kid})

    serialized = json.loads(token.serialize(compact=False))
    if set(serialized) != _JWE_MEMBERS:
        raise ValueError("Version-2 JWE serialization produced unexpected top-level members.")
    return serialized


def decrypt_v2_jwe(
    envelope: Mapping[str, Any],
    private_bundle: ExchangeKeyBundle,
) -> tuple[bytes, bytes]:
    """Decrypt a version-2 JWE and derive its token transport key.

    Args:
        envelope: Standard general-JSON version-2 JWE mapping.
        private_bundle: Matching private version-2 exchange key bundle.

    Returns:
        A pair containing the decrypted payload bytes and 32-byte token
        transport key.
    """
    if not isinstance(private_bundle, ExchangeKeyBundle):
        raise TypeError("Version-2 decryption requires an ExchangeKeyBundle.")
    if set(envelope) != _JWE_MEMBERS:
        raise ValueError("Version-2 JWE must contain only standard general JSON members.")

    protected_header = _decode_protected_header(envelope.get("protected"))
    _validate_protected_header(protected_header)
    suite = CryptoSuite.from_id(protected_header["cryptoSuite"])
    algorithm = _algorithm_for_suite(suite)
    if private_bundle.suite != suite:
        raise ValueError("Private key bundle suite does not match the protected exchange suite.")

    recipients = envelope.get("recipients")
    if not isinstance(recipients, list) or len(recipients) < 2:
        raise ValueError("Version-2 JWE must contain at least two recipients.")
    matching_recipients = []
    for recipient in recipients:
        _validate_recipient(recipient, algorithm)
        if recipient["header"]["kid"] == private_bundle.kid:
            matching_recipients.append(recipient)
    if len(matching_recipients) != 1:
        raise ValueError("No unique recipient entry matches the supplied private key bundle.")

    token = OpenLinkTokenJWE(algs=_ALLOWED_ALGORITHMS)
    try:
        token.deserialize(json.dumps(dict(envelope), sort_keys=True, separators=(",", ":")))
        token.decrypt(private_bundle)
    except (JWException, KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Failed to decrypt the version-2 JWE exchange: {error}") from error

    if token.cek is None:
        raise ValueError("Version-2 JWE decryption did not produce a content-encryption key.")
    transport_key = _derive_token_transport_key(token.cek, protected_header["exchangeId"])
    return token.payload, transport_key


def _derive_token_transport_key(cek: bytes, exchange_id: str) -> bytes:
    """Derive the v2 token transport key from the internal JWE CEK.

    Args:
        cek: 32-byte JWE content-encryption key.
        exchange_id: Non-empty exchange identifier used as the HKDF salt.

    Returns:
        The 32-byte HKDF-derived token transport key.
    """
    if not isinstance(cek, bytes):
        raise TypeError("Version-2 JWE CEK must be bytes.")
    if len(cek) != CEK_SIZE:
        raise ValueError(f"Version-2 JWE CEK must be {CEK_SIZE} bytes.")
    if not isinstance(exchange_id, str) or not exchange_id:
        raise ValueError("Version-2 exchange ID must be a non-empty string.")

    return HKDF(
        algorithm=hashes.SHA256(),
        length=CEK_SIZE,
        salt=exchange_id.encode("utf-8"),
        info=TOKEN_TRANSPORT_KEY_INFO,
    ).derive(cek)


def _validate_protected_header(protected_header: Mapping[str, Any]) -> None:
    """Validate the authenticated protected-header fields required by v2.

    Args:
        protected_header: Candidate version-2 protected-header mapping.

    Returns:
        None.
    """
    if not isinstance(protected_header, Mapping):
        raise ValueError("Version-2 protected header must be a JSON object.")
    missing = _REQUIRED_PROTECTED_FIELDS - set(protected_header)
    if missing:
        raise ValueError(f"Version-2 protected header is missing fields: {', '.join(sorted(missing))}.")
    if protected_header.get("typ") != EXCHANGE_V2_TYPE:
        raise ValueError("Version-2 protected header has an unsupported typ.")
    if protected_header.get("cty") != EXCHANGE_V2_CONTENT_TYPE:
        raise ValueError("Version-2 protected header has an unsupported cty.")
    if protected_header.get("enc") != EXCHANGE_V2_ENCRYPTION:
        raise ValueError(f"Version-2 protected header must use {CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM}.")
    if protected_header.get("version") != EXCHANGE_V2_VERSION:
        raise ValueError("Version-2 protected header must declare version 2.")
    if not isinstance(protected_header.get("cryptoSuite"), str):
        raise ValueError("Version-2 protected header cryptoSuite must be a string.")
    if not isinstance(protected_header.get("exchangeId"), str) or not protected_header["exchangeId"]:
        raise ValueError("Version-2 protected header exchangeId must be a non-empty string.")
    if "alg" in protected_header or "kid" in protected_header or "epk" in protected_header:
        raise ValueError("Version-2 key-management headers must be recipient-specific.")


def _validate_recipient(recipient: Any, algorithm: str) -> None:
    """Validate a standard v2 recipient member before invoking jwcrypto.

    Args:
        recipient: Candidate general-JSON JWE recipient mapping.
        algorithm: Key-management algorithm required by the protected suite.

    Returns:
        None.
    """
    if not isinstance(recipient, Mapping) or set(recipient) != {"header", "encrypted_key"}:
        raise ValueError("Version-2 recipients must contain only header and encrypted_key.")
    header = recipient["header"]
    if not isinstance(header, Mapping):
        raise ValueError("Version-2 recipient header must be a JSON object.")
    if header.get("alg") != algorithm:
        raise ValueError("Version-2 recipient algorithm does not match the protected suite.")
    if not isinstance(header.get("kid"), str) or not header["kid"]:
        raise ValueError("Version-2 recipient header must contain a non-empty kid.")
    encrypted_key = _decode_base64url(recipient["encrypted_key"], "recipient encrypted_key")
    if len(encrypted_key) != RECIPIENT_ENCRYPTED_KEY_SIZE:
        raise ValueError(
            f"Recipient encrypted_key must decode to {RECIPIENT_ENCRYPTED_KEY_SIZE} bytes, got {len(encrypted_key)}."
        )

    if "epk" in header:
        raise ValueError("ML-KEM recipients must not contain epk.")


def _decode_protected_header(value: Any) -> dict[str, Any]:
    """Decode the base64url protected header from a standard JWE object.

    Args:
        value: Unpadded base64url text from the JWE ``protected`` member.

    Returns:
        The decoded protected-header dictionary.
    """
    protected_bytes = _decode_base64url(value, "protected")
    try:
        protected_header = json.loads(protected_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Protected version-2 JWE header is not valid JSON: {error}") from error
    if not isinstance(protected_header, dict):
        raise ValueError("Protected version-2 JWE header must be a JSON object.")
    return protected_header


def _decode_base64url(value: Any, field_name: str) -> bytes:
    """Decode an unpadded base64url field with strict input validation.

    Args:
        value: Base64url text to decode.
        field_name: Field name included in validation errors.

    Returns:
        The decoded field bytes.
    """
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be non-empty base64url data.")
    try:
        padding = "=" * (-len(value) % 4)
        return base64.b64decode(value + padding, altchars=b"-_", validate=True)
    except (ValueError, UnicodeEncodeError) as error:
        raise ValueError(f"{field_name} is not valid base64url data: {error}") from error


def _algorithm_for_suite(suite: CryptoSuite) -> str:
    """Return the custom JOSE key-management algorithm for a suite.

    Args:
        suite: Validated crypto suite selecting version-2 key agreement.

    Returns:
        The ML-KEM JOSE algorithm identifier.
    """
    if suite.exchange_config_version != EXCHANGE_V2_VERSION:
        raise ValueError(f"Suite '{suite.suite_id}' does not use exchange configuration version 2.")
    if suite.exchange_key_agreement == CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768:
        return PURE_KEM_ALGORITHM
    raise ValueError(f"Unsupported version-2 exchange agreement '{suite.exchange_key_agreement}'.")


def _validate_key_and_headers(
    key: ExchangeKeyBundle,
    headers: Mapping[str, Any],
    algorithm: str,
    require_private: bool,
) -> None:
    """Validate bundle material and JOSE context before key management.

    Args:
        key: Exchange key bundle supplied to the key-management handler.
        headers: JOSE protected and recipient header values.
        algorithm: Key-management algorithm selected for the recipient.
        require_private: Whether the bundle must include private key material.

    Returns:
        None.
    """
    if not isinstance(key, ExchangeKeyBundle):
        raise ValueError("Version-2 custom algorithms require an ExchangeKeyBundle.")
    _validate_header_context(headers, algorithm)
    suite = CryptoSuite.from_id(headers["cryptoSuite"])
    if _algorithm_for_suite(suite) != algorithm:
        raise ValueError("Recipient algorithm does not match the protected exchange suite.")
    if key.suite != suite:
        raise ValueError("Exchange key bundle suite does not match the protected exchange suite.")
    if headers["kid"] != key.kid:
        raise ValueError("Recipient kid does not match the supplied exchange key bundle.")
    if key.mlkem_public_key is None:
        raise ValueError("Exchange key bundle is missing its ML-KEM public key.")
    if require_private and key.mlkem_private_seed is None:
        raise ValueError("Exchange key bundle is missing its ML-KEM private seed.")


def _validate_header_context(headers: Mapping[str, Any], algorithm: str) -> None:
    """Validate the JOSE context visible to a key-management handler.

    Args:
        headers: Combined header values supplied to the handler.
        algorithm: Key-management algorithm selected for the recipient.

    Returns:
        None.
    """
    if headers.get("alg") != algorithm:
        raise ValueError("Recipient algorithm does not match the selected handler.")
    if headers.get("enc") != EXCHANGE_V2_ENCRYPTION:
        raise ValueError(f"Version-2 custom algorithms require {CryptoSuite.TOKEN_CONTENT_ENCRYPTION_A256GCM}.")
    if headers.get("version") != EXCHANGE_V2_VERSION:
        raise ValueError("Version-2 custom algorithms require protected version 2.")
    if not isinstance(headers.get("cryptoSuite"), str) or not headers["cryptoSuite"]:
        raise ValueError("Version-2 custom algorithms require a protected cryptoSuite.")
    if not isinstance(headers.get("exchangeId"), str) or not headers["exchangeId"]:
        raise ValueError("Version-2 custom algorithms require a protected exchangeId.")
    if not isinstance(headers.get("kid"), str) or not headers["kid"]:
        raise ValueError("Version-2 custom algorithms require a recipient kid.")


def _encapsulate(
    bundle: ExchangeKeyBundle,
) -> tuple[bytes, bytes]:
    """Encapsulate an ML-KEM shared secret.

    Args:
        bundle: Recipient's public exchange key bundle.

    Returns:
        A tuple containing the shared secret and ML-KEM ciphertext.
    """
    mlkem_public = mlkem.MLKEM768PublicKey.from_public_bytes(bundle.mlkem_public_key or b"")
    mlkem_shared_secret, mlkem_ciphertext = mlkem_public.encapsulate()
    if len(mlkem_ciphertext) != MLKEM_CIPHERTEXT_SIZE:
        raise ValueError(f"{CryptoSuite.EXCHANGE_KEY_AGREEMENT_MLKEM768} produced an unexpected ciphertext length.")

    return mlkem_shared_secret, mlkem_ciphertext


def _decapsulate(
    bundle: ExchangeKeyBundle,
    mlkem_ciphertext: bytes,
) -> bytes:
    """Decapsulate an ML-KEM shared secret.

    Args:
        bundle: Recipient's private exchange key bundle.
        mlkem_ciphertext: ML-KEM ciphertext produced during encapsulation.

    Returns:
        The shared secret bytes.
    """
    mlkem_private = mlkem.MLKEM768PrivateKey.from_seed_bytes(bundle.mlkem_private_seed or b"")
    return mlkem_private.decapsulate(mlkem_ciphertext)


def _derive_recipient_kek(
    shared_secret: bytes,
    headers: Mapping[str, Any],
    mlkem_ciphertext: bytes,
    recipient_public_key: bytes,
) -> bytes:
    """Derive the AES-KW key-encryption key from the exchange context.

    The ML-KEM ciphertext and recipient public key are bound into the HKDF
    info so the derivation stays sound if hybrid KEMs are added later.

    Args:
        shared_secret: Shared secret produced by the recipient key agreement.
        headers: Authenticated exchange and recipient header values.
        mlkem_ciphertext: ML-KEM ciphertext for this recipient.
        recipient_public_key: Recipient ML-KEM public key bytes.

    Returns:
        The derived AES-KW key-encryption key bytes.
    """
    info = ":".join(
        (
            "openlinktoken",
            "jwe",
            "v2",
            headers["cryptoSuite"],
            headers["alg"],
            headers["kid"],
            hashlib.sha256(mlkem_ciphertext + recipient_public_key).hexdigest(),
        )
    ).encode("ascii")
    return HKDF(
        algorithm=hashes.SHA256(),
        length=CEK_SIZE,
        salt=headers["exchangeId"].encode("utf-8"),
        info=info,
    ).derive(shared_secret)


def _wipe(buffer: bytearray) -> None:
    """Overwrite a mutable secret buffer with zeros.

    This is best effort: immutable ``bytes`` copies created by libraries
    such as ``cryptography`` cannot be cleared from Python.

    Args:
        buffer: Mutable buffer holding secret material.

    Returns:
        None.
    """
    buffer[:] = bytes(len(buffer))


def _encode_base64url(value: bytes) -> str:
    """Encode bytes as unpadded base64url text.

    Args:
        value: Bytes to encode.

    Returns:
        The base64url-encoded ASCII text without padding.
    """
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
