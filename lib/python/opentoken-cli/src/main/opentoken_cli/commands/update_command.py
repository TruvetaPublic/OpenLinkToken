"""
Copyright (c) Truveta. All rights reserved.
"""

import hashlib
import json
import logging
import os
import platform
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from opentoken.metadata import Metadata
from opentoken_cli.util.version_checker import VersionChecker

logger = logging.getLogger(__name__)

_GITHUB_API_BASE = "https://api.github.com/repos/TruvetaPublic/OpenToken"
_REQUEST_TIMEOUT_SECONDS = 30
_OS_SYSTEM_ALIASES = {
    "darwin": "macos",
}


class UpdateCommand:
    """
    Update command - self-update the OpenToken CLI to the latest release.

    Downloads, verifies (SHA-256 checksum when available), and replaces the
    running binary/package with the specified or latest release.
    """

    @staticmethod
    def register_subcommand(subparsers):
        """Register the update subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "update",
            help="Update OpenToken CLI to the latest release",
            description=(
                "Self-update the OpenToken CLI to the latest (or a specified) release.\n\n"
                "Downloads the correct asset for the current platform, verifies its checksum,\n"
                "and replaces the current binary in-place."
            ),
        )

        parser.add_argument(
            "--version",
            dest="target_version",
            default=None,
            help="Install a specific release version tag (default: latest)",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            dest="dry_run",
            help="Show what would be updated without applying changes",
        )

        parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            default=False,
            dest="yes",
            help="Skip confirmation prompt",
        )

        parser.set_defaults(func=UpdateCommand.execute)

    @staticmethod
    def execute(args) -> int:
        """Execute the update command."""
        current_version = Metadata.DEFAULT_VERSION
        target_version_tag = getattr(args, "target_version", None)
        dry_run = getattr(args, "dry_run", False)
        skip_confirm = getattr(args, "yes", False)

        # Resolve which version to install
        if target_version_tag:
            # Normalise: accept "v2.1.0" or "2.1.0"
            if not target_version_tag.startswith("v"):
                target_version_tag = f"v{target_version_tag}"
            release_info = UpdateCommand._fetch_release_by_tag(target_version_tag)
        else:
            release_info = UpdateCommand._fetch_latest_release()

        if release_info is None:
            print(
                "Error: Could not fetch release information from GitHub. "
                "Please check your network connection.",
                file=sys.stderr,
            )
            return 1

        tag = release_info.get("tag_name", "")
        latest_version = tag.lstrip("v")

        # Already up to date?
        if not target_version_tag and not UpdateCommand._is_newer(latest_version, current_version):
            print(f"OpenToken is already up to date ({tag}).")
            return 0

        # Find the correct asset for this platform
        asset = UpdateCommand._find_asset(release_info)
        if asset is None:
            system = platform.system().lower()
            machine = platform.machine().lower()
            print(
                f"Error: No suitable release asset found for platform {system}/{machine}.\n"
                f"Please download manually from: {release_info.get('html_url', '')}",
                file=sys.stderr,
            )
            return 1

        asset_name = asset["name"]
        asset_url = asset["browser_download_url"]
        checksum_asset = UpdateCommand._find_checksum_asset(release_info, asset_name)

        if dry_run:
            print(f"Would update OpenToken from v{current_version} to {tag}.")
            print(f"  Asset : {asset_name}")
            print(f"  URL   : {asset_url}")
            if checksum_asset:
                print(f"  Checksum: {checksum_asset['name']}")
            return 0

        # Confirmation prompt (skip when --yes or non-interactive)
        if not skip_confirm and sys.stdin.isatty():
            try:
                answer = input(
                    f"Update OpenToken from v{current_version} to {tag}? [y/N] "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""
            if answer not in ("y", "yes"):
                print("Update cancelled.")
                return 0

        # Download the asset to a temp file
        print(f"Downloading {asset_name}...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(asset_name).suffix) as tmp:
            tmp_path = Path(tmp.name)

        try:
            if not UpdateCommand._download_file(asset_url, tmp_path):
                tmp_path.unlink(missing_ok=True)
                return 1

            # Verify checksum if available
            if checksum_asset:
                print("Verifying checksum...")
                expected = UpdateCommand._fetch_checksum(
                    checksum_asset["browser_download_url"], asset_name
                )
                if expected:
                    actual = UpdateCommand._sha256_file(tmp_path)
                    if actual != expected:
                        print(
                            f"Error: Checksum verification failed.\n"
                            f"  Expected: {expected}\n"
                            f"  Actual  : {actual}",
                            file=sys.stderr,
                        )
                        tmp_path.unlink(missing_ok=True)
                        return 1

            # Replace current installation
            current_executable = Path(sys.executable)
            result = UpdateCommand._replace_binary(tmp_path, current_executable, asset_name)
            if result != 0:
                tmp_path.unlink(missing_ok=True)
                return result

        finally:
            # Clean up temp file if still present
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

        print(f"OpenToken successfully updated to {tag}.")
        return 0

    # ------------------------------------------------------------------
    # GitHub API helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fetch_latest_release() -> Optional[dict]:
        """Fetch the latest release JSON from GitHub."""
        url = f"{_GITHUB_API_BASE}/releases/latest"
        return UpdateCommand._get_json(url)

    @staticmethod
    def _fetch_release_by_tag(tag: str) -> Optional[dict]:
        """Fetch a specific release by tag name from GitHub."""
        url = f"{_GITHUB_API_BASE}/releases/tags/{tag}"
        return UpdateCommand._get_json(url)

    @staticmethod
    def _get_json(url: str) -> Optional[dict]:
        """Perform a GET request and return the parsed JSON body."""
        try:
            req = Request(url, headers={"User-Agent": "opentoken-cli"})
            with urlopen(req, timeout=_REQUEST_TIMEOUT_SECONDS) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (URLError, OSError, json.JSONDecodeError):
            return None

    # ------------------------------------------------------------------
    # Asset selection
    # ------------------------------------------------------------------

    @staticmethod
    def _find_asset(release_info: dict) -> Optional[dict]:
        """Find the release asset that matches the current platform/architecture."""
        assets = release_info.get("assets", [])
        raw_system = platform.system().lower()
        system = _OS_SYSTEM_ALIASES.get(raw_system, raw_system)
        machine = platform.machine().lower()

        # Normalise common machine names
        arch_aliases = {
            "x86_64": ["x86_64", "amd64", "x64"],
            "aarch64": ["aarch64", "arm64"],
            "arm64": ["aarch64", "arm64"],
        }
        archs = arch_aliases.get(machine, [machine])

        for asset in assets:
            name_lower = asset["name"].lower()
            # Skip checksum files
            if name_lower.endswith(".sha256") or name_lower.endswith(".sha256sum"):
                continue
            if system in name_lower and any(a in name_lower for a in archs):
                return asset

        # Fallback: try just system match
        for asset in assets:
            name_lower = asset["name"].lower()
            if name_lower.endswith(".sha256") or name_lower.endswith(".sha256sum"):
                continue
            if system in name_lower:
                return asset

        return None

    @staticmethod
    def _find_checksum_asset(release_info: dict, asset_name: str) -> Optional[dict]:
        """Find the SHA-256 checksum asset for the given asset, if available."""
        for asset in release_info.get("assets", []):
            name = asset["name"]
            if name in (f"{asset_name}.sha256", f"{asset_name}.sha256sum"):
                return asset
        return None

    # ------------------------------------------------------------------
    # Download and verification
    # ------------------------------------------------------------------

    @staticmethod
    def _download_file(url: str, dest: Path) -> bool:
        """Download *url* to *dest*. Returns True on success."""
        try:
            req = Request(url, headers={"User-Agent": "opentoken-cli"})
            with urlopen(req, timeout=_REQUEST_TIMEOUT_SECONDS) as resp, dest.open("wb") as f:
                shutil.copyfileobj(resp, f)
            return True
        except (URLError, OSError) as exc:
            print(f"Error: Download failed: {exc}", file=sys.stderr)
            return False

    @staticmethod
    def _fetch_checksum(url: str, asset_name: str) -> Optional[str]:
        """
        Fetch a checksum file and extract the SHA-256 for *asset_name*.

        Returns the lowercase hex digest, or None if it cannot be parsed.
        """
        try:
            req = Request(url, headers={"User-Agent": "opentoken-cli"})
            with urlopen(req, timeout=_REQUEST_TIMEOUT_SECONDS) as resp:
                text = resp.read().decode("utf-8")
            for line in text.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1].lstrip("*") == asset_name:
                    return parts[0].lower()
            return None
        except Exception as exc:
            logger.debug("Could not fetch checksum for %s: %s", asset_name, exc)
            return None

    @staticmethod
    def _sha256_file(path: Path) -> str:
        """Compute the SHA-256 hex digest of *path*."""
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Binary replacement
    # ------------------------------------------------------------------

    @staticmethod
    def _replace_binary(src: Path, current_executable: Path, asset_name: str) -> int:
        """
        Replace the current executable with *src*.

        Returns 0 on success, non-zero on failure.
        """
        # Determine target path: for a wheel-installed script the executable is
        # the Python interpreter; we instead look for the "opentoken" script on PATH.
        target = UpdateCommand._find_target_binary()
        if target is None:
            # Fallback: try to infer the CLI entrypoint from sys.argv[0], but only
            # if it is a real file, matches the expected asset name, and is not
            # the Python interpreter itself.
            argv0: Optional[Path] = None
            if sys.argv and sys.argv[0]:
                argv0 = Path(sys.argv[0])
            if (
                argv0 is not None
                and argv0.is_file()
                and argv0.name == asset_name
                and argv0 != Path(sys.executable)
            ):
                target = argv0
            else:
                print(
                    "Error: Unable to locate the opentoken executable to update.\n"
                    "The updater could not find an 'opentoken' binary on PATH and\n"
                    "cannot safely determine which file to overwrite.\n"
                    "Please reinstall opentoken via your package manager or download\n"
                    "the latest release from:\n"
                    "  https://github.com/TruvetaPublic/OpenToken/releases",
                    file=sys.stderr,
                )
                return 1

        if not os.access(str(target.parent), os.W_OK):
            print(
                f"Error: Insufficient permissions to write to {target.parent}.\n"
                f"Try running with elevated privileges (e.g. sudo) or download manually from:\n"
                f"  https://github.com/TruvetaPublic/OpenToken/releases",
                file=sys.stderr,
            )
            return 1

        # Copy with preserved permissions
        try:
            shutil.copy2(str(src), str(target))
            # Ensure the binary is executable
            current_mode = target.stat().st_mode
            target.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError as exc:
            print(f"Error: Could not replace binary: {exc}", file=sys.stderr)
            return 1

        return 0

    @staticmethod
    def _find_target_binary() -> Optional[Path]:
        """Locate the 'opentoken' script on PATH."""
        target = shutil.which("opentoken")
        return Path(target) if target else None

    # ------------------------------------------------------------------
    # Version comparison (reuse VersionChecker logic)
    # ------------------------------------------------------------------

    @staticmethod
    def _is_newer(candidate: str, current: str) -> bool:
        return VersionChecker._is_newer(candidate, current)
