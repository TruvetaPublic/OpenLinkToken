"""
Copyright (c) Truveta. All rights reserved.

Unit tests for the VersionChecker utility.
"""

import json
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from opentoken_cli.util.version_checker import VersionChecker, start_version_check

_CURRENT = "2.0.0"
_NEWER = "2.1.0"
_OLDER = "1.9.0"


# ---------------------------------------------------------------------------
# Helper: build a fake cache payload
# ---------------------------------------------------------------------------


def _make_cache(latest: str, age_hours: float = 0.0) -> dict:
    ts = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    return {
        "last_checked": ts.isoformat(),
        "latest_version": latest,
        "current_version": _CURRENT,
    }


# ---------------------------------------------------------------------------
# VersionChecker._is_newer
# ---------------------------------------------------------------------------


class TestIsNewer:
    """Tests for the semver comparison helper."""

    def test_newer_patch(self):
        assert VersionChecker._is_newer("2.0.1", "2.0.0")

    def test_newer_minor(self):
        assert VersionChecker._is_newer("2.1.0", "2.0.0")

    def test_newer_major(self):
        assert VersionChecker._is_newer("3.0.0", "2.0.0")

    def test_same_version(self):
        assert not VersionChecker._is_newer("2.0.0", "2.0.0")

    def test_older(self):
        assert not VersionChecker._is_newer("1.9.0", "2.0.0")

    def test_prerelease_vs_release(self):
        # 2.0.0-alpha is older than 2.0.0
        assert VersionChecker._is_newer("2.0.0", "2.0.0-alpha")

    def test_alpha_not_newer_than_same_alpha(self):
        assert not VersionChecker._is_newer("2.0.0-alpha", "2.0.0-alpha")


# ---------------------------------------------------------------------------
# Disable logic
# ---------------------------------------------------------------------------


class TestIsDisabled:
    """Tests for the opt-out mechanisms."""

    def test_disabled_via_flag(self):
        checker = VersionChecker(_CURRENT, no_update_check=True)
        assert checker._is_disabled()

    def test_disabled_via_env(self, monkeypatch):
        monkeypatch.setenv("OPENTOKEN_DISABLE_UPDATE_CHECK", "1")
        checker = VersionChecker(_CURRENT)
        assert checker._is_disabled()

    def test_not_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("OPENTOKEN_DISABLE_UPDATE_CHECK", raising=False)
        checker = VersionChecker(_CURRENT)
        assert not checker._is_disabled()

    def test_not_disabled_when_env_zero(self, monkeypatch):
        monkeypatch.setenv("OPENTOKEN_DISABLE_UPDATE_CHECK", "0")
        checker = VersionChecker(_CURRENT)
        assert not checker._is_disabled()

    def test_start_does_nothing_when_disabled(self):
        checker = VersionChecker(_CURRENT, no_update_check=True)
        checker.start()
        assert checker._thread is None


# ---------------------------------------------------------------------------
# Cache read / write
# ---------------------------------------------------------------------------


