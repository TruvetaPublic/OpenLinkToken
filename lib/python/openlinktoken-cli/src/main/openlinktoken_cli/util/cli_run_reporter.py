# SPDX-License-Identifier: MIT

import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from openlinktoken_cli.util.cli_error_reporter import (
    RedactingFormatter,
    create_cli_log_report,
    format_dimmed_stderr_message,
)

_DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_DEFAULT_CONSOLE_FORMAT = "%(message)s"
_CONSOLE_HANDLER_MARKER = "_openlinktoken_console_handler"


def configure_default_logging() -> None:
    """Attach the default console logger once for the CLI process."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if getattr(handler, _CONSOLE_HANDLER_MARKER, False):
            return

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(RedactingFormatter(_DEFAULT_CONSOLE_FORMAT))
    setattr(console_handler, _CONSOLE_HANDLER_MARKER, True)
    root_logger.addHandler(console_handler)
    if root_logger.level == logging.NOTSET or root_logger.level > logging.INFO:
        root_logger.setLevel(logging.INFO)


def _get_default_console_handler() -> logging.Handler | None:
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if getattr(handler, _CONSOLE_HANDLER_MARKER, False):
            return handler
    return None


def _format_eta(seconds: float) -> str:
    """Format elapsed or estimated seconds as MM:SS or HH:MM:SS."""
    if seconds < 0 or not seconds:
        return "??:??"
    seconds = int(seconds)
    mins = seconds // 60
    secs = seconds % 60
    if mins >= 60:
        hours = mins // 60
        return f"{hours:02d}:{mins % 60:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def _format_elapsed(seconds: float) -> str:
    """Format total elapsed seconds as MM:SS or HH:MM:SS."""
    seconds = int(seconds)
    mins = seconds // 60
    secs = seconds % 60
    if mins >= 60:
        hours = mins // 60
        return f"{hours:02d}:{mins % 60:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


@dataclass(frozen=True)
class CountSummary:
    """Summary item for a named count."""
    name: str
    count: int


class _ProgressIndicator:
    """Enhanced TTY progress indicator with percentage, ETA, and throughput display.

    When total_rows > 0 and done > 0:
        Show: {spinner} {stage} 42.0% [████░░░░░░░░░░░░░░░░] 420,000/1,000,000 ETA 01:23 (7,500 rows/s)

    When total_rows == 0 or done == 0:
        Show: {spinner} {stage} 420,000 records, elapsed 00:56 (7,500 rows/s)

    When no progress yet:
        Show: {spinner} {stage} starting...

    Render loop runs at ~8 FPS on stderr. Output is suppressed when enabled=False.
    """

    _FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

    def __init__(self, enabled: bool):
        self._enabled = enabled
        self._stage = ""
        self._total_rows = 0
        self._done = 0
        self._start_time = 0.0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, stage: str, total_rows: int = 0) -> None:
        """Start the progress indicator with a stage label and optional total row count."""
        if not self._enabled:
            return
        with self._lock:
            self._stage = stage
            self._total_rows = total_rows
            self._done = 0
            self._start_time = time.time()
        self._thread = threading.Thread(target=self._render, daemon=True)
        self._thread.start()

    def update(self, stage: str | None = None, done: int | None = None) -> None:
        """Update stage text and/or done count. Total rows is set at start()."""
        if not self._enabled:
            return
        with self._lock:
            if stage is not None:
                self._stage = stage
            if done is not None:
                self._done = done

    def set_total_rows(self, total_rows: int) -> None:
        """Update the total row count for percentage/ETA calculation."""
        if not self._enabled:
            return
        with self._lock:
            self._total_rows = total_rows

    def stop(self) -> None:
        """Stop the render thread and clear the progress line."""
        if not self._enabled:
            return
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._clear_line()

    def _render(self) -> None:
        """Background render loop. Runs at ~8 FPS."""
        while not self._stop_event.is_set():
            with self._lock:
                stage = self._stage
                total = self._total_rows
                done = self._done
                start_time = self._start_time

            elapsed = time.time() - start_time
            frame_idx = int(time.time() / 0.125)
            frame = self._FRAMES[frame_idx % len(self._FRAMES)]

            if total > 0 and done > 0 and elapsed > 0:
                pct = done / max(total, 0.001) * 100
                rate = done / elapsed
                remaining = total - done
                eta_secs = remaining / rate if rate > 0 else -1.0
                eta = _format_eta(eta_secs) if eta_secs >= 0 else "??:??"
                throughput_str = f"{rate:,.0f}"
                bar_width = 20
                filled = min(bar_width, int(pct / 100 * bar_width))
                bar = "█" * filled + "░" * (bar_width - filled)
                line = (
                    f"\r{frame} {stage} "
                    f"{pct:5.1f}% [{bar}] "
                    f"{done:,}/{total:,} "
                    f"ETA {eta} "
                    f"({throughput_str} rows/s)"
                )
            elif done > 0:
                throughput = f"{done / max(0.001, elapsed):,.0f}" if elapsed > 0 else "..."
                elapsed_str = _format_elapsed(elapsed)
                line = f"\r{frame} {stage} {done:,} records, elapsed {elapsed_str} ({throughput} rows/s)"
            else:
                line = f"\r{frame} {stage} starting..."

            sys.stderr.write(line)
            sys.stderr.flush()
            time.sleep(0.125)

    @staticmethod
    def _clear_line() -> None:
        """Clear the current cursor line."""
        sys.stderr.write("\r\033[K")
        sys.stderr.flush()


class CliRunReporter:
    """Manage per-run logging, TTY progress, and end-of-run summaries.

    Usage:
        reporter = CliRunReporter("encrypt", no_progress=False)
        with reporter:
            reporter.update_status("Processing...")
            callback = reporter.make_progress_callback("Encrypting tokens", "tokens")
            for row in reader:
                callback(row_count)
            reporter.set_total_rows(total_count)    # if count known in advance
        # Summary printed on exit
    """

    def __init__(self, command_name: str, no_progress: bool = False):
        self.command_name = command_name
        self.log_report = create_cli_log_report(command_name)
        self._no_progress = no_progress
        self._console_handler: logging.Handler | None = None
        self._console_handler_level: int | None = None
        self._file_handler: logging.Handler | None = None
        self._stage = ""
        self._total_rows = 0
        self._interactive = bool(
            sys.stderr.isatty()
            and not os.getenv("NO_COLOR")
            and not no_progress
            and not os.getenv("NO_PROGRESS")
            and not os.getenv("OPENLINK_NO_PROGRESS")
        )
        self._progress_indicator = _ProgressIndicator(self._interactive)

    def __enter__(self) -> "CliRunReporter":
        self._attach_file_logging()
        self._mute_console_logging()
        self._progress_indicator.start(
            f"Starting {self.command_name}... ",
            total_rows=0,
        )
        logging.getLogger(__name__).info("Starting %s command", self.command_name)
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self._progress_indicator.stop()
        self._restore_console_logging()
        self._detach_file_logging()

    def update_status(self, stage: str, processed_count: int | None = None, unit_label: str | None = None) -> None:
        """Update the live progress status shown in interactive terminals.

        When processed_count and unit_label are provided, formats the message as:
           "{stage} ({count:,} {unit_label})"
        """
        message = stage
        count_to_show = processed_count
        if processed_count is not None and unit_label:
            message = f"{stage} ({processed_count:,} {unit_label})"
            count_to_show = processed_count
        self._progress_indicator.update(stage=message, done=count_to_show)

    def make_progress_callback(self, stage: str, unit_label: str) -> Callable[[int], None]:
        """Return a callback that updates the shared progress indicator.

        The callback accepts a processed_count (int) and updates both stage and done.
        """
        def _callback(processed_count: int) -> None:
            self.update_status(stage, processed_count=processed_count, unit_label=unit_label)
        return _callback

    def set_total_rows(self, total_rows: int) -> None:
        """Set the total row count for progress percentage/ETA calculation."""
        self._total_rows = total_rows
        self._progress_indicator.set_total_rows(total_rows)

    def finish_success(self, title: str, lines: Sequence[str]) -> None:
        """Render a concise success summary for the completed run."""
        # Clear any lingering progress line before printing summary
        self._progress_indicator._clear_line()
        detail_log_line = format_dimmed_stderr_message(f"  Detailed log: {self.log_report.log_path}")
        summary_lines = [title, *[f"   {line}" for line in lines], detail_log_line]
        print("\n".join(summary_lines), file=sys.stderr)

    @staticmethod
    def summarize_count_lines(label: str, counts: Mapping[str, int], limit: int | None = None) -> list[str]:
        """Format named counts for CLI summary output."""
        non_zero_items = [CountSummary(name=name, count=count) for name, count in counts.items() if count > 0]
        if not non_zero_items:
            return [f"{label}: none"]

        if limit is not None:
            non_zero_items = sorted(non_zero_items, key=lambda item: (-item.count, item.name))[:limit]

        summary_items = sorted(non_zero_items, key=lambda item: item.name)
        if len(summary_items) == 1:
            item = summary_items[0]
            return [f"{label}: {item.name}={item.count:,}"]

        return [f"{label}:", *[f"   {item.name}: {item.count:,}" for item in summary_items]]

    def _attach_file_logging(self) -> None:
        self.log_report.log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(self.log_report.log_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(RedactingFormatter(_DEFAULT_LOG_FORMAT))
        logging.getLogger().addHandler(file_handler)
        self._file_handler = file_handler

    def _detach_file_logging(self) -> None:
        if self._file_handler is None:
            return
        logging.getLogger().removeHandler(self._file_handler)
        self._file_handler.close()
        self._file_handler = None

    def _mute_console_logging(self) -> None:
        self._console_handler = _get_default_console_handler()
        if self._console_handler is None:
            return
        self._console_handler_level = self._console_handler.level
        self._console_handler.setLevel(logging.CRITICAL + 1)

    def _restore_console_logging(self) -> None:
        if self._console_handler is None or self._console_handler_level is None:
            return
        self._console_handler.setLevel(self._console_handler_level)
        self._console_handler_level = None
