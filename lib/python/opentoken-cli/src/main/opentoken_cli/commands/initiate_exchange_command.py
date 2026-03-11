"""
Copyright (c) Truveta. All rights reserved.
"""

import base64
import json
import logging
import os
import secrets
from pathlib import Path
from typing import Optional

from opentoken_cli.util.ec_key_utils import (
    HKDF_INFO,
    SUPPORTED_CURVES,
    derive_public_key_from_private_pem,
    ensure_directory,
    generate_key_pair,
    public_key_fingerprint,
    resolve_key_name,
    write_key,
)

logger = logging.getLogger(__name__)

EXCHANGE_CONFIG_VERSION = 1


class InitiateExchangeCommand:
    """
    Initiate an ECDH key-exchange with a partner.

    Steps performed:
    1. Resolve/create a local key pair in ``~/.opentoken/``.
    2. Read the partner's public key from a PEM/SPKI file.
    3. Generate a random hashing secret (or accept one provided by the caller).
    4. Derive a shared secret via ECDH, then expand it into an AES-256 key via HKDF.
    5. Encrypt the hashing secret with AES-256-GCM.
    6. Write a versioned JSON exchange config to the requested output path.
    """

    @staticmethod
    def register_subcommand(subparsers) -> None:
        """Register the initiate-exchange subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "initiate-exchange",
            help="Initiate an ECDH key exchange and produce a portable exchange config",
            description=(
                "Initiate an ECDH key exchange with a partner.\n\n"
                "Generates or uses a local key pair in ~/.opentoken/, derives a shared\n"
                "secret from the partner's public key via ECDH + HKDF, and writes a versioned\n"
                "JSON exchange config containing the encrypted hashing secret."
            ),
        )

        parser.add_argument(
            "--public-key",
            dest="public_key",
            required=True,
            metavar="PATH",
            help="Path to the partner's public key in PEM/SPKI format",
        )

        parser.add_argument(
            "-n",
            "--name",
            dest="name",
            default=None,
            help="Base name for the local key files (default: opentoken-<ISO8601-date>)",
        )

        parser.add_argument(
            "-o",
            "--output",
            dest="output",
            default=None,
            metavar="PATH",
            help="Output path for the exchange config JSON (default: ./<name>.exchange.json)",
        )

        parser.add_argument(
            "--hashingsecret",
            dest="hashing_secret",
            default=None,
            metavar="SECRET",
            help="Hashing secret to encrypt (default: randomly generated)",
        )

        parser.add_argument(
            "-c",
            "--curve",
            dest="curve",
            default=None,
            help="Elliptic curve for key generation. Supported: P-256, P-384, P-521 (default: P-256)",
        )

        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            dest="force",
            help="Overwrite existing local key files and exchange config if they already exist",
        )

        parser.add_argument(
            "--local-private-key",
            dest="local_private_key",
            default=None,
            metavar="PATH",
            help="Path to an existing local private key PEM to use and embed instead of generating a new one",
        )

        parser.set_defaults(func=InitiateExchangeCommand.execute)

    @staticmethod
    def execute(args) -> int:
        """Execute the initiate-exchange command.

        Args:
            args: Parsed command-line arguments.

        Returns:
            Exit code (0 for success, non-zero for errors).
        """
        name: Optional[str] = getattr(args, "name", None)
        public_key_path_str: str = getattr(args, "public_key", "")
        output_path_str: Optional[str] = getattr(args, "output", None)
        hashing_secret: Optional[str] = getattr(args, "hashing_secret", None)
        curve: Optional[str] = getattr(args, "curve", None)
        force: bool = getattr(args, "force", False)
        local_private_key_path_str: Optional[str] = getattr(args, "local_private_key", None)

        try:
            name = resolve_key_name(name)

            if curve is not None and curve not in SUPPORTED_CURVES:
                logger.error(
                    "Unsupported curve '%s'. Valid options are: %s",
                    curve,
                    ", ".join(SUPPORTED_CURVES),
                )
                return 1

            opentoken_dir = Path.home() / ".opentoken"
            private_key_path = opentoken_dir / f"{name}.private.pem"
            public_key_path_local = opentoken_dir / f"{name}.public.pem"

            if not force and (private_key_path.exists() or public_key_path_local.exists()):
                logger.error(
                    "Key files for '%s' already exist in %s. Use --force to overwrite.",
                    name,
                    opentoken_dir,
                )
                return 1

            output_path = Path(output_path_str) if output_path_str else Path(f"{name}.exchange.json")

            if not force and output_path.exists():
                logger.error(
                    "Exchange config '%s' already exists. Use --force to overwrite.",
                    output_path,
                )
                return 1

            partner_public_key_path = Path(public_key_path_str)
            if not partner_public_key_path.exists():
                logger.error("Partner public key file not found: %s", partner_public_key_path)
                return 1

            partner_public_pem = partner_public_key_path.read_bytes()

            ensure_directory(opentoken_dir)
            if local_private_key_path_str:
                local_private_key_path = Path(local_private_key_path_str)
                if not local_private_key_path.exists():
                    logger.error("Local private key file not found: %s", local_private_key_path)
                    return 1

                private_pem = local_private_key_path.read_bytes()
                local_public_pem, resolved_curve = derive_public_key_from_private_pem(private_pem)
                if curve is not None and curve != resolved_curve:
                    logger.error(
                        "Local private key curve '%s' does not match requested --curve '%s'.",
                        resolved_curve,
                        curve,
                    )
                    return 1
            else:
                resolved_curve = curve or "P-256"
                private_pem, local_public_pem = generate_key_pair(resolved_curve)

            write_key(private_key_path, private_pem, 0o600, overwrite=force)
            write_key(public_key_path_local, local_public_pem, 0o644, overwrite=force)

            resolved_hashing_secret = InitiateExchangeCommand._resolve_hashing_secret(hashing_secret)
            partner_fingerprint = public_key_fingerprint(partner_public_pem)
            encrypted_payload = InitiateExchangeCommand._encrypt_hashing_secret(
                private_pem, partner_public_pem, resolved_hashing_secret
            )

            config = InitiateExchangeCommand._build_config(
                name=name,
                curve=resolved_curve,
                local_public_pem=local_public_pem,
                partner_public_pem=partner_public_pem,
                partner_fingerprint=partner_fingerprint,
                encrypted_payload=encrypted_payload,
                local_private_pem=private_pem,
            )

            InitiateExchangeCommand._write_config(output_path, config, overwrite=force)
        except (OSError, ValueError) as error:
            logger.error("Validation or file system error during initiate-exchange: %s", error)
            return 1
        except Exception as e:
            logger.error("Unexpected error during initiate-exchange: %s", e, exc_info=True)
            return 1

        print(f"Private key:     {private_key_path.resolve()}")
        print(f"Public key:      {public_key_path_local.resolve()}")
        print(f"Exchange config: {output_path.resolve()}")
        return 0

    @staticmethod
    def _resolve_hashing_secret(hashing_secret: Optional[str]) -> bytes:
        """Return the provided hashing secret as bytes, or generate a secure random one.

        Args:
            hashing_secret: Caller-supplied secret string, or ``None`` to auto-generate.

        Returns:
            The hashing secret as raw bytes.
        """
        if hashing_secret:
            return hashing_secret.encode()
        return secrets.token_bytes(32)

    @staticmethod
    def _encrypt_hashing_secret(
        private_pem: bytes,
        partner_public_pem: bytes,
        hashing_secret: bytes,
    ) -> dict:
        """Derive a shared AES-256 key via ECDH+HKDF and encrypt the hashing secret with AES-GCM.

        Args:
            private_pem:        PEM-encoded local private key bytes.
            partner_public_pem: PEM-encoded partner SubjectPublicKeyInfo bytes.
            hashing_secret:     Plaintext hashing secret bytes to encrypt.

        Returns:
            A dict with ``nonce`` and ``ciphertext`` keys (base64-encoded strings).

        Raises:
            ValueError: If the partner public key PEM cannot be loaded.
        """
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric.ec import ECDH
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

        try:
            partner_public_key = load_pem_public_key(partner_public_pem)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Failed to load partner public key: {e}") from e

        private_key = load_pem_private_key(private_pem, password=None)
        shared_secret = private_key.exchange(ECDH(), partner_public_key)

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=HKDF_INFO,
        )
        aes_key = hkdf.derive(shared_secret)

        nonce = os.urandom(12)
        aesgcm = AESGCM(aes_key)
        ciphertext = aesgcm.encrypt(nonce, hashing_secret, None)

        return {
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
        }

    @staticmethod
    def _build_config(
        name: str,
        curve: str,
        local_public_pem: bytes,
        partner_public_pem: bytes,
        partner_fingerprint: str,
        encrypted_payload: dict,
        local_private_pem: Optional[bytes] = None,
    ) -> dict:
        """Assemble the versioned JSON exchange config dictionary.

        Args:
            name:                Exchange/key basename.
            curve:               Elliptic curve name (e.g. ``P-256``).
            local_public_pem:    PEM-encoded local public key bytes.
            partner_public_pem:  PEM-encoded partner public key bytes.
            partner_fingerprint: SHA-256 fingerprint of the partner's public key.
            encrypted_payload:   Dict with ``nonce`` and ``ciphertext`` (base64 strings).
            local_private_pem:   Optional PEM-encoded local private key bytes for self-contained bundles.

        Returns:
            A dict ready to be serialized as JSON.
        """
        config = {
            "version": EXCHANGE_CONFIG_VERSION,
            "exchangeName": name,
            "keyAgreement": "ECDH",
            "curve": curve,
            "localKey": {
                "basename": name,
                "publicKey": local_public_pem.decode(),
                "publicKeyFingerprint": public_key_fingerprint(local_public_pem),
            },
            "partnerKey": {
                "publicKey": partner_public_pem.decode(),
                "publicKeyFingerprint": partner_fingerprint,
            },
            "kdf": {
                "algorithm": "HKDF",
                "hash": "SHA-256",
                "info": HKDF_INFO.decode(),
            },
            "encryption": {
                "algorithm": "AES-GCM",
                "keyLength": 256,
                "nonceEncoding": "base64",
                "nonce": encrypted_payload["nonce"],
            },
            "encryptedHashingSecret": encrypted_payload["ciphertext"],
        }

        if local_private_pem is not None:
            config["localKey"]["privateKey"] = local_private_pem.decode()
            config["localKey"]["privateKeyFingerprint"] = public_key_fingerprint(local_public_pem)

        return config

    @staticmethod
    def _write_config(path: Path, config: dict, overwrite: bool = True) -> None:
        """Serialize ``config`` as formatted JSON and write it to ``path``.

        Args:
            path:      Destination file path.
            config:    Dict to serialize.
            overwrite: When ``False``, raise ``FileExistsError`` if the file already exists.

        Raises:
            FileExistsError: If the file exists and ``overwrite`` is ``False``.
        """
        if not overwrite and path.exists():
            raise FileExistsError(f"Exchange config '{path}' already exists. Use --force to overwrite.")

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
