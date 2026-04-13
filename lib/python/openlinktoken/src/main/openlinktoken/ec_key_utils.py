"""
Copyright (c) Truveta. All rights reserved.

Shared utilities for ECDH key management used by initiate-exchange and
exchange-config consumers.

Note: The exchange-config workflow is Python-CLI only. The Java counterpart
(``EcKeyUtils.java``) is a placeholder stub that references this module.
"""

import logging
import os
import stat
from datetime import date
from pathlib import Path, PureWindowsPath
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

SUPPORTED_CURVES = ["P-256", "P-384", "P-521"]


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
        return f"openlinktoken-{date.today().isoformat()}"

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


def _curve_name_from_private_key(private_key) -> str:
    """Map a cryptography EC private key's curve to an OpenLinkToken curve name."""
    curve_name_map = {
        "secp256r1": "P-256",
        "secp384r1": "P-384",
        "secp521r1": "P-521",
    }
    curve_name = curve_name_map.get(private_key.curve.name)
    if curve_name is None:
        raise ValueError(f"Unsupported EC private key curve '{private_key.curve.name}'.")
    return curve_name


def derive_public_key_from_private_pem(private_pem: bytes) -> Tuple[bytes, str]:
    """Load an EC private key PEM and return its public key PEM plus OpenLinkToken curve name."""
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, load_pem_private_key

    private_key = load_pem_private_key(private_pem, password=None)
    public_pem = private_key.public_key().public_bytes(
        encoding=Encoding.PEM,
        format=PublicFormat.SubjectPublicKeyInfo,
    )
    return public_pem, _curve_name_from_private_key(private_key)


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
        os.chmod(directory, stat.S_IRWXU)
    except (NotImplementedError, PermissionError) as error:
        logger.warning("Could not set directory permissions on %s: %s", directory, error)


def write_key(path: Path, pem_bytes: bytes, mode: int, overwrite: bool = True) -> None:
    """Write PEM bytes to a file using secure creation flags and set the specified permissions.

    Args:
        path: The target file path.
        pem_bytes: The PEM-encoded key bytes.
        mode: Octal file permission mode (for example, ``0o600``).
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
    except (NotImplementedError, PermissionError) as error:
        logger.warning("Could not set file permissions on %s: %s", path, error)


def public_key_fingerprint(public_pem: bytes) -> str:
    """Compute a SHA-256 fingerprint of a SubjectPublicKeyInfo PEM public key."""
    import hashlib

    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, load_pem_public_key

    key = load_pem_public_key(public_pem)
    der = key.public_bytes(encoding=Encoding.DER, format=PublicFormat.SubjectPublicKeyInfo)
    digest = hashlib.sha256(der).hexdigest().upper()
    return ":".join(digest[index : index + 2] for index in range(0, len(digest), 2))


def fingerprint_to_kid(fingerprint: str) -> str:
    """Convert a SHA-256 public-key fingerprint into the portable JWE recipient id."""
    normalized = fingerprint.strip()
    if not normalized:
        raise ValueError("Fingerprint must not be empty.")

    return f"sha256:{normalized.lower().replace(':', '-')}"
