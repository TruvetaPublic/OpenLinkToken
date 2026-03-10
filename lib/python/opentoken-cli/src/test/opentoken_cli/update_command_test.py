"""
Copyright (c) Truveta. All rights reserved.

Unit tests for the UpdateCommand utility.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from opentoken_cli.commands.update_command import UpdateCommand

# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------

_FAKE_VERSION = "2.0.0"
_NEWER_VERSION = "2.1.0"
_NEWER_TAG = "v2.1.0"


def _make_release(tag: str = _NEWER_TAG, assets: list | None = None) -> dict:
    """Build a minimal GitHub release JSON object."""
    if assets is None:
        assets = [
            {
                "name": f"opentoken-{tag}-linux-x86_64",
                "browser_download_url": f"https://example.com/opentoken-{tag}-linux-x86_64",
            },
            {
                "name": f"opentoken-{tag}-linux-x86_64.sha256",
                "browser_download_url": f"https://example.com/opentoken-{tag}-linux-x86_64.sha256",
            },
        ]
    return {
        "tag_name": tag,
        "html_url": f"https://github.com/TruvetaPublic/OpenToken/releases/tag/{tag}",
        "assets": assets,
    }


def _make_args(
    target_version: str | None = None,
    dry_run: bool = False,
    yes: bool = True,
) -> MagicMock:
    args = MagicMock()
    args.target_version = target_version
    args.dry_run = dry_run
    args.yes = yes
    return args


# ---------------------------------------------------------------------------
# _find_asset — OS alias normalisation
# ---------------------------------------------------------------------------


class TestFindAsset:
    """Tests for platform asset selection."""

    def test_linux_x86_64(self):
        release = _make_release(assets=[{"name": "opentoken-v2.1.0-linux-x86_64", "browser_download_url": "u"}])
        with patch("platform.system", return_value="Linux"), patch("platform.machine", return_value="x86_64"):
            asset = UpdateCommand._find_asset(release)
        assert asset is not None
        assert "linux" in asset["name"]

    def test_darwin_matches_macos(self):
        """platform.system() returns 'Darwin' on macOS; should match 'macos' assets."""
        release = _make_release(assets=[{"name": "opentoken-v2.1.0-macos-arm64", "browser_download_url": "u"}])
        with patch("platform.system", return_value="Darwin"), patch("platform.machine", return_value="arm64"):
            asset = UpdateCommand._find_asset(release)
        assert asset is not None
        assert "macos" in asset["name"]

    def test_no_matching_asset_returns_none(self):
        release = _make_release(assets=[{"name": "opentoken-v2.1.0-windows-x86_64.exe", "browser_download_url": "u"}])
        with patch("platform.system", return_value="Linux"), patch("platform.machine", return_value="x86_64"):
            asset = UpdateCommand._find_asset(release)
        assert asset is None

    def test_checksum_files_skipped(self):
        """SHA256 sidecar files must not be selected as the main asset."""
        release = _make_release(
            assets=[
                {"name": "opentoken-v2.1.0-linux-x86_64.sha256", "browser_download_url": "u1"},
                {"name": "opentoken-v2.1.0-linux-x86_64", "browser_download_url": "u2"},
            ]
        )
        with patch("platform.system", return_value="Linux"), patch("platform.machine", return_value="x86_64"):
            asset = UpdateCommand._find_asset(release)
        assert asset is not None
        assert not asset["name"].endswith(".sha256")


# ---------------------------------------------------------------------------
# execute — dry-run
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_dry_run_prints_would_update(self, capsys):
        release = _make_release()
        args = _make_args(dry_run=True)
        with (
            patch.object(UpdateCommand, "_fetch_latest_release", return_value=release),
            patch("platform.system", return_value="Linux"),
            patch("platform.machine", return_value="x86_64"),
        ):
            rc = UpdateCommand.execute(args)

        assert rc == 0
        captured = capsys.readouterr()
        assert "Would update" in captured.out
        assert _NEWER_TAG in captured.out

    def test_dry_run_no_download(self):
        release = _make_release()
        args = _make_args(dry_run=True)
        with (
            patch.object(UpdateCommand, "_fetch_latest_release", return_value=release),
            patch.object(UpdateCommand, "_download_file") as mock_dl,
            patch("platform.system", return_value="Linux"),
            patch("platform.machine", return_value="x86_64"),
        ):
            UpdateCommand.execute(args)

        mock_dl.assert_not_called()


# ---------------------------------------------------------------------------
# execute — asset not found
# ---------------------------------------------------------------------------


class TestAssetNotFound:
    def test_returns_nonzero_when_no_asset(self, capsys):
        release = _make_release(assets=[])
        args = _make_args()
        with (
            patch.object(UpdateCommand, "_fetch_latest_release", return_value=release),
            patch("platform.system", return_value="Linux"),
            patch("platform.machine", return_value="x86_64"),
        ):
            rc = UpdateCommand.execute(args)

        assert rc != 0
        assert "No suitable release asset" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# execute — already up to date
# ---------------------------------------------------------------------------


class TestAlreadyUpToDate:
    def test_up_to_date_message(self, capsys):
        from opentoken.metadata import Metadata

        current_ver = Metadata.DEFAULT_VERSION
        same_tag = f"v{current_ver}"
        release = _make_release(
            tag=same_tag,
            assets=[
                {"name": f"opentoken-{same_tag}-linux-x86_64", "browser_download_url": "u"},
            ],
        )
        args = _make_args()

        with patch.object(UpdateCommand, "_fetch_latest_release", return_value=release):
            rc = UpdateCommand.execute(args)

        assert rc == 0
        assert "already up to date" in capsys.readouterr().out.lower()


# ---------------------------------------------------------------------------
# execute — checksum mismatch
# ---------------------------------------------------------------------------


class TestChecksumMismatch:
    def test_checksum_mismatch_returns_nonzero(self, tmp_path, capsys):
        release = _make_release()
        fake_binary = tmp_path / "opentoken-v2.1.0-linux-x86_64"
        fake_binary.write_bytes(b"fake binary content")

        args = _make_args()
        with (
            patch.object(UpdateCommand, "_fetch_latest_release", return_value=release),
            patch.object(UpdateCommand, "_download_file", side_effect=lambda url, dest: dest.write_bytes(b"x") or True),
            patch.object(UpdateCommand, "_fetch_checksum", return_value="expected_sha256_value"),
            patch.object(UpdateCommand, "_sha256_file", return_value="actual_different_sha256"),
            patch("platform.system", return_value="Linux"),
            patch("platform.machine", return_value="x86_64"),
        ):
            rc = UpdateCommand.execute(args)

        assert rc != 0
        assert "Checksum verification failed" in capsys.readouterr().err

    def test_checksum_ok_proceeds(self, tmp_path):
        release = _make_release()
        checksum = "aabbccdd" * 8  # 64 hex chars

        args = _make_args()
        with (
            patch.object(UpdateCommand, "_fetch_latest_release", return_value=release),
            patch.object(UpdateCommand, "_download_file", side_effect=lambda url, dest: dest.write_bytes(b"x") or True),
            patch.object(UpdateCommand, "_fetch_checksum", return_value=checksum),
            patch.object(UpdateCommand, "_sha256_file", return_value=checksum),
            patch.object(UpdateCommand, "_replace_binary", return_value=0),
            patch("platform.system", return_value="Linux"),
            patch("platform.machine", return_value="x86_64"),
        ):
            rc = UpdateCommand.execute(args)

        assert rc == 0


# ---------------------------------------------------------------------------
# _replace_binary — safe fallback logic
# ---------------------------------------------------------------------------


class TestReplaceBinary:
    def test_uses_path_binary_when_found(self, tmp_path):
        src = tmp_path / "new_binary"
        src.write_bytes(b"new content")
        target = tmp_path / "opentoken"
        target.write_bytes(b"old content")

        with patch.object(UpdateCommand, "_find_target_binary", return_value=target):
            rc = UpdateCommand._replace_binary(src, "opentoken")

        assert rc == 0
        assert target.read_bytes() == b"new content"

    def test_does_not_overwrite_python_interpreter(self, tmp_path, capsys):
        src = tmp_path / "new_binary"
        src.write_bytes(b"new content")

        # Simulate PATH search finding nothing
        with (
            patch.object(UpdateCommand, "_find_target_binary", return_value=None),
            patch.object(Path, "is_file", return_value=False),
        ):
            rc = UpdateCommand._replace_binary(src, "opentoken")

        assert rc != 0
        assert "Unable to locate" in capsys.readouterr().err

    def test_argv0_fallback_when_name_matches(self, tmp_path):
        src = tmp_path / "new_binary"
        src.write_bytes(b"new content")
        fake_entrypoint = tmp_path / "opentoken"
        fake_entrypoint.write_bytes(b"old content")

        with (
            patch.object(UpdateCommand, "_find_target_binary", return_value=None),
            patch.object(sys, "argv", [str(fake_entrypoint)]),
        ):
            rc = UpdateCommand._replace_binary(src, "opentoken")

        assert rc == 0
        assert fake_entrypoint.read_bytes() == b"new content"

    def test_permission_error_returns_nonzero(self, tmp_path, capsys):
        src = tmp_path / "new_binary"
        src.write_bytes(b"content")
        target = tmp_path / "opentoken"
        target.write_bytes(b"old")

        with (
            patch.object(UpdateCommand, "_find_target_binary", return_value=target),
            patch("shutil.copy2", side_effect=OSError("Permission denied")),
        ):
            rc = UpdateCommand._replace_binary(src, "opentoken")

        assert rc != 0


# ---------------------------------------------------------------------------
# _fetch_latest_release / network error handling
# ---------------------------------------------------------------------------


class TestNetworkErrorHandling:
    def test_returns_nonzero_when_release_fetch_fails(self, capsys):
        args = _make_args()
        with patch.object(UpdateCommand, "_fetch_latest_release", return_value=None):
            rc = UpdateCommand.execute(args)

        assert rc != 0
        assert "Could not fetch release" in capsys.readouterr().err