class TestCache:
    """Tests for cache read/write behaviour."""

    def test_cache_miss_when_absent(self, tmp_path):
        checker = VersionChecker(_CURRENT)
        with patch.object(VersionChecker, "_get_cache_path", return_value=tmp_path / "missing.json"):
            assert checker._read_cache() is None

    def test_cache_hit_when_fresh(self, tmp_path):
        cache_path = tmp_path / "update-check.json"
        cache_path.write_text(json.dumps(_make_cache(_NEWER, age_hours=1.0)))

        checker = VersionChecker(_CURRENT)
        with patch.object(VersionChecker, "_get_cache_path", return_value=cache_path):
            result = checker._read_cache()
        assert result == _NEWER

    def test_cache_miss_when_expired(self, tmp_path):
        cache_path = tmp_path / "update-check.json"
        cache_path.write_text(json.dumps(_make_cache(_NEWER, age_hours=25.0)))

        checker = VersionChecker(_CURRENT)
        with patch.object(VersionChecker, "_get_cache_path", return_value=cache_path):
            assert checker._read_cache() is None

    def test_write_cache_creates_file(self, tmp_path):
        cache_path = tmp_path / "sub" / "update-check.json"
        checker = VersionChecker(_CURRENT)
        with patch.object(VersionChecker, "_get_cache_path", return_value=cache_path):
            checker._write_cache(_NEWER)
        assert cache_path.exists()
        data = json.loads(cache_path.read_text())
        assert data["latest_version"] == _NEWER
        assert data["current_version"] == _CURRENT

    def test_write_cache_ignores_permission_error(self, tmp_path):
        checker = VersionChecker(_CURRENT)
        with patch.object(VersionChecker, "_get_cache_path", return_value=tmp_path / "no.json"):
            with patch("builtins.open", side_effect=PermissionError("read-only")):
                # Must not raise
                checker._write_cache(_NEWER)

    def test_read_cache_ignores_corrupt_file(self, tmp_path):
        cache_path = tmp_path / "update-check.json"
        cache_path.write_text("not-valid-json{{{")
        checker = VersionChecker(_CURRENT)
        with patch.object(VersionChecker, "_get_cache_path", return_value=cache_path):
            assert checker._read_cache() is None


# ---------------------------------------------------------------------------
# _fetch_latest_version
# ---------------------------------------------------------------------------


