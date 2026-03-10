"""
Copyright (c) Truveta. All rights reserved.

Shared utilities for ECDH key management used by generate-key-pair and initiate-exchange.
"""

import logging
import os
import stat
from datetime import date
from pathlib import Path, PureWindowsPath
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

SUPPORTED_CURVES = ["P-256", "P-384", "P-521"]

_CURVE_MAP_NAMES = {
    "P-256": "SECP256R1",
    "P-384": "SECP384R1",
    "P-521": "SECP521R1",
}

HKDF_INFO = b"opentoken-exchange-v1"


def get_curve_class(curve: str):
    """Return the cryptography EC curve class for the named curve.

    Args:
        curve: One of ``P-256``, ``P-384``, or ``P-521``.

    Returns:
        An EC curve instance from ``cryptography.hazmat.primitives.asymmetric.ec``.

    Raises:
        ValueError: If the curve name is not supported.
    """
    from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, SECP384R1, SECP521R1

    curve_map = {
        "P-256": SECP256R1,
        "P-384": SECP384R1,
        "P-521": SECP521R1,
    }

    if curve not in curve_map:
        raise ValueError(f"Unsupported curve '{curve}'. Valid options are: {', '.join(SUPPORTED_CURVES)}")

    return curve_map[curve]()


def resolve_key_name(name: Optional[str]) -> str:
    """Resolve and validate the requested key basename.

    Args:
        name: Caller-supplied name, or ``None`` / empty to use the default.

    Returns:
        A validated simple file basename.

    Raises:
        ValueError: If the supplied name contains path separators, traversal components, or drive prefixes.
    """
    if not name or not name.strip():
        return f"opentoken-{date.today().isoformat()}"

    candidate = name.strip()
    if (
        candidate in {".", ".."}
        or "/" in candidate
        or "\\" in candidate
        or ":" in candidate
        or candidate != Path(candidate).name
        or PureWindowsPath(candidate).drive
    ):
        raise ValueError(
            "Key name must be a simple file basename without path separators, traversal, or drive prefixes."
        )

    return candidate


def generate_key_pair(curve: str) -> Tuple[bytes, bytes]:
    """Generate an EC key pair for the specified curve.

    Args:
        curve: One of ``P-256``, ``P-384``, or ``P-521``.

    Returns:
        A tuple of ``(private_pem, public_pem)`` as bytes.

    Raises:
        ValueError: If the curve name is unsupported.
    """
    from cryptography.hazmat.primitives.asymmetric.ec import generate_private_key
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

    curve_instance = get_curve_class(curve)
    private_key = generate_private_key(curve_instance)

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


def ensure_directory(directory: Path) -> None:
    """Ensure the directory exists, is not a symlink, and has 700 permissions.

    Args:
        directory: The directory path to create or validate.

    Raises:
        OSError: If the path is a symbolic link.
        NotADirectoryError: If the path exists but is not a directory.
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


def write_key(path: Path, pem_bytes: bytes, mode: int, overwrite: bool = True) -> None:
    """Write PEM bytes to a file using secure creation flags and set the specified permissions.

    Args:
        path:      The target file path.
        pem_bytes: The PEM-encoded key bytes.
        mode:      Octal file permission mode (e.g., ``0o600``).
        overwrite: When false, require exclusive creation instead of truncating an existing file.

    Raises:
        OSError: If the path is a symbolic link.
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


def public_key_fingerprint(public_pem: bytes) -> str:
    """Compute a SHA-256 fingerprint of a SubjectPublicKeyInfo PEM public key.

    The fingerprint is computed over the raw DER bytes of the SubjectPublicKeyInfo
    structure and returned as a colon-separated uppercase hex string.

    Args:
        public_pem: PEM-encoded SubjectPublicKeyInfo bytes.

    Returns:
        Colon-separated SHA-256 hex fingerprint, e.g. ``"AB:CD:EF:..."``.
    """
    import hashlib

    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, load_pem_public_key

    key = load_pem_public_key(public_pem)
    der = key.public_bytes(encoding=Encoding.DER, format=PublicFormat.SubjectPublicKeyInfo)
    digest = hashlib.sha256(der).hexdigest().upper()
    return ":".join(digest[i : i + 2] for i in range(0, len(digest), 2))
