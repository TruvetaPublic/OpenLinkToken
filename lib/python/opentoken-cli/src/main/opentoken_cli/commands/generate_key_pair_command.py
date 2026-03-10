"""
Copyright (c) Truveta. All rights reserved.
"""

import logging
import ntpath
import os
import stat
from datetime import date
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

SUPPORTED_CURVES = ["P-256", "P-384", "P-521"]


class GenerateKeyPairCommand:
    """
    Generate an ECDH public/private key pair and write the keys to ~/.opentoken/.

    Private key:  ~/.opentoken/<name>.private.pem  (PEM PKCS#8, permissions 600)
    Public key:   ~/.opentoken/<name>.public.pem   (PEM SubjectPublicKeyInfo, permissions 644)
    Directory:    ~/.opentoken/                     (created with permissions 700 if absent)
    """

    @staticmethod
    def register_subcommand(subparsers) -> None:
        """Register the generate-key-pair subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "generate-key-pair",
            help="Generate an ECDH public/private key pair and write keys to ~/.opentoken/",
            description=(
                "Generate an ECDH public/private key pair and write the keys to ~/.opentoken/.\n\n"
                "Private key:  ~/.opentoken/<name>.private.pem  (PEM PKCS#8, permissions 600)\n"
                "Public key:   ~/.opentoken/<name>.public.pem   (PEM SubjectPublicKeyInfo, permissions 644)\n"
                "Directory:    ~/.opentoken/                     (created with permissions 700 if absent)"
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
            help="Base name for the key files (default: opentoken-<ISO8601-date>)",
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
            name = GenerateKeyPairCommand._resolve_key_name(name)

            if curve not in SUPPORTED_CURVES:
                logger.error(
                    "Unsupported curve '%s'. Valid options are: %s",
                    curve,
                    ", ".join(SUPPORTED_CURVES),
                )
                return 1

            opentoken_dir = Path.home() / ".opentoken"
            private_key_path = opentoken_dir / f"{name}.private.pem"
            public_key_path = opentoken_dir / f"{name}.public.pem"

            if not force and (private_key_path.exists() or public_key_path.exists()):
                logger.error(
                    "Key files for '%s' already exist in %s. Use --force to overwrite.",
                    name,
                    opentoken_dir,
                )
                return 1

            GenerateKeyPairCommand._ensure_directory(opentoken_dir)
            private_pem, public_pem = GenerateKeyPairCommand.generate_key_pair(curve)
            GenerateKeyPairCommand._write_key(private_key_path, private_pem, 0o600, overwrite=force)
            GenerateKeyPairCommand._write_key(public_key_path, public_pem, 0o644, overwrite=force)
        except (OSError, ValueError) as error:
            logger.error("Failed to generate key pair: %s", error)
            return 1
        except Exception as e:
            logger.error("Failed to generate key pair: %s", e, exc_info=True)
            return 1

        print(f"Private key: {private_key_path.resolve()}")
        print(f"Public key:  {public_key_path.resolve()}")
        return 0

    @staticmethod
    def _resolve_key_name(name: Optional[str]) -> str:
        """Resolve and validate the requested key basename."""
        if not name or not name.strip():
            return f"opentoken-{date.today().isoformat()}"

        candidate = name.strip()
        if (
            candidate in {".", ".."}
            or "/" in candidate
            or "\\" in candidate
            or ":" in candidate
            or candidate != Path(candidate).name
            or ntpath.splitdrive(candidate)[0]
        ):
            raise ValueError(
                "Key name must be a simple file basename without path separators, traversal, or drive prefixes."
            )

        return candidate

    @staticmethod
    def generate_key_pair(curve: str) -> Tuple[bytes, bytes]:
        """Generate an EC key pair for the specified curve.

        Args:
            curve: One of ``P-256``, ``P-384``, or ``P-521``.

        Returns:
            A tuple of ``(private_pem, public_pem)`` as bytes.

        Raises:
            ValueError: If the curve name is unsupported.
        """
        from cryptography.hazmat.primitives.asymmetric.ec import (
            SECP256R1,
            SECP384R1,
            SECP521R1,
            generate_private_key,
        )
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            NoEncryption,
            PrivateFormat,
            PublicFormat,
        )

        curve_map = {
            "P-256": SECP256R1,
            "P-384": SECP384R1,
            "P-521": SECP521R1,
        }

        if curve not in curve_map:
            raise ValueError(f"Unsupported curve '{curve}'. Valid options are: {', '.join(SUPPORTED_CURVES)}")

        private_key = generate_private_key(curve_map[curve]())

        private_pem = private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption(),
        )
        public_pem = private_key.public_key().public_bytes(
            encoding=Encoding.PEM,
            format=PublicFormat.SubjectPublicKeyInfo,
        )

        return private_pem, public_pem

    @staticmethod
    def _ensure_directory(directory: Path) -> None:
        """Ensure the directory exists, is not a symlink, and has 700 permissions.

        Args:
            directory: The directory path to create or validate.
        """
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)

        if directory.is_symlink():
            raise OSError(f"Key directory {directory} must not be a symbolic link.")

        if not directory.is_dir():
            raise NotADirectoryError(f"Key directory path {directory} exists and is not a directory.")

        try:
            os.chmod(directory, stat.S_IRWXU)  # 700
        except (NotImplementedError, PermissionError) as e:
            logger.warning("Could not set directory permissions on %s: %s", directory, e)

    @staticmethod
    def _write_key(path: Path, pem_bytes: bytes, mode: int, overwrite: bool = True) -> None:
        """Write PEM bytes to a file using secure creation flags and set the specified permissions.

        Args:
            path:      The target file path.
            pem_bytes: The PEM-encoded key bytes.
            mode:      Octal file permission mode (e.g., ``0o600``).
            overwrite: When false, require exclusive creation instead of truncating an existing file.
        """
        if path.is_symlink():
            raise OSError(f"Key file path {path} must not be a symbolic link.")

        flags = os.O_WRONLY | os.O_CREAT
        flags |= os.O_TRUNC if overwrite else os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW

        file_descriptor = os.open(path, flags, mode)
        try:
            with os.fdopen(file_descriptor, "wb") as file_handle:
                file_handle.write(pem_bytes)
            os.chmod(path, mode)
        except (NotImplementedError, PermissionError) as e:
            logger.warning("Could not set file permissions on %s: %s", path, e)
        except Exception:
            raise
