# SPDX-License-Identifier: MIT
"""
Unit and integration tests for GenerateKeyPairCommand.
"""

import os
import stat
import sys
from unittest.mock import patch

import pytest

from openlinktoken_cli.commands.generate_key_pair_command import SUPPORTED_CURVES, GenerateKeyPairCommand
from openlinktoken_cli.commands.open_token_command import OpenLinkTokenCommand


class TestGenerateKeyPairCommandUnit:
    """Unit tests for GenerateKeyPairCommand helper methods."""

    # -------------------------------------------------------------------------
    # generate_key_pair: supported curves produce valid PEM output
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("curve", SUPPORTED_CURVES)
    def test_generate_key_pair_supported_curves(self, curve):
        """generate_key_pair returns valid PEM bytes for all supported curves."""
        private_pem, public_pem = GenerateKeyPairCommand.generate_key_pair(curve)

        assert private_pem.startswith(b"-----BEGIN PRIVATE KEY-----"), (
            f"Private key PEM header missing for curve {curve}"
        )
        assert b"-----END PRIVATE KEY-----" in private_pem, f"Private key PEM footer missing for curve {curve}"
        assert public_pem.startswith(b"-----BEGIN PUBLIC KEY-----"), f"Public key PEM header missing for curve {curve}"
        assert b"-----END PUBLIC KEY-----" in public_pem, f"Public key PEM footer missing for curve {curve}"

    def test_generate_key_pair_unsupported_curve_raises(self):
        """generate_key_pair raises ValueError for unsupported curve names."""
        with pytest.raises(ValueError, match="Unsupported curve"):
            GenerateKeyPairCommand.generate_key_pair("P-192")

    def test_generate_key_pair_each_call_produces_different_keys(self):
        """Two calls to generate_key_pair should produce different private keys."""
        pem1, _ = GenerateKeyPairCommand.generate_key_pair("P-256")
        pem2, _ = GenerateKeyPairCommand.generate_key_pair("P-256")
        assert pem1 != pem2, "Successive key-pair generations must produce unique keys"

    # -------------------------------------------------------------------------
    # _ensure_directory: creates directory with 700 permissions
    # -------------------------------------------------------------------------

    def test_ensure_directory_creates_with_700(self, tmp_path):
        """_ensure_directory creates the directory with owner-only permissions."""
        target = tmp_path / "dot_olt"
        GenerateKeyPairCommand._ensure_directory(target)

        assert target.is_dir(), "Directory must be created"
        if sys.platform != "win32":
            mode = stat.S_IMODE(os.stat(target).st_mode)
            assert mode == 0o700, f"Expected 700 but got {oct(mode)}"

    def test_ensure_directory_is_idempotent(self, tmp_path):
        """_ensure_directory does not raise when called on an existing directory."""
        target = tmp_path / "existing_dir"
        target.mkdir()
        GenerateKeyPairCommand._ensure_directory(target)  # Must not raise

    def test_ensure_directory_rejects_symlink(self, tmp_path):
        """_ensure_directory rejects symlink targets."""
        target = tmp_path / "dir-link"
        target.symlink_to(tmp_path, target_is_directory=True)

        with pytest.raises(OSError, match="must not be a symbolic link"):
            GenerateKeyPairCommand._ensure_directory(target)

    def test_ensure_directory_tightens_existing_permissions(self, tmp_path):
        """_ensure_directory resets an existing directory to owner-only permissions on POSIX."""
        if sys.platform == "win32":
            pytest.skip("POSIX permission test skipped on Windows")

        target = tmp_path / "existing-wide-open"
        target.mkdir()
        os.chmod(target, 0o755)

        GenerateKeyPairCommand._ensure_directory(target)

        mode = stat.S_IMODE(os.stat(target).st_mode)
        assert mode == 0o700, f"Expected 700 but got {oct(mode)}"

    # -------------------------------------------------------------------------
    # _write_key: writes bytes and sets permissions
    # -------------------------------------------------------------------------

    def test_write_key_creates_file_with_correct_content(self, tmp_path):
        """_write_key writes the supplied bytes to the target path."""
        path = tmp_path / "key.pem"
        content = b"-----BEGIN PRIVATE KEY-----\nABC\n-----END PRIVATE KEY-----\n"
        GenerateKeyPairCommand._write_key(path, content, 0o600)

        assert path.read_bytes() == content

    def test_write_key_sets_private_permissions(self, tmp_path):
        """_write_key sets 600 permissions for private keys on POSIX."""
        if sys.platform == "win32":
            pytest.skip("POSIX permission test skipped on Windows")

        path = tmp_path / "private.pem"
        GenerateKeyPairCommand._write_key(path, b"data", 0o600)

        mode = stat.S_IMODE(os.stat(path).st_mode)
        assert mode == 0o600, f"Expected 600 but got {oct(mode)}"

    def test_write_key_sets_public_permissions(self, tmp_path):
        """_write_key sets 644 permissions for public keys on POSIX."""
        if sys.platform == "win32":
            pytest.skip("POSIX permission test skipped on Windows")

        path = tmp_path / "public.pem"
        GenerateKeyPairCommand._write_key(path, b"data", 0o644)

        mode = stat.S_IMODE(os.stat(path).st_mode)
        assert mode == 0o644, f"Expected 644 but got {oct(mode)}"

    def test_write_key_rejects_symlink_path(self, tmp_path):
        """_write_key rejects symlink targets to avoid writing through links."""
        target = tmp_path / "real.pem"
        target.write_text("original")
        link_path = tmp_path / "linked.pem"
        link_path.symlink_to(target)

        with pytest.raises(OSError, match="must not be a symbolic link"):
            GenerateKeyPairCommand._write_key(link_path, b"data", 0o600)


