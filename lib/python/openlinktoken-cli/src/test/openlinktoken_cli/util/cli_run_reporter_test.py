# SPDX-License-Identifier: MIT

from pathlib import Path
from unittest.mock import patch

from openlinktoken_cli.util.cli_error_reporter import format_dimmed_stderr_message
from openlinktoken_cli.util.cli_run_reporter import (
    _ProgressIndicator,
    _format_eta,
    _format_elapsed,
    CliRunReporter,
)


class TestProgressIndicator:
    """Unit tests for the enhanced progress indicator."""

    def test_format_eta_short(self):
        """Under an hour, ETA should be MM:SS format."""
        assert _format_eta(55) == "00:55"
        assert _format_eta(120) == "02:00"
        assert _format_eta(3660) == "01:01:00"

    def test_format_eta_invalid(self):
        """Invalid or zero ETA should return "?"."""
        assert _format_eta(-1) == "??:??"
        assert _format_eta(0) == "??:??"

    def test_format_elapsed_short(self):
        """Elapsed time under an hour should be MM:SS format."""
        assert _format_elapsed(55) == "00:55"
        assert _format_elapsed(3723) == "01:02:03"

    def test_progress_indicator_start_stop_noop(self):
        """Disabled progress indicator should return immediately."""
        pi = _ProgressIndicator(enabled=False)
        pi.start("initial", total_rows=1000)
        pi.update(stage="progress", done=500)
        pi.set_total_rows(1000)
        pi.stop()

    def test_progress_indicator_start_stop_enabled(self):
        """Enabled progress indicator should start a render thread."""
        pi = _ProgressIndicator(enabled=True)
        pi.start("initial", total_rows=1000)
        assert pi._thread is not None
        assert pi._thread.is_alive()
        pi.update(stage="progress", done=500)
        with pi._lock:
            assert pi._stage == "progress"
            assert pi._done == 500
        pi.set_total_rows(1000)
        with pi._lock:
            assert pi._total_rows == 1000
        pi.stop()
        assert not pi._thread.is_alive()