class TestFetchLatestVersion:
    """Tests for the GitHub API fetch helper."""

    def _make_response(self, tag_name: str):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"tag_name": tag_name}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_returns_version_without_v_prefix(self):
        checker = VersionChecker(_CURRENT)
        with patch("opentoken_cli.util.version_checker.urlopen", return_value=self._make_response(f"v{_NEWER}")):
            assert checker._fetch_latest_version() == _NEWER

    def test_returns_none_on_network_error(self):
        from urllib.error import URLError

        checker = VersionChecker(_CURRENT)
        with patch("opentoken_cli.util.version_checker.urlopen", side_effect=URLError("timeout")):
            assert checker._fetch_latest_version() is None

    def test_returns_none_on_json_error(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"bad-json"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        checker = VersionChecker(_CURRENT)
        with patch("opentoken_cli.util.version_checker.urlopen", return_value=mock_resp):
            assert checker._fetch_latest_version() is None


# ---------------------------------------------------------------------------
# _run integration (thread target)
# ---------------------------------------------------------------------------


class TestRun:
    """Tests for the background _run method."""

    def test_uses_cache_when_fresh(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "update-check.json"
        cache_path.write_text(json.dumps(_make_cache(_NEWER, age_hours=1.0)))

        checker = VersionChecker(_CURRENT)
        monkeypatch.delenv("OPENTOKEN_DISABLE_UPDATE_CHECK", raising=False)
        with patch.object(VersionChecker, "_get_cache_path", return_value=cache_path):
            checker._run()
        assert checker._result == _NEWER

    def test_fetches_when_cache_expired(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "update-check.json"
        cache_path.write_text(json.dumps(_make_cache(_NEWER, age_hours=25.0)))

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"tag_name": f"v{_NEWER}"}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        checker = VersionChecker(_CURRENT)
        monkeypatch.delenv("OPENTOKEN_DISABLE_UPDATE_CHECK", raising=False)
        with patch.object(VersionChecker, "_get_cache_path", return_value=cache_path):
            with patch("opentoken_cli.util.version_checker.urlopen", return_value=mock_resp):
                checker._run()
        assert checker._result == _NEWER


# ---------------------------------------------------------------------------
# _print_notice
# ---------------------------------------------------------------------------


class TestPrintNotice:
    """Tests for the update notice output."""

    def test_notice_printed_to_stderr(self, capsys, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        checker = VersionChecker(_CURRENT)
        checker._print_notice(_NEWER)
        captured = capsys.readouterr()
        assert _NEWER in captured.err
        assert _CURRENT in captured.err

    def test_notice_respects_no_color(self, capsys, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        checker = VersionChecker(_CURRENT)
        checker._print_notice(_NEWER)
        captured = capsys.readouterr()
        # No ANSI escape codes in output
        assert "\033[" not in captured.err


# ---------------------------------------------------------------------------
# wait_and_notify
# ---------------------------------------------------------------------------


class TestWaitAndNotify:
    """Tests for wait_and_notify."""

    def test_no_notice_when_no_thread(self, capsys):
        checker = VersionChecker(_CURRENT)
        checker.wait_and_notify()  # must not raise
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_notice_shown_after_command(self, capsys, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.delenv("OPENTOKEN_DISABLE_UPDATE_CHECK", raising=False)

        checker = VersionChecker(_CURRENT)
        checker._result = _NEWER  # inject result directly
        checker._thread = threading.Thread(target=lambda: None)
        checker._thread.start()

        with patch.object(sys.stderr, "isatty", return_value=True):
            checker.wait_and_notify()

        captured = capsys.readouterr()
        assert _NEWER in captured.err

    def test_no_notice_when_stderr_is_not_tty(self, capsys, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        checker = VersionChecker(_CURRENT)
        checker._result = _NEWER
        checker._thread = threading.Thread(target=lambda: None)
        checker._thread.start()

        with patch.object(sys.stderr, "isatty", return_value=False):
            checker.wait_and_notify()

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_no_notice_when_same_version(self, capsys):
        checker = VersionChecker(_CURRENT)
        checker._result = _CURRENT
        checker._thread = threading.Thread(target=lambda: None)
        checker._thread.start()

        checker.wait_and_notify()

        captured = capsys.readouterr()
        assert captured.err == ""


# ---------------------------------------------------------------------------
# start_version_check convenience function
# ---------------------------------------------------------------------------


class TestStartVersionCheck:
    """Tests for the module-level start_version_check helper."""

    def test_returns_checker_instance(self, monkeypatch):
        monkeypatch.setenv("OPENTOKEN_DISABLE_UPDATE_CHECK", "1")
        checker = start_version_check(_CURRENT)
        assert isinstance(checker, VersionChecker)

    def test_disabled_when_env_set(self, monkeypatch):
        monkeypatch.setenv("OPENTOKEN_DISABLE_UPDATE_CHECK", "1")
        checker = start_version_check(_CURRENT)
        assert checker._thread is None

    def test_disabled_via_flag(self, monkeypatch):
        monkeypatch.delenv("OPENTOKEN_DISABLE_UPDATE_CHECK", raising=False)
        checker = start_version_check(_CURRENT, no_update_check=True)
        assert checker._thread is None


# ---------------------------------------------------------------------------
# get_cache_path (public helper)
# ---------------------------------------------------------------------------


class TestGetCachePath:
    """Tests for the public cache path helper."""

    def test_returns_path_object(self):
        path = VersionChecker.get_cache_path()
        assert isinstance(path, Path)
        assert path.name == "update-check.json"

    def test_returns_dot_opentoken_path_under_home(self):
        expected_path = Path("/home/tester/.opentoken/update-check.json")

        with patch.object(Path, "home", return_value=Path("/home/tester")):
            with patch.dict("os.environ", {}, clear=True):
                path = VersionChecker.get_cache_path()

        assert path == expected_path

    def test_returns_dot_opentoken_path_under_appdata_on_windows(self, monkeypatch):
        appdata = r"C:\Users\tester\AppData\Roaming"
        expected_path = Path(appdata) / ".opentoken" / "update-check.json"

        monkeypatch.setenv("APPDATA", appdata)
        monkeypatch.setattr("sys.platform", "win32")

        path = VersionChecker.get_cache_path()

        assert path == expected_path
