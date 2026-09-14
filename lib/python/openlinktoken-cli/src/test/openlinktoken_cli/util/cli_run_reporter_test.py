# SPDX-License-Identifier: MIT

import logging
import os
import re
from unittest.mock import patch

import pytest

from openlinktoken_cli.util.cli_run_reporter import (
    CliRunReporter,
    StatsProvider,
    _format_elapsed,
    _format_throughput,
    _format_throughput_parts,
    _ProgressIndicator,
)


class TestProgressIndicator:
    """Unit tests for the enhanced progress indicator."""

    @staticmethod
    def _rendered_lines(rendered: str) -> list[str]:
        normalized = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", rendered).replace("\r", "")
        return normalized.splitlines()

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

    def test_render_writes_single_line_progress_status(self):
        """Rendered progress should keep all core metrics on one terminal line."""
        pi = _ProgressIndicator()
        pi._start_time = 0.0
        pi.set_total_rows(200)
        pi.update(stage="Working", done=100)
        pi._running.set()

        writes: list[str] = []

        def _write(text: str) -> int:
            writes.append(text)
            pi._running.clear()
            return len(text)

        with (
            patch("shutil.get_terminal_size", return_value=os.terminal_size((160, 24))),
            patch("sys.stderr.write", side_effect=_write),
            patch("sys.stderr.flush"),
            patch("time.sleep", return_value=None),
            patch("time.perf_counter", return_value=10.0),
        ):
            pi._render()

        assert writes
        rendered_lines = self._rendered_lines("".join(writes))
        assert rendered_lines == ["⠋ Working | 100/200 rows (50.0%) | remaining 00:10 | 10.0 rows/s | elapsed 00:10"]

    def test_render_without_total_shows_placeholders(self):
        """When the total is unknown, the status line should show stable placeholders."""
        pi = _ProgressIndicator()
        pi._start_time = 0.0
        pi.update(stage="Working", done=25)
        pi._running.set()

        writes: list[str] = []

        def _write(text: str) -> int:
            writes.append(text)
            pi._running.clear()
            return len(text)

        with (
            patch("sys.stderr.write", side_effect=_write),
            patch("sys.stderr.flush"),
            patch("time.sleep", return_value=None),
            patch("time.perf_counter", return_value=5.0),
        ):
            pi._render()

        assert writes
        rendered_lines = self._rendered_lines("".join(writes))
        assert rendered_lines == ["⠋ Working | 25/-- rows (--) | remaining -- | 5.0 rows/s | elapsed 00:05"]

    def test_render_keeps_progress_to_terminal_width(self):
        """The live progress line should fit within terminal width."""
        pi = _ProgressIndicator()
        pi._start_time = 0.0
        pi.set_total_rows(200)
        pi.update(stage="Working", done=100)
        pi._running.set()

        writes: list[str] = []

        def _write(text: str) -> int:
            writes.append(text)
            pi._running.clear()
            return len(text)

        with (
            patch("shutil.get_terminal_size", return_value=os.terminal_size((80, 24))),
            patch("sys.stderr.write", side_effect=_write),
            patch("sys.stderr.flush"),
            patch("time.sleep", return_value=None),
            patch("time.perf_counter", return_value=10.0),
        ):
            pi._render()

        assert writes
        rendered_lines = self._rendered_lines("".join(writes))
        assert len(rendered_lines) == 1
        assert "100/200 rows (50.0%)" in rendered_lines[0]
        assert "remaining 00:10" in rendered_lines[0]
        assert len(rendered_lines[0].rstrip()) <= 80

    def test_render_uses_one_terminal_line_for_redraw(self):
        """A redraw should use one terminal line so cursor tracking cannot drift."""
        pi = _ProgressIndicator(use_color=False)
        pi._last_render_line_count = 7
        lines = ["header", "processed", "total", "complete", "throughput", "elapsed", "remaining"]
        writes: list[str] = []

        with (
            patch("shutil.get_terminal_size", return_value=os.terminal_size((160, 24))),
            patch("sys.stderr.write", side_effect=lambda text: writes.append(text) or len(text)),
            patch("sys.stderr.flush"),
        ):
            pi._write_render_block(lines)

        assert len(writes) == 1
        assert writes[0].startswith("\r\x1b[2K")
        assert "\x1b[6F" not in writes[0]
        assert "\n" not in writes[0]
        assert " | ".join(lines) in writes[0]

    def test_render_advances_spinner_on_fixed_interval_without_progress_updates(self):
        """The spinner should animate every 100 ms when progress remains unchanged."""
        pi = _ProgressIndicator(use_color=False)
        pi._start_time = 0.0
        pi.set_total_rows(100)
        pi.update(stage="Working", done=50)
        pi._running.set()

        clock = [0.0]
        writes: list[str] = []
        wait_timeouts: list[float] = []

        def _wait(timeout: float) -> bool:
            wait_timeouts.append(timeout)
            clock[0] += timeout
            return False

        def _perf_counter() -> float:
            return clock[0]

        def _write(text: str) -> int:
            writes.append(text)
            if len(writes) == 3:
                pi._running.clear()
            return len(text)

        with (
            patch("shutil.get_terminal_size", return_value=os.terminal_size((160, 24))),
            patch.object(pi._update_event, "wait", side_effect=_wait),
            patch("sys.stderr.write", side_effect=_write),
            patch("sys.stderr.flush"),
            patch("time.perf_counter", side_effect=_perf_counter),
        ):
            pi._render()

        assert len(writes) == 3
        assert wait_timeouts[1:] == pytest.approx([0.1, 0.1])
        rendered_lines = [self._rendered_lines(write)[0] for write in writes]
        assert [line[0] for line in rendered_lines] == ["⠋", "⠙", "⠹"]

    def test_render_with_stats_provider(self):
        """Extension stats providers should appear after core metrics in the status line."""
        pi = _ProgressIndicator()
        pi._start_time = 0.0
        pi.set_total_rows(1000)
        pi.update(stage="Processing", done=500)
        pi._running.set()

        class TestProvider:
            def get_metrics(self) -> list[tuple[str, str, str]]:
                return [("matched", "1,042", "rows"), ("errors", "3", "")]

        pi._stats_providers.append(TestProvider())

        writes: list[str] = []

        def _write(text: str) -> int:
            writes.append(text)
            pi._running.clear()
            return len(text)

        with (
            patch("shutil.get_terminal_size", return_value=os.terminal_size((300, 24))),
            patch("sys.stderr.write", side_effect=_write),
            patch("sys.stderr.flush"),
            patch("time.sleep", return_value=None),
            patch("time.perf_counter", return_value=10.0),
        ):
            pi._render()

        assert writes
        rendered_lines = self._rendered_lines("".join(writes))
        assert len(rendered_lines) == 1
        assert "matched: 1,042 rows" in rendered_lines[0]
        assert "errors: 3" in rendered_lines[0]

    def test_stats_provider_protocol(self):
        """Objects implementing get_metrics() should satisfy StatsProvider protocol."""

        class ValidProvider:
            def get_metrics(self) -> list[tuple[str, str, str]]:
                return [("test", "42", "items")]

        assert isinstance(ValidProvider(), StatsProvider)

    def test_format_throughput_parts(self):
        """_format_throughput_parts should split number and unit."""
        assert _format_throughput_parts(1.5) == ("1.5", "rows/s")
        assert _format_throughput_parts(100.0) == ("100", "rows/s")
        assert _format_throughput_parts(1500.0) == ("1.5 K", "rows/s")
        assert _format_throughput_parts(2_500_000.0) == ("2.5 M", "rows/s")


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
        """OPENLINK_NO_PROGRESS should suppress interactive progress."""
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

    def test_no_color_env_keeps_interactive_but_strips_colors(self):
        """NO_COLOR should strip ANSI styling but keep the progress display active."""
        with patch("sys.stderr.isatty", return_value=True):
            with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=True):
                reporter = CliRunReporter("test")
                assert reporter._interactive is True
                assert reporter._progress_indicator._BOLD == ""
                assert reporter._progress_indicator._CYAN == ""

    def test_no_color_absent_enables_styling(self):
        """Without NO_COLOR, ANSI styling should be active."""
        with patch("sys.stderr.isatty", return_value=True):
            with patch.dict("os.environ", {}, clear=True):
                reporter = CliRunReporter("test")
                assert reporter._progress_indicator._BOLD != ""

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

    def test_add_stats_provider(self):
        """add_stats_provider should register a provider on the progress indicator."""
        with patch("sys.stderr.isatty", return_value=True):
            with patch.dict("os.environ", {}, clear=True):
                reporter = CliRunReporter("test")

                class MockProvider:
                    def get_metrics(self) -> list[tuple[str, str, str]]:
                        return [("custom", "99", "items")]

                provider = MockProvider()
                reporter.add_stats_provider(provider)
                assert provider in reporter._progress_indicator._stats_providers


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


