# SPDX-License-Identifier: MIT

import logging
import os
import re
import shutil
import sys
import threading
import time
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol, Sequence, runtime_checkable

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


@dataclass(frozen=True)
class CountSummary:
    """Summary item for a named count."""

    name: str
    count: int


def _format_elapsed(seconds: float) -> str:
    """Format seconds as HH:MM:SS or NN:MM:SS."""
    seconds = int(seconds)
    hours = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0 or seconds >= 3600:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def _format_throughput(rate: float) -> str:
    """Format throughput as human-readable rows per second with K/M for large values."""
    rows = rate
    if rows >= 1_000_000:
        return f"{rows / 1_000_000:.1f} M rows/s"
    elif rows >= 1_000:
        return f"{rows / 1_000:.1f} K rows/s"
    elif rows >= 100:
        return f"{rows:.0f} rows/s"
    else:
        return f"{rows:.1f} rows/s"


def _format_throughput_parts(rate: float) -> tuple[str, str]:
    """Format throughput as (number, unit) parts for aligned rendering."""
    rows = rate
    if rows >= 1_000_000:
        return f"{rows / 1_000_000:.1f} M", "rows/s"
    elif rows >= 1_000:
        return f"{rows / 1_000:.1f} K", "rows/s"
    elif rows >= 100:
        return f"{rows:.0f}", "rows/s"
    else:
        return f"{rows:.1f}", "rows/s"


@runtime_checkable
class StatsProvider(Protocol):
    """
    Protocol for extension packages to provide custom metrics to the progress display.

    Extensions implement this interface and register with the reporter via
    ``CliRunReporter.add_stats_provider(provider)``. The reporter queries
    ``get_metrics()`` on each render tick and appends the results to the
    single-line status display.
    """

    def get_metrics(self) -> list[tuple[str, str, str]]:
        """
        Return custom metrics as (label, number, unit) triples for the status line.

        Returns:
            List of (label, number_string, unit_string) tuples.
            Use empty string for unit when not applicable.
        """
        ...


