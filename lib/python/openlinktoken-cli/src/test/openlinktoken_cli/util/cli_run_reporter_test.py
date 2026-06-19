# SPDX-License-Identifier: MIT

from pathlib import Path
from unittest.mock import patch

from openlinktoken_cli.util.cli_error_reporter import format_dimmed_stderr_message
from openlinktoken_cli.util.cli_run_reporter import (
     _ProgressIndicator,
     _format_elapsed,
     _format_throughput,
    CliRunReporter,
)


class TestProgressIndicator:
    """Unit tests for the enhanced progress indicator."""

    def test_format_elapsed_short(self):
        """Elapsed time under an hour should be MM:SS format."""
        assert _format_elapsed(55) == "00:55"
        assert _format_elapsed(3723) == "01:02:03"

    def test_format_elapsed_hours(self):
        """Elapsed time over an hour should include hours."""
        assert _format_elapsed(3660) == "01:01:00"
        assert _format_elapsed(86400) == "24:00:00"

    def test_format_throughput_small(self):
        """Small throughput in rows/s."""
        assert _format_throughput(1.5) == "1.5 rows/s"
        assert _format_throughput(99.0) == "99.0 rows/s"

    def test_format_throughput_medium(self):
        """Medium throughput as whole rows/s."""
        assert _format_throughput(100.0) == "100 rows/s"
        assert _format_throughput(999.0) == "999 rows/s"

    def test_format_throughput_k(self):
        """Large throughput in K rows/s."""
        assert _format_throughput(1000.0) == "1.0 K rows/s"
        assert _format_throughput(1500.5) == "1.5 K rows/s"

    def test_format_throughput_m(self):
        """Very large throughput in M rows/s."""
        assert _format_throughput(1_000_000.0) == "1.0 M rows/s"
        assert _format_throughput(5_250_000.0) == "5.2 M rows/s"

    def test_progress_indicator_start_stop(self):
        """Enabled progress indicator should start and stop cleanly."""
        pi = _ProgressIndicator()
        pi.start()
        assert pi._thread is not None
        assert pi._thread.is_alive()
        pi.update(stage="Encrypting", done=500)
        with pi._lock:
            assert pi._stage == "Encrypting"
            assert pi._done == 500
        pi.set_total_rows(1000)
        with pi._lock:
            assert pi._total_rows == 1000
        pi.stop()
        assert not pi._thread.is_alive()

    def test_progress_update_via_lock(self):
        """Updates via _lock should be visible immediately."""
        pi = _ProgressIndicator()
        pi.start()
        pi.update(stage="Process", done=1)
        with pi._lock:
            assert pi._done == 1
        pi.stop()


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
                    assert reporter._progress_indicator._stage == "Encrypting"

    def test_update_status_includes_count(self):
        """update_status should include processed_count in the stage message."""
        with patch("sys.stderr.isatty", return_value=True):
            with patch.dict("os.environ", {}, clear=True):
                reporter = CliRunReporter("test")
                reporter.update_status("Processing", processed_count=1000, unit_label="rows")
                with reporter._progress_indicator._lock:
                    assert reporter._progress_indicator._stage == "Processing"
                    assert reporter._progress_indicator._done == 1000

    def test_update_status_without_count(self):
        """update_status without count should just update stage."""
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
