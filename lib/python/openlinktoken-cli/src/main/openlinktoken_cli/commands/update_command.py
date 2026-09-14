# SPDX-License-Identifier: MIT

import hashlib
import json
import logging
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from openlinktoken.metadata import Metadata
from openlinktoken_cli.util.version_checker import VersionChecker

logger = logging.getLogger(__name__)

_GITHUB_API_BASE = "https://api.github.com/repos/TruvetaPublic/OpenLinkToken"
_REQUEST_TIMEOUT_SECONDS = 30
_OS_SYSTEM_ALIASES = {
    "darwin": "macos",
}


class UpdateCommand:
    """
    Update command - self-update the Open Link Token CLI to the latest release.

    Downloads, verifies (SHA-256 checksum when available), and replaces the
    running binary/package with the specified or latest release.
    """

    @staticmethod
    def register_subcommand(subparsers):
        """Register the update subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "update",
            help="Update Open Link Token CLI to the latest release",
            description=(
                "Self-update the Open Link Token CLI to the latest (or a specified) release.\n\n"
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
                "Error: Could not fetch release information from GitHub. Please check your network connection.",
                file=sys.stderr,
            )
            return 1

        tag = release_info.get("tag_name", "")
        latest_version = tag.lstrip("v")

        # Already up to date?
        if not target_version_tag and not UpdateCommand._is_newer(latest_version, current_version):
            print(f"Open Link Token is already up to date ({tag}).")
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
            print(f"Would update Open Link Token from v{current_version} to {tag}.")
            print(f"  Asset : {asset_name}")
            print(f"  URL   : {asset_url}")
            if checksum_asset:
                print(f"  Checksum: {checksum_asset['name']}")
            return 0

        # Confirmation prompt (skip when --yes or non-interactive)
        if not skip_confirm and sys.stdin.isatty():
            try:
                answer = input(f"Update Open Link Token from v{current_version} to {tag}? [y/N] ").strip().lower()
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
                expected = UpdateCommand._fetch_checksum(checksum_asset["browser_download_url"], asset_name)
                if expected:
                    actual = UpdateCommand._sha256_file(tmp_path)
                    if actual != expected:
                        print(
                            f"Error: Checksum verification failed.\n  Expected: {expected}\n  Actual  : {actual}",
                            file=sys.stderr,
                        )
                        tmp_path.unlink(missing_ok=True)
                        return 1

            # Replace the complete bundle when available. Keep the raw binary path
            # for older releases and older installations.
            expected_entrypoint_name = asset_name.split("-", 1)[0] if asset_name else ""
            if asset_name.lower().endswith(".zip"):
                result = UpdateCommand._replace_bundle(tmp_path, expected_entrypoint_name)
            else:
                result = UpdateCommand._replace_binary(tmp_path, expected_entrypoint_name)
            if result != 0:
                tmp_path.unlink(missing_ok=True)
                return result

        finally:
            # Clean up temp file if still present
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

        print(f"Open Link Token successfully updated to {tag}.")
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
            req = Request(url, headers={"User-Agent": "openlinktoken-cli"})
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

        version = str(release_info.get("tag_name", "")).lstrip("v")
        expected_names = UpdateCommand._expected_asset_names(version, system, machine)
        assets_by_name = {
            asset.get("name", "").lower(): asset
            for asset in assets
            if not asset.get("name", "").lower().endswith((".sha256", ".sha256sum"))
        }
        for expected_name in expected_names:
            asset = assets_by_name.get(expected_name.lower())
            if asset is not None:
                return asset

        # Keep compatibility with pre-bundle releases whose versioned asset
        # names did not match the release tag exactly.
        legacy_suffixes = {
            "linux": ("-linux-x86_64",),
            "macos": UpdateCommand._legacy_macos_suffixes(machine),
            "windows": ("-windows-x86_64.exe",),
        }
        for asset in assets:
            name = asset.get("name", "").lower()
            if name.startswith("openlinktoken-v") and name.endswith(legacy_suffixes.get(system, ())):
                return asset

        return None

    @staticmethod
    def _expected_asset_names(version: str, system: str, machine: str) -> tuple[str, ...]:
        """Return exact bundle-first asset names for a platform."""
        if system == "linux" and machine in {"x86_64", "amd64"}:
            return (
                f"olt-cli-{version}-linux-x64.zip",
                f"olt-v{version}-linux-x86_64",
                f"openlinktoken-v{version}-linux-x86_64",
            )
        if system == "macos" and machine in {"x86_64", "amd64", "arm64", "aarch64"}:
            architecture = "arm64" if machine in {"arm64", "aarch64"} else "x86_64"
            return (
                f"olt-cli-{version}-macos-{architecture}.zip",
                f"olt-v{version}-macos-{architecture}",
                f"openlinktoken-v{version}-macos-{architecture}",
                f"olt-cli-{version}-macos-universal.zip",
                f"olt-v{version}-macos-universal",
                f"openlinktoken-v{version}-macos-universal",
            )
        if system == "windows" and machine in {"x86_64", "amd64", "x64"}:
            return (
                f"olt-cli-{version}-windows-x64.zip",
                f"olt-v{version}-windows-x86_64.exe",
                f"openlinktoken-v{version}-windows-x86_64.exe",
            )
        return ()

    @staticmethod
    def _legacy_macos_suffixes(machine: str) -> tuple[str, ...]:
        """Return legacy macOS asset suffixes compatible with the current architecture."""
        if machine in {"arm64", "aarch64"}:
            return ("-macos-arm64", "-macos-universal")
        if machine in {"x86_64", "amd64", "x64"}:
            return ("-macos-x86_64", "-macos-universal")
        return ()

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
            req = Request(url, headers={"User-Agent": "openlinktoken-cli"})
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
            req = Request(url, headers={"User-Agent": "openlinktoken-cli"})
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
    def _resolve_target_binary(expected_entrypoint_name: str) -> Optional[Path]:
        """Locate the installed CLI entry point without selecting the interpreter."""
        python_interpreter = Path(sys.executable).resolve()
        target = UpdateCommand._find_target_binary()
        if target is not None:
            return target

        argv0: Optional[Path] = None
        if sys.argv and sys.argv[0]:
            argv0 = Path(sys.argv[0]).resolve()
        if (
            argv0 is not None
            and argv0.is_file()
            and argv0.name == expected_entrypoint_name
            and argv0 != python_interpreter
        ):
            return argv0
        return None

    @staticmethod
    def _replace_binary(src: Path, expected_entrypoint_name: str) -> int:
        """
        Replace the current executable with *src*.

        Returns 0 on success, non-zero on failure.
        """
        target = UpdateCommand._resolve_target_binary(expected_entrypoint_name)
        if target is None:
            return UpdateCommand._print_target_not_found_error()

        if not os.access(str(target.parent), os.W_OK):
            print(
                f"Error: Insufficient permissions to write to {target.parent}.\n"
                f"Try running with elevated privileges (e.g. sudo) or download manually from:\n"
                f"  https://github.com/TruvetaPublic/OpenLinkToken/releases",
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
    def _replace_bundle(src: Path, expected_entrypoint_name: str) -> int:
        """Extract and install a complete PyInstaller bundle."""
        target = UpdateCommand._resolve_target_binary(expected_entrypoint_name)
        if target is None:
            return UpdateCommand._print_target_not_found_error()
        if not os.access(str(target.parent), os.W_OK):
            print(f"Error: Insufficient permissions to write to {target.parent}.", file=sys.stderr)
            return 1

        entrypoint_name = "olt.exe" if platform.system().lower() == "windows" else "olt"
        try:
            with tempfile.TemporaryDirectory(prefix="olt-update-") as temp_dir:
                extracted_dir = Path(temp_dir) / "extracted"
                extracted_dir.mkdir()
                with zipfile.ZipFile(src) as archive:
                    UpdateCommand._extract_bundle(archive, extracted_dir)

                executable = next(extracted_dir.rglob(entrypoint_name), None)
                if executable is None or not executable.is_file():
                    print(
                        f"Error: Release bundle does not contain {entrypoint_name}.",
                        file=sys.stderr,
                    )
                    return 1

                if platform.system().lower() == "windows":
                    return UpdateCommand._schedule_windows_bundle_replacement(executable.parent, target)
                return UpdateCommand._replace_posix_bundle(executable.parent, target, entrypoint_name)
        except (OSError, zipfile.BadZipFile, ValueError) as exc:
            print(f"Error: Could not install CLI bundle: {exc}", file=sys.stderr)
            return 1

    @staticmethod
    def _extract_bundle(archive: zipfile.ZipFile, destination: Path) -> None:
        """Extract a bundle after rejecting unsafe archive paths."""
        destination_root = destination.resolve()
        for member in archive.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Unsafe path in release bundle: {member.filename}")
            resolved_path = (destination / member_path).resolve()
            if os.path.commonpath((str(destination_root), str(resolved_path))) != str(destination_root):
                raise ValueError(f"Unsafe path in release bundle: {member.filename}")
            archive.extract(member, destination)

    @staticmethod
    def _replace_posix_bundle(source_bundle: Path, target: Path, entrypoint_name: str) -> int:
        """Atomically switch the POSIX launcher to a staged bundle."""
        bundle_dir = target.resolve().parent if target.is_symlink() else target.parent / ".olt"
        staged_bundle = bundle_dir.parent / f".olt-staged-{os.getpid()}"
        old_bundle = bundle_dir.parent / f".olt-previous-{os.getpid()}"
        launcher_tmp = target.parent / f".olt-launcher-{os.getpid()}"
        shutil.copytree(source_bundle, staged_bundle)

        try:
            if bundle_dir.exists() or bundle_dir.is_symlink():
                os.replace(bundle_dir, old_bundle)
            os.replace(staged_bundle, bundle_dir)
            launcher_tmp.symlink_to(bundle_dir / entrypoint_name)
            os.replace(launcher_tmp, target)
        except OSError as exc:
            if launcher_tmp.exists() or launcher_tmp.is_symlink():
                launcher_tmp.unlink()
            if not bundle_dir.exists() and old_bundle.exists():
                os.replace(old_bundle, bundle_dir)
            print(f"Error: Could not replace CLI bundle: {exc}", file=sys.stderr)
            return 1
        finally:
            if old_bundle.is_symlink():
                old_bundle.unlink()
            elif old_bundle.exists():
                shutil.rmtree(old_bundle)
            if staged_bundle.exists():
                shutil.rmtree(staged_bundle)
        return 0

    @staticmethod
    def _schedule_windows_bundle_replacement(source_bundle: Path, target: Path) -> int:
        """Schedule replacement after the running Windows executable exits."""
        stage_dir = Path(tempfile.mkdtemp(prefix="olt-update-"))
        script = Path(tempfile.gettempdir()) / f"olt-update-{os.getpid()}.cmd"
        backup_dir = Path(tempfile.gettempdir()) / f"olt-update-previous-{os.getpid()}"
        try:
            shutil.copytree(source_bundle, stage_dir, dirs_exist_ok=True)
            target_dir = target.parent
            script.write_text(
                "@echo off\r\n"
                "setlocal\r\n"
                f'set "STAGED={stage_dir}"\r\n'
                f'set "TARGET={target_dir}"\r\n'
                f'set "BACKUP={backup_dir}"\r\n'
                ":wait\r\n"
                'move "%TARGET%" "%BACKUP%" >nul 2>&1\r\n'
                "if errorlevel 1 (timeout /t 1 /nobreak >nul & goto wait)\r\n"
                'move "%STAGED%" "%TARGET%" >nul 2>&1\r\n'
                'if errorlevel 1 (move "%BACKUP%" "%TARGET%" >nul 2>&1 & goto fail)\r\n'
                'rmdir /s /q "%BACKUP%" >nul 2>&1\r\n'
                "goto done\r\n"
                ":fail\r\n"
                'rmdir /s /q "%STAGED%" >nul 2>&1\r\n'
                ":done\r\n"
                'del /q "%~f0" >nul 2>&1\r\n',
                encoding="utf-8",
            )
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
            subprocess.Popen(["cmd.exe", "/d", "/c", str(script)], creationflags=creation_flags)
        except (OSError, shutil.Error) as exc:
            shutil.rmtree(stage_dir, ignore_errors=True)
            script.unlink(missing_ok=True)
            print(f"Error: Could not schedule Windows CLI update: {exc}", file=sys.stderr)
            return 1
        return 0

    @staticmethod
    def _print_target_not_found_error() -> int:
        """Report that the active standalone executable could not be located."""
        print(
            "Error: Unable to locate the olt executable to update.\n"
            "The updater could not find an 'olt' binary on PATH and\n"
            "cannot safely determine which file to overwrite.\n"
            "Please reinstall olt via your package manager or download\n"
            "the latest release from:\n"
            "  https://github.com/TruvetaPublic/OpenLinkToken/releases",
            file=sys.stderr,
        )
        return 1

    @staticmethod
    def _find_target_binary() -> Optional[Path]:
        """Locate the 'olt' script on PATH."""
        target = shutil.which("olt")
        return Path(target) if target else None

    # ------------------------------------------------------------------
    # Version comparison (reuse VersionChecker logic)
    # ------------------------------------------------------------------

    @staticmethod
    def _is_newer(candidate: str, current: str) -> bool:
        return VersionChecker._is_newer(candidate, current)