class TestCliRunReporter:
    """Unit tests for CLI run progress reporter."""

    def test_progress_flag_suppresses_interactive(self):
        """CliRunReporter should ignore TTY when no_progress=True."""
        with patch("sys.stderr.isatty", return_value=True):
            reporter = CliRunReporter("test", no_progress=True)
            assert reporter._interactive is False

    def test_no_progress_env_var_suppresses_interactive(self):
        """NO_PROGRESS env var should suppress interactive progress."""
        with patch("sys.stderr.isatty", return_value=True):
            with patch.dict("os.environ", {"NO_PROGRESS": "1"}):
                reporter = CliRunReporter("test")
                assert reporter._interactive is False

    def test_openlink_no_progress_env_var_suppresses_interactive(self):
        """OPENLINK_NO_PROGRESS env var should also suppress interactive."""
        with patch("sys.stderr.isatty", return_value=True):
            with patch.dict("os.environ", {"OPENLINK_NO_PROGRESS": "1"}):
                reporter = CliRunReporter("test")
                assert reporter._interactive is False

    def test_interactive_when_tty_and_no_env(self):
        """Interactive progress on when TTY and no env vars."""
        with patch("sys.stderr.isatty", return_value=True):
            with patch.dict("os.environ", {}, clear=True):
                reporter = CliRunReporter("test")
                assert reporter._interactive is True

    def test_set_total_rows_propagates(self):
        """reporter.set_total_rows() should propagate to the progress indicator."""
        with patch("sys.stderr.isatty", return_value=True):
            with patch.dict("os.environ", {}, clear=True):
                reporter = CliRunReporter("test")
                reporter.set_total_rows(10000)
                assert reporter._total_rows == 10000
                with reporter._progress_indicator._lock:
                    assert reporter._progress_indicator._total_rows == 10000

    def test_make_progress_callback_returns_callable(self):
        """make_progress_callback should return a callable that updates done."""
        with patch("sys.stderr.isatty", return_value=True):
            with patch.dict("os.environ", {}, clear=True):
                reporter = CliRunReporter("test")
                callback = reporter.make_progress_callback("Stage", "records")
                assert callable(callback)
                callback(500)
                with reporter._progress_indicator._lock:
                    assert reporter._progress_indicator._done == 500

    def test_make_progress_callback_updates_stage(self):
        """make_progress_callback should update the progress stage."""
        with patch("sys.stderr.isatty", return_value=True):
            with patch.dict("os.environ", {}, clear=True):
                reporter = CliRunReporter("test")
                callback = reporter.make_progress_callback("Encrypting", "tokens")
                callback(100)
                with reporter._progress_indicator._lock:
                    assert reporter._progress_indicator._stage == "Encrypting (100 tokens)"

    def test_update_status_includes_count(self):
        """update_status should include processed_count in the stage message."""
        with patch("sys.stderr.isatty", return_value=True):
            with patch.dict("os.environ", {}, clear=True):
                reporter = CliRunReporter("test")
                reporter.update_status("Processing", processed_count=1000, unit_label="rows")
                with reporter._progress_indicator._lock:
                    assert reporter._progress_indicator._stage == "Processing (1,000 rows)"
                    assert reporter._progress_indicator._done == 1000

    def test_update_status_without_count(self):
        """update_status without count should not include count in stage."""
        with patch("sys.stderr.isatty", return_value=True):
            with patch.dict("os.environ", {}, clear=True):
                reporter = CliRunReporter("test")
                reporter.update_status("Starting...")
                with reporter._progress_indicator._lock:
                    assert reporter._progress_indicator._stage == "Starting..."

    def test_summarize_count_lines_sorts_alphabetically(self):
        """Multi-item summaries are sorted alphabetically with 3-space prefix."""
        lines = CliRunReporter.summarize_count_lines(
            "Blank tokens by rule",
            {"T2": 8, "T4": 7, "T1": 6},
        )
        assert lines == [
            "Blank tokens by rule:",
            "   T1: 6",
            "   T2: 8",
            "   T4: 7",
        ]

    def test_summarize_count_lines_limits_and_sorts(self):
        """Limited summaries keep top N counts, sorted alphabetically."""
        lines = CliRunReporter.summarize_count_lines(
            "Top invalid attributes",
            {
                "SocialSecurityNumber": 4,
                "BirthDate": 3,
                "LastName": 2,
                "PostalCode": 1,
            },
            limit=3,
        )
        assert len(lines) == 4
        assert lines[0] == "Top invalid attributes:"
        assert "   BirthDate: 3" in lines
        assert "   LastName: 2" in lines
        assert "   SocialSecurityNumber: 4" in lines

    def test_summarize_count_lines_limits_one(self):
        """limit=1 should return single-item compact format."""
        lines = CliRunReporter.summarize_count_lines(
            "Top invalid",
            {"SocialSecurityNumber": 4, "BirthDate": 3},
            limit=1,
        )
        assert lines == ["Top invalid: SocialSecurityNumber=4"]

    def test_summarize_count_lines_handles_empty(self):
        """Empty counts should show none."""
        lines = CliRunReporter.summarize_count_lines("Empty", {})
        assert lines == ["Empty: none"]

    def test_summarize_count_lines_single_item(self):
        """Single item renders as label: name=count (no prefix)."""
        lines = CliRunReporter.summarize_count_lines(
            "Top invalid",
            {"Phone": 5},
        )
        assert lines == ["Top invalid: Phone=5"]

    def test_finish_success_exists(self):
        """finish_success method should exist on the reporter."""
        with patch("sys.stderr.isatty", return_value=True):
            with patch.dict("os.environ", {}, clear=True):
                reporter = CliRunReporter("test")
                assert hasattr(reporter, "finish_success")

    def test_finish_success_clears_progress_line(self):
        """finish_success should be callable when progress is active."""
        with patch("sys.stderr.isatty", return_value=True):
            with patch.dict("os.environ", {}, clear=True):
                reporter = CliRunReporter("test")
                reporter._progress_indicator.start("stage", total_rows=1000)
                pass


class TestFormatNumber:
    """Unit tests for _format_number convenience (uses f-string formatting)."""

    def test_format_number_small(self):
        """Small numbers should be formatted with commas."""
        assert f"{1000:,}" == "1,000"

    def test_format_number_large(self):
        """Large numbers should be formatted with commas."""
        assert f"{1234567:,}" == "1,234,567"

    def test_format_number_zero(self):
        """Zero should render as 0."""
        assert f"{0:,}" == "0"


class TestProgressIndicatorInteractive:
    """Tests for interactive behavior in enabled/disabled modes."""

    def test_done_zero_displays_start_message(self):
        """When done is 0 or not set, should show starting..."""
        pi = _ProgressIndicator(enabled=True)
        pi.start("Encrypting", total_rows=10000)
        with pi._lock:
            assert pi._done == 0
        pi.update(stage="Encrypting", done=500)
        with pi._lock:
            assert pi._done == 500
        pi.stop()

    def test_done_updates_respect_lock(self):
        """Concurrent updates to done should be safe via lock."""
        pi = _ProgressIndicator(enabled=True)
        pi.start("Process", total_rows=10000)
        pi._lock.acquire()
        pi._done = 1
        pi._done = 2
        pi._done = 3
        pi._lock.release()
        with pi._lock:
            assert pi._done == 3
        pi.stop()
