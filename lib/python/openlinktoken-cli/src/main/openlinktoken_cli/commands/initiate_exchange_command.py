# SPDX-License-Identifier: MIT

import argparse
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from openlinktoken.exchange_jwe import EXCHANGE_JWE_VERSION, build_exchange_envelope
from openlinktoken_cli.util.ec_key_utils import (
    SUPPORTED_CURVES,
    derive_public_key_from_private_pem,
    ensure_directory,
    generate_key_pair,
    resolve_key_name,
    write_key,
)
from openlinktoken_cli.util.stdin_utils import read_required_env_bytes, read_required_stdin_bytes

logger = logging.getLogger(__name__)

EXCHANGE_CONFIG_VERSION = EXCHANGE_JWE_VERSION


class InitiateExchangeCommand:
    """
    Initiate an ECDH key-exchange with a partner.

    Steps performed:
     1. Resolve/create a sender key pair locally, or derive it from an external reference.
     2. Read the partner's public key from a PEM/SPKI file.
     3. Generate a random hashing secret (or accept one provided by the caller).
     4. Encrypt the exchange payload into a multi-recipient JWE envelope.
     5. Write the versioned exchange config envelope to the requested output path.
    """

    @staticmethod
    def register_subcommand(subparsers) -> None:
        """Register the initiate-exchange subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "initiate-exchange",
            help="Initiate an ECDH key exchange and produce an encrypted exchange config JWE envelope",
            formatter_class=argparse.RawTextHelpFormatter,
            description=(
                "Initiate an ECDH key exchange with a partner.\n\n"
                "Generates, reuses, or derives a sender key pair, encrypts the\n"
                "exchange payload into a multi-recipient JWE envelope, and writes a\n"
                f"version {EXCHANGE_CONFIG_VERSION} encrypted exchange config JSON file."
            ),
        )

        partner_public_key_group = parser.add_mutually_exclusive_group(required=True)
        partner_public_key_group.add_argument(
            "--public-key",
            dest="public_key",
            metavar="PATH",
            help="Path to the partner's public key in PEM/SPKI format",
        )
        partner_public_key_group.add_argument(
            "--public-key-stdin",
            dest="public_key_stdin",
            action="store_true",
            default=False,
            help="Read the partner's public key PEM/SPKI data from stdin",
        )
        partner_public_key_group.add_argument(
            "--public-key-env",
            dest="public_key_env",
            metavar="ENV_VAR",
            help="Read the partner's public key PEM/SPKI data from the named environment variable",
        )

        parser.add_argument(
            "-n",
            "--name",
            dest="name",
            default=None,
            help="Base name for the local key files (default: openlinktoken-<ISO8601-date>)",
        )

        parser.add_argument(
            "-o",
            "--output",
            dest="output",
            default=None,
            metavar="PATH",
            help="Output path for the exchange config JSON (default: ./<name>.exchange.json)",
        )

        hashing_secret_group = parser.add_mutually_exclusive_group(required=False)
        hashing_secret_group.add_argument(
            "--hashingsecret",
            dest="hashing_secret",
            default=None,
            metavar="SECRET",
            help="Hashing secret to encrypt (default: randomly generated)",
        )
        hashing_secret_group.add_argument(
            "--hashingsecret-stdin",
            dest="hashing_secret_stdin",
            action="store_true",
            default=False,
            help="Read the hashing secret from stdin instead of passing it on the command line",
        )
        hashing_secret_group.add_argument(
            "--hashingsecret-env",
            dest="hashing_secret_env",
            default=None,
            metavar="ENV_VAR",
            help="Read the hashing secret from the named environment variable",
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

        sender_private_key_group = parser.add_mutually_exclusive_group(required=False)
        sender_private_key_group.add_argument(
            "--sender-private-key",
            dest="local_private_key",
            default=None,
            metavar="PATH",
            help=(
                "Reuse an existing sender private key PEM for the sender-side recipient entry and local key continuity"
            ),
        )
        sender_private_key_group.add_argument(
            "--sender-private-key-env",
            dest="sender_private_key_env",
            default=None,
            metavar="ENV_VAR",
            help="Read the sender private key PEM from the named environment variable without writing local key files",
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
        public_key_stdin: bool = getattr(args, "public_key_stdin", False)
        public_key_env_name: Optional[str] = getattr(args, "public_key_env", None)
        output_path_str: Optional[str] = getattr(args, "output", None)
        hashing_secret: Optional[str] = getattr(args, "hashing_secret", None)
        hashing_secret_stdin: bool = getattr(args, "hashing_secret_stdin", False)
        hashing_secret_env_name: Optional[str] = getattr(args, "hashing_secret_env", None)
        curve: Optional[str] = getattr(args, "curve", None)
        force: bool = getattr(args, "force", False)
        local_private_key_path_str: Optional[str] = getattr(args, "local_private_key", None)
        sender_private_key_env_name: Optional[str] = getattr(args, "sender_private_key_env", None)

        try:
            name = resolve_key_name(name)

            if curve is not None and curve not in SUPPORTED_CURVES:
                logger.error(
                    "Unsupported curve '%s'. Valid options are: %s",
                    curve,
                    ", ".join(SUPPORTED_CURVES),
                )
                return 1

            if public_key_stdin and hashing_secret_stdin:
                logger.error(
                    "Cannot combine --public-key-stdin and --hashingsecret-stdin because both consume stdin. "
                    "Use an environment-variable or file-based input for one of them."
                )
                return 1

            opentoken_dir = Path.home() / ".openlinktoken"
            private_key_path = opentoken_dir / f"{name}.private.pem"
            public_key_path_local = opentoken_dir / f"{name}.public.pem"
            output_path = Path(output_path_str) if output_path_str else Path(f"{name}.exchange.json")

            if not force and output_path.exists():
                logger.error(
                    "Exchange config '%s' already exists. Use --force to overwrite.",
                    output_path,
                )
                return 1

            if public_key_stdin:
                partner_public_pem = read_required_stdin_bytes("--public-key-stdin", "partner public key")
            elif public_key_env_name:
                partner_public_pem = read_required_env_bytes(
                    "--public-key-env",
                    public_key_env_name,
                    "partner public key",
                )
            else:
                partner_public_key_path = Path(public_key_path_str)
                if not partner_public_key_path.exists():
                    logger.error("Partner public key file not found: %s", partner_public_key_path)
                    return 1

                partner_public_pem = partner_public_key_path.read_bytes()

            persist_local_key_files = True
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
            elif sender_private_key_env_name:
                persist_local_key_files = False
                private_pem = read_required_env_bytes(
                    "--sender-private-key-env",
                    sender_private_key_env_name,
                    "sender private key",
                )
                local_public_pem, resolved_curve = derive_public_key_from_private_pem(private_pem)
                if curve is not None and curve != resolved_curve:
                    logger.error(
                        "Sender private key curve '%s' does not match requested --curve '%s'.",
                        resolved_curve,
                        curve,
                    )
                    return 1
            else:
                resolved_curve = curve or "P-256"
                private_pem, local_public_pem = generate_key_pair(resolved_curve)

            resolved_hashing_secret = InitiateExchangeCommand._resolve_hashing_secret(
                hashing_secret,
                hashing_secret_stdin=hashing_secret_stdin,
                hashing_secret_env_name=hashing_secret_env_name,
            )

            if persist_local_key_files:
                if not force and (private_key_path.exists() or public_key_path_local.exists()):
                    logger.error(
                        "Key files for '%s' already exist in %s. Use --force to overwrite.",
                        name,
                        opentoken_dir,
                    )
                    return 1

                ensure_directory(opentoken_dir)
                write_key(private_key_path, private_pem, 0o600, overwrite=force)
                write_key(public_key_path_local, local_public_pem, 0o644, overwrite=force)

            config = build_exchange_envelope(
                exchange_name=name,
                hashing_secret=resolved_hashing_secret,
                sender_public_pem=local_public_pem,
                recipient_public_pem=partner_public_pem,
                curve=resolved_curve,
                created_at=InitiateExchangeCommand._created_at(),
                exchange_id=InitiateExchangeCommand._exchange_id(),
            )

            InitiateExchangeCommand._write_config(output_path, config, overwrite=force)
        except (OSError, ValueError) as error:
            logger.error("Validation or file system error during initiate-exchange: %s", error)
            return 1
        except Exception as e:
            logger.error("Unexpected error during initiate-exchange: %s", e, exc_info=True)
            return 1

        if persist_local_key_files:
            print(f"Private key:     {private_key_path.resolve()}")
            print(f"Public key:      {public_key_path_local.resolve()}")
        else:
            print(f"Sender private key: ${sender_private_key_env_name} (environment variable, not written locally)")
            print("Sender public key:  derived from the sender private key (not written locally)")
        print(f"Exchange config: {output_path.resolve()}")
        return 0

    @staticmethod
    def _resolve_hashing_secret(
        hashing_secret: Optional[str],
        hashing_secret_stdin: bool = False,
        hashing_secret_env_name: Optional[str] = None,
    ) -> bytes:
        """Return the provided hashing secret as bytes, or generate a secure random one.

        Args:
            hashing_secret: Caller-supplied secret string, or ``None`` to auto-generate.
            hashing_secret_stdin: When true, read the hashing secret bytes from stdin.
            hashing_secret_env_name: Environment variable name containing the hashing secret.

        Returns:
            The hashing secret as raw bytes.
        """
        if hashing_secret_stdin:
            hashing_secret_bytes = read_required_stdin_bytes("--hashingsecret-stdin", "hashing secret")
            if hashing_secret_bytes.endswith(b"\r\n"):
                return hashing_secret_bytes[:-2]
            if hashing_secret_bytes.endswith(b"\n"):
                return hashing_secret_bytes[:-1]
            return hashing_secret_bytes
        if hashing_secret_env_name:
            return read_required_env_bytes(
                "--hashingsecret-env",
                hashing_secret_env_name,
                "hashing secret",
            )
        if hashing_secret:
            return hashing_secret.encode()
        return secrets.token_bytes(32)

    @staticmethod
    def _created_at() -> str:
        """Return the current UTC timestamp in ISO 8601 ``Z`` form."""
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _exchange_id() -> str:
        """Return a stable random exchange identifier for the envelope payload."""
        return str(uuid4())

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
        if path.is_symlink():
            raise OSError(f"Exchange config path {path} must not be a symbolic link.")

        if not overwrite and path.exists():
            raise FileExistsError(f"Exchange config '{path}' already exists. Use --force to overwrite.")

        path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT
        flags |= os.O_TRUNC if overwrite else os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW

        file_descriptor = os.open(path, flags, 0o600)
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as file_handle:
            json.dump(config, file_handle, indent=2)
            file_handle.write("\n")
