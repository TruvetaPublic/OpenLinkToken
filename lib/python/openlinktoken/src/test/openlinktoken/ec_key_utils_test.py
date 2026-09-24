# SPDX-License-Identifier: MIT

import os
import stat
from pathlib import Path

import pytest

from openlinktoken.ec_key_utils import (
    ensure_directory,
    fingerprint_to_kid,
    get_curve_class,
    resolve_key_name,
    write_key,
)


def test_get_curve_class_rejects_unsupported_curve():
    """Unsupported curve names must raise a descriptive ValueError."""
    with pytest.raises(ValueError, match="Unsupported curve 'P-999'"):
        get_curve_class("P-999")


def test_resolve_key_name_returns_date_based_default_for_none():
    """None or empty names should produce a date-prefixed default basename."""
    result = resolve_key_name(None)
    assert result.startswith("openlinktoken-")

    result = resolve_key_name("")
    assert result.startswith("openlinktoken-")


def test_resolve_key_name_returns_stripped_name_for_valid_input():
    """Valid simple names should be returned as-is after stripping whitespace."""
    assert resolve_key_name("my-key") == "my-key"
    assert resolve_key_name("  my-key  ") == "my-key"


def test_resolve_key_name_rejects_dot_traversal():
    """Dot-only names used for traversal must be rejected."""
    with pytest.raises(ValueError):
        resolve_key_name(".")
    with pytest.raises(ValueError):
        resolve_key_name("..")


def test_resolve_key_name_rejects_path_separators():
    """Names containing path separators must be rejected."""
    with pytest.raises(ValueError):
        resolve_key_name("a/b")
    with pytest.raises(ValueError):
        resolve_key_name("a\\b")


def test_resolve_key_name_rejects_colon():
    """Names containing colons (Windows drive prefixes) must be rejected."""
    with pytest.raises(ValueError):
        resolve_key_name("C:key")


def test_fingerprint_to_kid_rejects_empty_fingerprint():
    """An empty or whitespace-only fingerprint must raise ValueError."""
    with pytest.raises(ValueError, match="Fingerprint must not be empty"):
        fingerprint_to_kid("")
    with pytest.raises(ValueError, match="Fingerprint must not be empty"):
        fingerprint_to_kid("   ")


def test_ensure_directory_rejects_symlink(tmp_path: Path):
    """A symlinked directory path must raise OSError."""
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    link_dir = tmp_path / "link"
    link_dir.symlink_to(real_dir)

    with pytest.raises(OSError, match="must not be a symbolic link"):
        ensure_directory(link_dir)


def test_ensure_directory_rejects_non_directory(tmp_path: Path):
    """A path that exists as a regular file must raise NotADirectoryError."""
    file_path = tmp_path / "not_a_dir"
    file_path.write_text("content")

    with pytest.raises(NotADirectoryError):
        ensure_directory(file_path)


def test_ensure_directory_creates_missing_directory(tmp_path: Path):
    """Missing directories should be created with 0o700 permissions."""
    target = tmp_path / "new_dir"
    ensure_directory(target)
    assert target.is_dir()


def test_write_key_rejects_symlink(tmp_path: Path):
    """A symlinked key file path must raise OSError."""
    real_file = tmp_path / "real.pem"
    real_file.write_bytes(b"content")
    link_file = tmp_path / "link.pem"
    link_file.symlink_to(real_file)

    with pytest.raises(OSError, match="must not be a symbolic link"):
        write_key(link_file, b"new-pem-content", 0o600)


def test_write_key_writes_pem_bytes(tmp_path: Path):
    """PEM bytes should be written to the specified path with the specified permissions."""
    key_path = tmp_path / "test.pem"
    pem_bytes = b"-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n"
    write_key(key_path, pem_bytes, 0o600)

    assert key_path.read_bytes() == pem_bytes
    if os.name != "nt":
        assert stat.S_IMODE(os.stat(key_path).st_mode) == 0o600
