# SPDX-License-Identifier: MIT

import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from openlinktoken_cli.extension.extension_manifest import (
    CURRENT_CORE_VERSION,
    ManifestValidationError,
    is_core_compatible,
    parse_manifest,
)
from openlinktoken_cli.extension.extension_registry import ExtensionRegistry
from openlinktoken_cli.util.app_paths import get_openlinktoken_home

logger = logging.getLogger(__name__)

_GITHUB_API_URL = "https://api.github.com/repos/TruvetaPublic/OpenLinkToken/releases/latest"
_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
_REQUEST_TIMEOUT_SECONDS = 2
_ENV_DISABLE = "OLT_DISABLE_UPDATE_CHECK"
_CACHE_FILENAME = "update-check.json"
_EXTENSION_CACHE_FILENAME = "extension-update-check.json"
_EXTENSION_CACHE_TTL_SECONDS = 24 * 60 * 60


class VersionChecker:
    """
    Asynchronous version checker that compares the running version against the latest
    GitHub release and optionally notifies the user of an available update.

    The check runs in a daemon thread and writes its result to stderr only after the
    primary command has finished, so it never blocks or delays normal usage.
    """

    def __init__(self, current_version: str, no_update_check: bool = False):
        """
        Initialize the VersionChecker.

        Args:
            current_version: The currently running version string (e.g. "2.2.0").
            no_update_check: When True the checker is disabled entirely.
        """
        self._current_version = current_version
        self._no_update_check = no_update_check
        self._result: Optional[str] = None  # latest version fetched/cached
        self._extension_results: list[tuple[str, str, str]] = []
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Launch the background version check.

        Does nothing when update checks are disabled via the ``--no-update-check``
        flag or the ``OLT_DISABLE_UPDATE_CHECK`` environment variable.
        """
        if self._is_disabled():
            return

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def wait_and_notify(self) -> None:
        """
        Wait briefly for the background check to finish and, if a newer version
        is available, print an update notice to stderr.

        This method should be called **after** the primary command has completed
        so it never adds latency to the critical path or noticeably delays
        process termination. If the background check is still running after a
        non-blocking check, no notice is printed.
        """
        if self._thread is None:
            return

        # Use a very short timeout to avoid delaying CLI termination.
        # If the background thread is still running, skip printing the notice
        # rather than blocking.
        self._thread.join(timeout=0.0)

        if self._thread.is_alive():
            return

        if not self._stderr_is_interactive():
            return

        if self._result and self._is_newer(self._result, self._current_version):
            if self._notice_due():
                self._print_notice(self._result)
                self._record_notice_shown()
        self._print_extension_notices()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_disabled(self) -> bool:
        if self._no_update_check:
            return True
        if os.getenv(_ENV_DISABLE, "").strip() == "1":
            return True
        return False

    def _run(self) -> None:
        """Entry point for the daemon thread."""
        try:
            cached = self._read_cache()
            if cached is not None:
                self._result = cached
            else:
                latest = self._fetch_latest_version()
                if latest:
                    self._result = latest
                    self._write_cache(latest)
            self._check_extension_updates()
        except Exception as exc:
            logger.debug("Version check failed", exc_info=exc)

    def _check_extension_updates(self) -> None:
        """Check registered vendor manifests without importing extension code."""
        cache = self._read_extension_cache()
        changed = False
        for name, metadata in ExtensionRegistry.load().items():
            manifest_url = metadata.get("update_manifest_url")
            if not manifest_url:
                continue
            cached = cache.get(manifest_url)
            payload = None
            if cached and self._cache_entry_fresh(cached):
                payload = cached.get("payload")
            if payload is None:
                payload = self._fetch_extension_manifest(manifest_url)
                if payload is None:
                    continue
                cache[manifest_url] = {
                    "last_checked": datetime.now(timezone.utc).isoformat(),
                    "payload": payload,
                }
                changed = True
            try:
                manifest = parse_manifest(payload, expected_name=name)
                if not is_core_compatible(CURRENT_CORE_VERSION, manifest.core_specifier):
                    continue
                current = metadata.get("version", "0.0.0")
                latest = max(
                    (artifact.version for artifact in manifest.artifacts if artifact.version),
                    key=lambda value: self._version_key(value),
                    default=current,
                )
                if self._is_newer(latest, current):
                    self._extension_results.append((name, current, latest))
            except (ManifestValidationError, TypeError, ValueError):
                logger.debug("Ignoring invalid extension update manifest for %s", name)
        if changed:
            self._write_extension_cache(cache)

    @staticmethod
    def _version_key(value: str):
        """Return a comparable packaging version, with invalid values sorted last."""
        from packaging.version import Version

        try:
            return Version(value)
        except Exception:
            return Version("0")

    def _fetch_extension_manifest(self, url: str) -> Optional[dict]:
        """Fetch one HTTPS vendor manifest as JSON, never importing extension code."""
        try:
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.netloc:
                return None
            request = Request(url, headers={"User-Agent": "openlinktoken-cli"})
            with urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
                final_url = response.geturl()
                final = urlparse(final_url)
                if final.scheme != "https" or not final.netloc:
                    return None
                payload = json.loads(response.read().decode("utf-8"))
            return payload if isinstance(payload, dict) else None
        except (URLError, OSError, json.JSONDecodeError, TypeError, ValueError):
            return None

    def _fetch_latest_version(self) -> Optional[str]:
        """Query the GitHub Releases API and return the tag name."""
        try:
            req = Request(_GITHUB_API_URL, headers={"User-Agent": "openlinktoken-cli"})
            with urlopen(req, timeout=_REQUEST_TIMEOUT_SECONDS) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                tag = data.get("tag_name", "")
                return tag.lstrip("v") if tag else None
        except (URLError, OSError, json.JSONDecodeError, KeyError):
            return None

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_cache_path() -> Path:
        """Return the platform-appropriate path for the cache file."""
        return get_openlinktoken_home() / _CACHE_FILENAME

    @staticmethod
    def _get_extension_cache_path() -> Path:
        """Return the bounded cache path for extension manifests."""
        return get_openlinktoken_home() / _EXTENSION_CACHE_FILENAME

    def _read_extension_cache(self) -> dict:
        """Read the extension manifest cache, returning an empty cache on errors."""
        try:
            payload = json.loads(self._get_extension_cache_path().read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return {}

    def _write_extension_cache(self, cache: dict) -> None:
        """Persist extension manifest responses without affecting command execution."""
        try:
            path = self._get_extension_cache_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(cache), encoding="utf-8")
        except OSError:
            logger.debug("Could not write extension update cache", exc_info=True)

    @staticmethod
    def _cache_entry_fresh(entry: dict) -> bool:
        """Return whether one extension manifest cache entry is inside its TTL."""
        try:
            checked = datetime.fromisoformat(entry["last_checked"])
            if checked.tzinfo is None:
                checked = checked.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - checked).total_seconds() <= _EXTENSION_CACHE_TTL_SECONDS
        except (KeyError, TypeError, ValueError):
            return False

    def _read_cache(self) -> Optional[str]:
        """
        Read the cached version result if it exists and is not older than the TTL.

        Returns:
            The cached latest version string, or None if missing/expired.
        """
        try:
            cache_path = self._get_cache_path()
            if not cache_path.exists():
                return None

            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            last_checked_str = data.get("last_checked", "")
            last_checked = datetime.fromisoformat(last_checked_str)
            # Make aware if naive
            if last_checked.tzinfo is None:
                last_checked = last_checked.replace(tzinfo=timezone.utc)

            age_seconds = (datetime.now(timezone.utc) - last_checked).total_seconds()
            if age_seconds > _CACHE_TTL_SECONDS:
                return None

            return data.get("latest_version") or None
        except Exception as exc:
            logger.debug("Could not read version cache", exc_info=exc)
            return None

    def _write_cache(self, latest_version: str) -> None:
        """Write the fetched version to the cache file, silently ignoring errors."""
        try:
            cache_path = self._get_cache_path()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "last_checked": datetime.now(timezone.utc).isoformat(),
                "latest_version": latest_version,
                "current_version": self._current_version,
            }
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception as exc:
            logger.debug("Could not write version cache", exc_info=exc)

    def _notice_due(self) -> bool:
        """Return True if the update notice has not been shown in the last 24 hours."""
        try:
            cache_path = self._get_cache_path()
            if not cache_path.exists():
                return True
            with cache_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            last_notified_str = data.get("last_notified", "")
            if not last_notified_str:
                return True
            last_notified = datetime.fromisoformat(last_notified_str)
            if last_notified.tzinfo is None:
                last_notified = last_notified.replace(tzinfo=timezone.utc)
            age_seconds = (datetime.now(timezone.utc) - last_notified).total_seconds()
            return age_seconds < 0 or age_seconds > _CACHE_TTL_SECONDS
        except Exception as exc:
            logger.debug("Could not read last_notified from cache", exc_info=exc)
            return True

    def _record_notice_shown(self) -> None:
        """Stamp last_notified in the cache so the notice is suppressed for 24 hours."""
        try:
            cache_path = self._get_cache_path()
            data: dict = {}
            if cache_path.exists():
                try:
                    with cache_path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    pass
            data["last_notified"] = datetime.now(timezone.utc).isoformat()
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as exc:
            logger.debug("Could not record notice shown", exc_info=exc)

    # ------------------------------------------------------------------
    # Version comparison and notice
    # ------------------------------------------------------------------

    @staticmethod
    def _is_newer(candidate: str, current: str) -> bool:
        """
        Return True when *candidate* is strictly greater than *current*
        using semantic-version comparison.
        """
        from packaging.version import Version  # type: ignore[import]

        try:
            return Version(candidate) > Version(current)
        except Exception:
            return False

    def _print_notice(self, latest_version: str) -> None:
        """
        Write the update notice to stderr.
        Respects the ``NO_COLOR`` environment variable.
        """
        use_color = not os.getenv("NO_COLOR")
        yellow = "\033[33m" if use_color else ""
        reset = "\033[0m" if use_color else ""

        tag = f"v{latest_version}"
        current_tag = f"v{self._current_version}"

        lines = [
            f"{yellow}⚠ A new version of Open Link Token is available: {tag} (you have {current_tag}){reset}",
            f"   Release notes: https://github.com/TruvetaPublic/OpenLinkToken/releases/tag/{tag}",
            f"   Run 'olt update' to upgrade, or set {_ENV_DISABLE}=1 to silence this message.",
        ]
        try:
            print("\n".join(lines), file=sys.stderr)
        except Exception:
            pass

    def _print_extension_notices(self) -> None:
        """Print rate-limited extension notices after normal command output."""
        if not self._extension_results:
            return
        cache = self._read_extension_cache()
        now = datetime.now(timezone.utc)
        changed = False
        for name, current, latest in self._extension_results:
            entry = cache.get(name, {})
            try:
                last_notified = datetime.fromisoformat(entry.get("last_notified", ""))
                if last_notified.tzinfo is None:
                    last_notified = last_notified.replace(tzinfo=timezone.utc)
                age_seconds = (now - last_notified).total_seconds()
                if 0 <= age_seconds <= _EXTENSION_CACHE_TTL_SECONDS:
                    continue
            except (TypeError, ValueError):
                pass
            try:
                print(
                    f"⚠ Extension update available: {name} {current} -> {latest}. "
                    f"Run 'olt extension update {name} --yes'.",
                    file=sys.stderr,
                )
            except Exception:
                continue
            entry["last_notified"] = now.isoformat()
            cache[name] = entry
            changed = True
        if changed:
            self._write_extension_cache(cache)

    @staticmethod
    def _stderr_is_interactive() -> bool:
        """Return whether stderr is attached to an interactive terminal."""
        isatty = getattr(sys.stderr, "isatty", None)
        return bool(isatty and isatty())

    # ------------------------------------------------------------------
    # Convenience class method for simple one-shot usage in tests
    # ------------------------------------------------------------------

    @classmethod
    def get_latest_version_from_cache(cls, current_version: str) -> Optional[str]:
        """
        Return the cached latest version without making a network call.

        Useful for tests and tooling.
        """
        checker = cls(current_version)
        return checker._read_cache()

    @staticmethod
    def get_cache_path() -> Path:
        """Return the path where the cache file is stored (public for tests)."""
        return VersionChecker._get_cache_path()

    # ------------------------------------------------------------------
    # Module-level helper used by UpdateCommand
    # ------------------------------------------------------------------

    @staticmethod
    def fetch_latest_version_sync() -> Optional[str]:
        """
        Synchronously fetch the latest release version from the GitHub API.

        Returns:
            The latest version string (without leading 'v'), or None on error.
        """
        checker = VersionChecker("")
        return checker._fetch_latest_version()


def start_version_check(current_version: str, no_update_check: bool = False) -> VersionChecker:
    """
    Create a VersionChecker, start its background thread, and return it so the
    caller can later call ``wait_and_notify()`` after the primary command finishes.

    Args:
        current_version: The running version string.
        no_update_check: Whether to skip the check entirely.

    Returns:
        The started VersionChecker instance.
    """
    checker = VersionChecker(current_version, no_update_check=no_update_check)
    checker.start()
    return checker