class _ProgressIndicator:
    """Internal progress indicator with spinner, percentage, ETA, and throughput."""

    _FRAMES = ("\u280b", "\u2819", "\u2839", "\u2838", "\u283c", "\u2834", "\u2826", "\u2827", "\u2807", "\u280f")
    _RENDER_INTERVAL_SECONDS = 1.0
    _ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

    def __init__(self, use_color: bool = True):
        self._total_rows = 0
        self._done = 0
        self._stage = ""
        self._start_time = time.perf_counter()
        self._lock = threading.Lock()
        self._frame_index = 0
        self._frame_lock = threading.Lock()
        self._running = threading.Event()
        self._update_event = threading.Event()
        self._last_render_line_count = 0
        self._stats_providers: list[StatsProvider] = []
        if use_color:
            self._BOLD = "\x1b[1m"
            self._CYAN = "\x1b[36m"
            self._RESET = "\x1b[0m"
        else:
            self._BOLD = ""
            self._CYAN = ""
            self._RESET = ""

    def start(self) -> None:
        """Start the background render thread."""
        self._start_time = time.perf_counter()
        self._last_render_line_count = 0
        self._running.set()
        self._thread = threading.Thread(target=self._render, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the spinner gracefully."""
        self._running.clear()
        self._update_event.set()  # Wake the render thread so it exits without waiting
        if hasattr(self, "_thread") and self._thread.is_alive():
            self._thread.join(timeout=self._RENDER_INTERVAL_SECONDS + 0.5)
        self._clear_block()

    def set_total_rows(self, total: int) -> None:
        """Set total rows and clear done count."""
        with self._lock:
            self._total_rows = total
            self._done = 0

    def update(self, stage: str, done: int) -> None:
        """Update the stage label and the number of completed rows."""
        with self._lock:
            self._stage = stage
            self._done = done
        self._update_event.set()

    def _format_elapsed(self, seconds: float) -> str:
        """Delegate to module-level _format_elapsed."""
        return _format_elapsed(seconds)

    def _format_percentage(self, done: int, total: int) -> str:
        """Format done/total as a percentage string."""
        if total > 0:
            return f"{done / total * 100:.1f}"
        return "N/A"

    def _visible_len(self, text: str) -> int:
        """Compute terminal-visible length (excluding ANSI escape sequences)."""
        return len(self._ANSI_RE.sub("", text))

    @staticmethod
    def _placeholder(value: str | None) -> str:
        """Render unknown progress values consistently."""
        return value if value else "--"

    def _truncate_line(self, line: str, max_width: int) -> str:
        """Truncate a rendered line to fit the terminal width (ANSI-aware)."""
        if max_width <= 0:
            return ""
        if self._visible_len(line) <= max_width:
            return line
        plain = self._ANSI_RE.sub("", line)
        if max_width <= 3:
            return "." * max_width
        return plain[: max_width - 3] + "..."

    def _build_render_line(
        self,
        frame: str,
        stage: str,
        done: int,
        total: int,
        pct_str: str | None,
        remaining_str: str | None,
        speed_parts: tuple[str, str] | None,
        elapsed_str: str,
    ) -> str:
        """Build a compact status line containing core and extension metrics."""
        total_text = f"{total:,}" if total > 0 else "--"
        percentage_text = f"{pct_str}%" if pct_str else "--"
        throughput_text = f"{speed_parts[0]} {speed_parts[1]}" if speed_parts else "--"
        remaining_text = remaining_str if remaining_str else "--"

        segments = [
            f"{self._CYAN}{frame}{self._RESET} {self._BOLD}{stage}{self._RESET}",
            (
                f"{self._BOLD}{done:,}{self._RESET}/{self._BOLD}{total_text}{self._RESET} "
                f"rows ({self._BOLD}{percentage_text}{self._RESET})"
            ),
            f"remaining {remaining_text}",
            throughput_text,
            f"elapsed {elapsed_str}",
        ]

        for provider in self._stats_providers:
            for label, number, unit in provider.get_metrics():
                segments.append(f"{label}: {number}" + (f" {unit}" if unit else ""))

        return " | ".join(segments)

    def _write_render_block(self, lines: list[str]) -> None:
        """Draw the progress status in place without moving through prior lines."""
        terminal_width = max(20, shutil.get_terminal_size((80, 24)).columns)
        rendered_line = " | ".join(line.strip() for line in lines)
        rendered_line = self._truncate_line(rendered_line, terminal_width)
        sys.stderr.write("\r\x1b[2K" + rendered_line)
        sys.stderr.flush()
        self._last_render_line_count = 1

    def _render(self) -> None:
        """Render the spinner and progress info on stderr at ~1 Hz or on update events."""
        try:
            while self._running.is_set():
                with self._frame_lock:
                    frame = self._FRAMES[self._frame_index % len(self._FRAMES)]
                    self._frame_index += 1

                self._update_event.wait(timeout=self._RENDER_INTERVAL_SECONDS)
                self._update_event.clear()

                if not self._running.is_set():
                    break

                with self._lock:
                    stage = self._stage
                    done = self._done
                    total = self._total_rows
                    start_time = self._start_time

                now = time.perf_counter()
                elapsed = now - start_time

                pct_str: str | None = None
                remaining_str: str | None = None
                speed_parts: tuple[str, str] | None = None

                rate = 0.0
                if elapsed > 0 and done > 0:
                    rate = done / elapsed
                    if rate > 0:
                        speed_parts = _format_throughput_parts(rate)

                if total > 0:
                    pct_str = self._format_percentage(done, total)
                    if rate > 0 and elapsed < 24 * 3600:
                        remaining = total - done
                        if remaining > 0:
                            eta_seconds = remaining / rate
                            remaining_str = self._format_elapsed(eta_seconds)

                elapsed_str = self._format_elapsed(elapsed)
                line = self._build_render_line(
                    frame,
                    stage,
                    done,
                    total,
                    pct_str,
                    remaining_str,
                    speed_parts,
                    elapsed_str,
                )
                self._write_render_block([line])

        except KeyboardInterrupt:
            pass

    def _clear_block(self) -> None:
        """Clear the current progress block from stderr."""
        if self._last_render_line_count <= 0:
            return

        sys.stderr.write("\r\x1b[2K\n")
        sys.stderr.flush()
        self._last_render_line_count = 0


class CliRunReporter:
    """Manage per-run logging, TTY progress, and end-of-run summaries."""

    def __init__(self, command_name: str, no_progress: bool = False):
        self.command_name = command_name
        self.log_report = create_cli_log_report(command_name)
        self._console_handler: logging.Handler | None = None
        self._console_handler_level: int | None = None
        self._file_handler: logging.Handler | None = None
        self._root_logger_level: int | None = None
        self._interactive = bool(getattr(sys.stderr, "isatty", None) and sys.stderr.isatty())
        self._interactive = self._interactive and not os.getenv("NO_PROGRESS")
        self._interactive = self._interactive and not os.getenv("OPENLINK_NO_PROGRESS")
        self._interactive = self._interactive and not no_progress
        use_color = not os.getenv("NO_COLOR")
        self._progress_indicator = _ProgressIndicator(use_color=use_color)
        self._total_rows = 0
        self._run_start_time: float | None = None
        self._elapsed_seconds: float | None = None

    def __enter__(self) -> "CliRunReporter":
        self._attach_file_logging()
        self._mute_console_logging()
        if self._interactive:
            self._progress_indicator.start()
        self._run_start_time = time.perf_counter()
        logging.getLogger(__name__).info("Starting %s command", self.command_name)
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._interactive:
            self._progress_indicator.stop()
        self._restore_console_logging()
        if self._run_start_time is not None:
            self._elapsed_seconds = time.perf_counter() - self._run_start_time
            status = "failed" if exc_type is not None else "completed"
            logging.getLogger(__name__).info(
                "Run %s. Duration: %s",
                status,
                _format_elapsed(self._elapsed_seconds),
            )
        self._detach_file_logging()

    def update_status(self, stage: str, processed_count: int | None = None, unit_label: str | None = None) -> None:
        self._progress_indicator.update(stage, processed_count or 0)

    def set_total_rows(self, total: int) -> None:
        self._progress_indicator.set_total_rows(total)
        self._total_rows = total

    def make_progress_callback(self, stage: str, unit_label: str) -> Callable[[int], None]:
        def _callback(processed_count: int) -> None:
            self.update_status(stage, processed_count=processed_count, unit_label=unit_label)

        return _callback

    def add_stats_provider(self, provider: StatsProvider) -> None:
        """
        Register an extension stats provider for the progress display.

        The provider's ``get_metrics()`` method will be called on each render tick
        and its metrics displayed below a divider in the progress block.

        Args:
            provider: An object implementing the StatsProvider protocol.
        """
        self._progress_indicator._stats_providers.append(provider)

    def finish_success(self, title: str, lines: Sequence[str]) -> None:
        detail_log_line = format_dimmed_stderr_message(f"  Detailed log: {self.log_report.log_path}")
        elapsed_line = (
            f"  Duration: {_format_elapsed(self._elapsed_seconds)}" if self._elapsed_seconds is not None else None
        )
        summary_parts: list[str] = [title, *[f"    {line}" for line in lines]]
        if elapsed_line:
            summary_parts.append(elapsed_line)
        summary_parts.append(detail_log_line)
        if self._interactive:
            print(file=sys.stderr)
        print("\n".join(summary_parts), file=sys.stderr)

    @staticmethod
    def summarize_count_lines(label: str, counts: Mapping[str, int], limit: int | None = None) -> list[str]:
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
        root_logger = logging.getLogger()
        self._root_logger_level = root_logger.level
        root_logger.addHandler(file_handler)
        if root_logger.level == logging.NOTSET or root_logger.level > logging.INFO:
            root_logger.setLevel(logging.INFO)
        self._file_handler = file_handler

    def _detach_file_logging(self) -> None:
        if self._file_handler is None:
            return
        root_logger = logging.getLogger()
        try:
            root_logger.removeHandler(self._file_handler)
            self._file_handler.close()
        finally:
            self._file_handler = None
            if self._root_logger_level is not None:
                root_logger.setLevel(self._root_logger_level)
                self._root_logger_level = None

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