class TestProgressIndicatorLiveRedraw:
    """Tests that the progress indicator redraws immediately on update, not just on the timer."""

    def test_update_sets_update_event(self):
        """update() sets _update_event so the render loop can wake without waiting 1 s."""
        pi = _ProgressIndicator()
        assert not pi._update_event.is_set()
        pi.update(stage="Working", done=10)
        assert pi._update_event.is_set()

    def test_render_redraws_when_update_event_set(self):
        """The render loop redraws immediately when _update_event is signalled."""
        pi = _ProgressIndicator()
        pi._start_time = 0.0
        pi.update(stage="Flushing", done=50)
        pi._running.set()

        writes: list[str] = []

        def _write(text: str) -> int:
            writes.append(text)
            pi._running.clear()
            return len(text)

        sleep_durations: list[float] = []

        def _fake_wait(timeout: float) -> bool:
            sleep_durations.append(timeout)
            return True  # simulate event triggered immediately

        with (
            patch("shutil.get_terminal_size", return_value=__import__("os").terminal_size((160, 24))),
            patch("sys.stderr.write", side_effect=_write),
            patch("sys.stderr.flush"),
            patch("time.perf_counter", return_value=5.0),
        ):
            # Patch the event's wait method to return True (event was set) without sleeping
            pi._update_event.wait = _fake_wait
            pi._render()

        # The render should have produced output (event-driven, not blocked by sleep)
        assert writes, "Render must write output when update event is signalled"
        # The wait should have been called with the configured render interval
        assert sleep_durations, "wait() should have been called"
        assert abs(sleep_durations[0] - _ProgressIndicator._RENDER_INTERVAL_SECONDS) < 1e-9