class TestGenerateKeyPairCommandIntegration:
    """Integration tests that exercise the full CLI path via OpenLinkTokenCommand.execute."""

    # -------------------------------------------------------------------------
    # Happy paths: all supported curves
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("curve", SUPPORTED_CURVES)
    def test_all_supported_curves(self, tmp_path, curve):
        """generate-key-pair succeeds for every supported --curve value."""
        key_name = f"test-{curve.replace('-', '').lower()}"
        with patch.dict(os.environ, {}):
            with patch("pathlib.Path.home", return_value=tmp_path):
                exit_code = OpenLinkTokenCommand.execute(
                    [
                        "generate-key-pair",
                        "--curve",
                        curve,
                        "--name",
                        key_name,
                    ]
                )

        openlinktoken_dir = tmp_path / ".openlinktoken"
        assert exit_code == 0, f"generate-key-pair should succeed for curve {curve}"
        assert (openlinktoken_dir / f"{key_name}.private.pem").exists()
        assert (openlinktoken_dir / f"{key_name}.public.pem").exists()

    # -------------------------------------------------------------------------
    # Default name: openlinktoken-<ISO8601-date>
    # -------------------------------------------------------------------------

    def test_default_name_uses_iso_date(self, tmp_path):
        """When --name is omitted, files are named openlinktoken-<YYYY-MM-DD>.*."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenLinkTokenCommand.execute(["generate-key-pair"])

        assert exit_code == 0
        openlinktoken_dir = tmp_path / ".openlinktoken"
        matches = list(openlinktoken_dir.glob("openlinktoken-????-??-??.private.pem"))
        assert matches, "Expected a private key file matching openlinktoken-<ISO-date>.private.pem"

    # -------------------------------------------------------------------------
    # Default curve: P-256
    # -------------------------------------------------------------------------

    def test_default_curve_is_p256(self, tmp_path):
        """When --curve is omitted, P-256 is used (PKCS#8 PEM is produced)."""
        key_name = "default-curve"
        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenLinkTokenCommand.execute(["generate-key-pair", "--name", key_name])

        assert exit_code == 0
        openlinktoken_dir = tmp_path / ".openlinktoken"
        priv = (openlinktoken_dir / f"{key_name}.private.pem").read_bytes()
        assert priv.startswith(b"-----BEGIN PRIVATE KEY-----")

    # -------------------------------------------------------------------------
    # No silent overwrite
    # -------------------------------------------------------------------------

    def test_fails_when_key_already_exists(self, tmp_path):
        """Second run without --force must exit non-zero."""
        key_name = "existing-key"
        with patch("pathlib.Path.home", return_value=tmp_path):
            first = OpenLinkTokenCommand.execute(["generate-key-pair", "--name", key_name])
            second = OpenLinkTokenCommand.execute(["generate-key-pair", "--name", key_name])

        assert first == 0, "First run should succeed"
        assert second != 0, "Second run without --force must fail"

    def test_force_overwrites_existing_keys(self, tmp_path):
        """--force allows overwriting existing key files."""
        key_name = "force-key"
        with patch("pathlib.Path.home", return_value=tmp_path):
            OpenLinkTokenCommand.execute(["generate-key-pair", "--name", key_name])
            exit_code = OpenLinkTokenCommand.execute(["generate-key-pair", "--name", key_name, "--force"])

        assert exit_code == 0, "--force overwrite should succeed"
        openlinktoken_dir = tmp_path / ".openlinktoken"
        assert (openlinktoken_dir / f"{key_name}.private.pem").exists()
        assert (openlinktoken_dir / f"{key_name}.public.pem").exists()

    # -------------------------------------------------------------------------
    # Unsupported curve
    # -------------------------------------------------------------------------

    def test_unsupported_curve_exits_nonzero(self, tmp_path):
        """Unsupported --curve value must produce a non-zero exit code."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenLinkTokenCommand.execute(["generate-key-pair", "--curve", "P-192"])

        assert exit_code != 0, "Unsupported curve must exit non-zero"

    @pytest.mark.parametrize("invalid_name", ["../escape", "nested/key", r"nested\\key", "C:\\temp\\key"])
    def test_invalid_name_exits_nonzero(self, tmp_path, invalid_name):
        """Unsafe key basenames must be rejected."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenLinkTokenCommand.execute(["generate-key-pair", "--name", invalid_name])

        assert exit_code != 0, "Unsafe key name must exit non-zero"

        openlinktoken_dir = tmp_path / ".openlinktoken"
        if openlinktoken_dir.exists():
            assert list(openlinktoken_dir.glob("*.pem")) == [], "Unsafe key names must not create output files"

    # -------------------------------------------------------------------------
    # Directory and file permissions
    # -------------------------------------------------------------------------

    def test_directory_created_with_700_permissions(self, tmp_path):
        """~/.openlinktoken/ is created with 700 permissions."""
        if sys.platform == "win32":
            pytest.skip("POSIX permission test skipped on Windows")

        key_name = "perm-dir-test"
        with patch("pathlib.Path.home", return_value=tmp_path):
            OpenLinkTokenCommand.execute(["generate-key-pair", "--name", key_name])

        openlinktoken_dir = tmp_path / ".openlinktoken"
        mode = stat.S_IMODE(os.stat(openlinktoken_dir).st_mode)
        assert mode == 0o700, f"Directory must have 700 permissions but got {oct(mode)}"

    def test_private_key_has_600_permissions(self, tmp_path):
        """Private key file is written with 600 permissions."""
        if sys.platform == "win32":
            pytest.skip("POSIX permission test skipped on Windows")

        key_name = "perm-priv-test"
        with patch("pathlib.Path.home", return_value=tmp_path):
            OpenLinkTokenCommand.execute(["generate-key-pair", "--name", key_name])

        priv = tmp_path / ".openlinktoken" / f"{key_name}.private.pem"
        mode = stat.S_IMODE(os.stat(priv).st_mode)
        assert mode == 0o600, f"Private key must have 600 permissions but got {oct(mode)}"

    def test_public_key_has_644_permissions(self, tmp_path):
        """Public key file is written with 644 permissions."""
        if sys.platform == "win32":
            pytest.skip("POSIX permission test skipped on Windows")

        key_name = "perm-pub-test"
        with patch("pathlib.Path.home", return_value=tmp_path):
            OpenLinkTokenCommand.execute(["generate-key-pair", "--name", key_name])

        pub = tmp_path / ".openlinktoken" / f"{key_name}.public.pem"
        mode = stat.S_IMODE(os.stat(pub).st_mode)
        assert mode == 0o644, f"Public key must have 644 permissions but got {oct(mode)}"

    # -------------------------------------------------------------------------
    # Output paths printed to stdout
    # -------------------------------------------------------------------------

    def test_output_paths_printed_to_stdout(self, tmp_path, capsys):
        """Both key file paths are printed to stdout on success."""
        key_name = "stdout-test"
        with patch("pathlib.Path.home", return_value=tmp_path):
            OpenLinkTokenCommand.execute(["generate-key-pair", "--name", key_name])

        captured = capsys.readouterr()
        assert "private" in captured.out.lower(), "stdout must mention the private key path"
        assert "public" in captured.out.lower(), "stdout must mention the public key path"
