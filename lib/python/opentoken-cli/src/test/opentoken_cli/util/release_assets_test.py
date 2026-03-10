"""
Copyright (c) Truveta. All rights reserved.
"""

import hashlib
import zipfile
from pathlib import Path

import pytest

from opentoken_cli.util.release_assets import create_release_assets


def _write_binary(dist_dir: Path, name: str, content: bytes) -> None:
    """Create a fake built CLI executable for release asset tests."""
    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / name).write_bytes(content)


def _expected_checksum(content: bytes, file_name: str) -> str:
    """Return the checksum file contents for an asset."""
    digest = hashlib.sha256(content).hexdigest()
    return f"{digest}  {file_name}\n"


class TestCreateReleaseAssets:
    """Unit tests for release asset preparation."""

    def test_creates_linux_release_assets_and_checksums(self, tmp_path):
        """Linux builds should emit updater binary, zip package, and checksum sidecars."""
        dist_dir = tmp_path / "dist"
        output_dir = tmp_path / "release-assets"
        binary_content = b"linux binary"
        _write_binary(dist_dir, "opentoken", binary_content)

        generated_paths = create_release_assets("2.1.0", "Linux", dist_dir, output_dir)

        generated_names = {path.name for path in generated_paths}
        assert generated_names == {
            "opentoken-v2.1.0-linux-x86_64",
            "opentoken-v2.1.0-linux-x86_64.sha256",
            "opentoken-cli-2.1.0-linux-x64.zip",
            "opentoken-cli-2.1.0-linux-x64.zip.sha256",
        }

        binary_path = output_dir / "opentoken-v2.1.0-linux-x86_64"
        assert binary_path.read_bytes() == binary_content
        assert (output_dir / f"{binary_path.name}.sha256").read_text() == _expected_checksum(
            binary_content, binary_path.name
        )

        zip_path = output_dir / "opentoken-cli-2.1.0-linux-x64.zip"
        with zipfile.ZipFile(zip_path) as archive:
            archived_binary_name = "opentoken-cli-2.1.0-linux-x64/opentoken"
            assert archive.namelist() == [archived_binary_name]
            assert archive.read(archived_binary_name) == binary_content

        assert (output_dir / f"{zip_path.name}.sha256").read_text() == _expected_checksum(
            zip_path.read_bytes(), zip_path.name
        )

    def test_normalizes_v_prefixed_versions_for_windows_assets(self, tmp_path):
        """Windows builds should keep the .exe binary name while normalizing the version string."""
        dist_dir = tmp_path / "dist"
        output_dir = tmp_path / "release-assets"
        binary_content = b"windows binary"
        _write_binary(dist_dir, "opentoken.exe", binary_content)

        create_release_assets("v2.1.0", "windows", dist_dir, output_dir)

        binary_path = output_dir / "opentoken-v2.1.0-windows-x86_64.exe"
        assert binary_path.read_bytes() == binary_content

        with zipfile.ZipFile(output_dir / "opentoken-cli-2.1.0-windows-x64.zip") as archive:
            assert archive.namelist() == ["opentoken-cli-2.1.0-windows-x64/opentoken.exe"]

    def test_rejects_unsupported_runner_os(self, tmp_path):
        """Unsupported runner names should fail fast with a clear error."""
        with pytest.raises(ValueError, match="Unsupported runner OS"):
            create_release_assets("2.1.0", "Solaris", tmp_path / "dist", tmp_path / "release-assets")

    def test_requires_built_executable_to_exist(self, tmp_path):
        """Preparing release assets should fail if PyInstaller output is missing."""
        with pytest.raises(FileNotFoundError, match="Expected built executable"):
            create_release_assets("2.1.0", "Linux", tmp_path / "dist", tmp_path / "release-assets")