class TestCliRunReporterElapsed:
    """Tests for elapsed-duration tracking and reporting."""

    def test_elapsed_seconds_stored_after_context_exit(self, tmp_path, monkeypatch):
        """CliRunReporter stores _elapsed_seconds after the with-block exits."""
        monkeypatch.setattr(
            "openlinktoken_cli.util.app_paths.get_openlinktoken_home",
            lambda: tmp_path,
        )
        reporter = CliRunReporter("test", no_progress=True)
        assert reporter._elapsed_seconds is None
        with reporter:
            pass
        assert reporter._elapsed_seconds is not None
        assert reporter._elapsed_seconds >= 0.0

    def test_finish_success_includes_elapsed_duration(self, tmp_path, monkeypatch, capsys):
        """finish_success prints elapsed duration in the completion summary."""
        monkeypatch.setattr(
            "openlinktoken_cli.util.app_paths.get_openlinktoken_home",
            lambda: tmp_path,
        )
        reporter = CliRunReporter("test", no_progress=True)
        with reporter:
            pass
        reporter.finish_success("Test complete", ["output: test.csv"])
        captured = capsys.readouterr()
        assert re.search(r"Duration: \d{2}:\d{2}", captured.err), (
            f"Expected duration (MM:SS) in summary, got:\n{captured.err}"
        )

    def test_elapsed_logged_to_file_before_handler_detaches(self, tmp_path, monkeypatch):
        """Elapsed completion message is written to the log file during __exit__."""
        monkeypatch.setattr(
            "openlinktoken_cli.util.app_paths.get_openlinktoken_home",
            lambda: tmp_path,
        )
        reporter = CliRunReporter("test", no_progress=True)
        with reporter:
            pass
        log_path = reporter.log_report.log_path
        assert log_path.exists(), "Log file must exist after run"
        log_text = log_path.read_text(encoding="utf-8")
        # The log file must contain a completion/elapsed message written before handler detach
        assert "duration" in log_text.lower(), f"Expected duration in log, got:\n{log_text}"

    def test_file_logging_restores_root_logger_level(self, tmp_path, monkeypatch):
        """Attaching per-run logging should not change the caller's root logger level."""
        monkeypatch.setattr(
            "openlinktoken_cli.util.app_paths.get_openlinktoken_home",
            lambda: tmp_path,
        )
        root_logger = logging.getLogger()
        original_level = root_logger.level
        root_logger.setLevel(logging.WARNING)
        try:
            reporter = CliRunReporter("test", no_progress=True)
            with reporter:
                pass
            assert root_logger.level == logging.WARNING
        finally:
            root_logger.setLevel(original_level)

    def test_file_logging_restores_root_logger_level_after_exception(self, tmp_path, monkeypatch):
        """Root logger restoration should also happen when a run raises an exception."""
        monkeypatch.setattr(
            "openlinktoken_cli.util.app_paths.get_openlinktoken_home",
            lambda: tmp_path,
        )
        root_logger = logging.getLogger()
        original_level = root_logger.level
        root_logger.setLevel(logging.WARNING)
        try:
            with pytest.raises(RuntimeError, match="processing failed"):
                with CliRunReporter("test", no_progress=True):
                    raise RuntimeError("processing failed")
            assert root_logger.level == logging.WARNING
        finally:
            root_logger.setLevel(original_level)
