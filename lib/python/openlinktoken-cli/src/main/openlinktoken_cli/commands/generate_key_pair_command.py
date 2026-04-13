# SPDX-License-Identifier: MIT

import logging
from pathlib import Path
from typing import Optional, Tuple

from openlinktoken_cli.util.ec_key_utils import (
    SUPPORTED_CURVES,
    ensure_directory,
    generate_key_pair,
    resolve_key_name,
    write_key,
)

logger = logging.getLogger(__name__)


class GenerateKeyPairCommand:
    """
    Generate an ECDH public/private key pair and write the keys to ~/.openlinktoken/.

    Private key:  ~/.openlinktoken/<name>.private.pem  (PEM PKCS#8, permissions 600)
    Public key:   ~/.openlinktoken/<name>.public.pem   (PEM SubjectPublicKeyInfo, permissions 644)
    Directory:    ~/.openlinktoken/                     (created with permissions 700 if absent)
    """

    @staticmethod
    def register_subcommand(subparsers) -> None:
        """Register the generate-key-pair subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "generate-key-pair",
            help="Generate an ECDH public/private key pair and write keys to ~/.openlinktoken/",
            description=(
                "Generate an ECDH public/private key pair and write the keys to ~/.openlinktoken/.\n\n"
                "Private key:  ~/.openlinktoken/<name>.private.pem  (PEM PKCS#8, permissions 600)\n"
                "Public key:   ~/.openlinktoken/<name>.public.pem   (PEM SubjectPublicKeyInfo, permissions 644)\n"
                "Directory:    ~/.openlinktoken/                     (created with permissions 700 if absent)"
            ),
        )

        parser.add_argument(
            "-c",
            "--curve",
            dest="curve",
            default="P-256",
            help="Elliptic curve for key generation. Supported: P-256, P-384, P-521 (default: P-256)",
        )

        parser.add_argument(
            "-n",
            "--name",
            dest="name",
            default=None,
            help="Base name for the key files (default: openlinktoken-<ISO8601-date>)",
        )

        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            dest="force",
            help="Overwrite existing key files if they already exist",
        )

        parser.set_defaults(func=GenerateKeyPairCommand.execute)

    @staticmethod
    def execute(args) -> int:
        """Execute the generate-key-pair command.

        Args:
            args: Parsed command-line arguments.

        Returns:
            Exit code (0 for success, non-zero for errors).
        """
        name: Optional[str] = getattr(args, "name", None)
        curve: str = getattr(args, "curve", "P-256")
        force: bool = getattr(args, "force", False)

        try:
            name = resolve_key_name(name)

            if curve not in SUPPORTED_CURVES:
                logger.error(
                    "Unsupported curve '%s'. Valid options are: %s",
                    curve,
                    ", ".join(SUPPORTED_CURVES),
                )
                return 1

            opentoken_dir = Path.home() / ".openlinktoken"
            private_key_path = opentoken_dir / f"{name}.private.pem"
            public_key_path = opentoken_dir / f"{name}.public.pem"

            if not force and (private_key_path.exists() or public_key_path.exists()):
                logger.error(
                    "Key files for '%s' already exist in %s. Use --force to overwrite.",
                    name,
                    opentoken_dir,
                )
                return 1

            ensure_directory(opentoken_dir)
            private_pem, public_pem = generate_key_pair(curve)
            write_key(private_key_path, private_pem, 0o600, overwrite=force)
            write_key(public_key_path, public_pem, 0o644, overwrite=force)
        except (OSError, ValueError) as error:
            logger.error("Validation or file system error while generating key pair: %s", error)
            return 1
        except Exception as e:
            logger.error("Unexpected error while generating key pair: %s", e, exc_info=True)
            return 1

        print(f"Private key: {private_key_path.resolve()}")
        print(f"Public key:  {public_key_path.resolve()}")
        return 0

    # ---------------------------------------------------------------------------
    # Backward-compatible shims — delegate to ec_key_utils so existing code that
    # called these static methods directly continues to work.
    # ---------------------------------------------------------------------------

    @staticmethod
    def _resolve_key_name(name: Optional[str]) -> str:
        """Resolve and validate the requested key basename."""
        return resolve_key_name(name)

    @staticmethod
    def generate_key_pair(curve: str) -> Tuple[bytes, bytes]:
        """Generate an EC key pair for the specified curve.

        .. deprecated::
            Call ``openlinktoken_cli.util.ec_key_utils.generate_key_pair`` directly.
            This shim exists only for backward compatibility.
        """
        return generate_key_pair(curve)

    @staticmethod
    def _ensure_directory(directory: Path) -> None:
        """Ensure the directory exists, is not a symlink, and has 700 permissions."""
        return ensure_directory(directory)

    @staticmethod
    def _write_key(path: Path, pem_bytes: bytes, mode: int, overwrite: bool = True) -> None:
        """Write PEM bytes to a file using secure creation flags and set the specified permissions."""
        return write_key(path, pem_bytes, mode, overwrite=overwrite)
