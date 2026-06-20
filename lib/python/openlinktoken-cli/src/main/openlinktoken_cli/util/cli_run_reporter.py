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
    ``get_metrics()`` on each render tick and displays the results below
    a divider line.
    """

    def get_metrics(self) -> list[tuple[str, str, str]]:
        """
        Return custom metrics as (label, number, unit) triples.

        Each triple is rendered as a right-aligned number with a left-aligned
        unit, matching the built-in metric style.

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

    _DIM = "\x1b[2m"
    _BOLD = "\x1b[1m"
    _CYAN = "\x1b[36m"
    _RESET = "\x1b[0m"

    _BOLD_METRIC_LABELS = frozenset({"processed", "total", "complete"})

    def __init__(self):
        self._total_rows = 0
        self._done = 0
        self._stage = ""
        self._start_time = time.perf_counter()
        self._lock = threading.Lock()
        self._frame_index = 0
        self._frame_lock = threading.Lock()
        self._running = threading.Event()
        self._last_render_line_count = 0
        self._stats_providers: list[StatsProvider] = []

    def start(self, progress_frames: int = 4) -> None:
        """Start the background render thread."""
        self._start_time = time.perf_counter()
        self._last_render_line_count = 0
        self._running.set()
        self._thread = threading.Thread(target=self._render, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the spinner gracefully."""
        self._running.clear()
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

    def _build_render_lines(
        self,
        frame: str,
        stage: str,
        done: int,
        total: int,
        pct_str: str | None,
        remaining_str: str | None,
        speed_parts: tuple[str, str] | None,
        elapsed_str: str,
    ) -> list[str]:
        """Build the styled multiline progress block with aligned columns."""
        # Core metrics as (label, number, unit) triples
        core_metrics: list[tuple[str, str, str]] = [
            ("processed", f"{done:,}", "rows"),
            ("total", f"{total:,}" if total > 0 else "--", "rows" if total > 0 else ""),
            ("complete", pct_str if pct_str else "--", "%" if pct_str else ""),
            ("throughput", speed_parts[0] if speed_parts else "--", speed_parts[1] if speed_parts else ""),
            ("elapsed", elapsed_str, ""),
            ("remaining", remaining_str if remaining_str else "--", ""),
        ]

        # Collect extension metrics
        extension_metrics: list[tuple[str, str, str]] = []
        for provider in self._stats_providers:
            extension_metrics.extend(provider.get_metrics())

        all_metrics = core_metrics + extension_metrics

        # Compute column widths from all metrics (core + extensions)
        label_width = max(len(label) for label, _, _ in all_metrics)
        number_width = max(len(number) for _, number, _ in all_metrics)

        # Build styled lines
        lines: list[str] = [f" {self._CYAN}{frame}{self._RESET} {self._BOLD}{stage}{self._RESET}"]

        for label, number, unit in core_metrics:
            lines.append(self._format_metric_line(label, number, unit, label_width, number_width))

        if extension_metrics:
            divider_width = label_width + number_width + 4
            lines.append(f"  {self._DIM}{'─' * divider_width}{self._RESET}")
            for label, number, unit in extension_metrics:
                lines.append(self._format_metric_line(label, number, unit, label_width, number_width))

        return lines

    def _format_metric_line(self, label: str, number: str, unit: str, label_width: int, number_width: int) -> str:
        """Format a single metric line with dim label and optionally bold value."""
        padding = " " * (label_width - len(label) + 1)
        is_bold = label in self._BOLD_METRIC_LABELS

        styled_label = f"{self._DIM}{label}:{self._RESET}"
        if is_bold:
            styled_number = f"{self._BOLD}{number.rjust(number_width)}{self._RESET}"
        else:
            styled_number = number.rjust(number_width)

        if unit:
            return f"  {styled_label}{padding}{styled_number} {unit}"
        return f"  {styled_label}{padding}{styled_number}"

    def _write_render_block(self, lines: list[str]) -> None:
        """Draw the multiline progress block in place."""
        terminal_width = max(20, shutil.get_terminal_size((80, 24)).columns)
        truncated_lines = [self._truncate_line(line, terminal_width) for line in lines]

        if self._last_render_line_count > 1:
            sys.stderr.write(f"\x1b[{self._last_render_line_count - 1}F")
        elif self._last_render_line_count == 1:
            sys.stderr.write("\r")

        for index, line in enumerate(truncated_lines):
            sys.stderr.write("\x1b[2K" + line)
            if index < len(truncated_lines) - 1:
                sys.stderr.write("\n")

        sys.stderr.flush()
        self._last_render_line_count = len(truncated_lines)

    def _render(self) -> None:
        """Render the spinner and progress info on stderr at ~1 Hz."""
        try:
            while self._running.is_set():
                with self._frame_lock:
                    frame = self._FRAMES[self._frame_index % len(self._FRAMES)]
                    self._frame_index += 1

                time.sleep(self._RENDER_INTERVAL_SECONDS)

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
                lines = self._build_render_lines(
                    frame,
                    stage,
                    done,
                    total,
                    pct_str,
                    remaining_str,
                    speed_parts,
                    elapsed_str,
                )
                self._write_render_block(lines)

        except KeyboardInterrupt:
            pass

    def _clear_block(self) -> None:
        """Clear the current progress block from stderr."""
        if self._last_render_line_count <= 0:
            return

        if self._last_render_line_count > 1:
            sys.stderr.write(f"\x1b[{self._last_render_line_count - 1}F")
        else:
            sys.stderr.write("\r")

        for index in range(self._last_render_line_count):
            sys.stderr.write("\x1b[2K")
            if index < self._last_render_line_count - 1:
                sys.stderr.write("\n")

        if self._last_render_line_count > 1:
            sys.stderr.write(f"\x1b[{self._last_render_line_count - 1}F")
        else:
            sys.stderr.write("\r")

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
        self._interactive = bool(getattr(sys.stderr, "isatty", None) and sys.stderr.isatty())
        self._interactive = self._interactive and not os.getenv("NO_PROGRESS")
        self._interactive = self._interactive and not os.getenv("OPENLINK_NO_PROGRESS")
        self._interactive = self._interactive and not os.getenv("NO_COLOR")
        self._interactive = self._interactive and not no_progress
        self._progress_indicator = _ProgressIndicator()
        self._total_rows = 0

    def __enter__(self) -> "CliRunReporter":
        self._attach_file_logging()
        self._mute_console_logging()
        if self._interactive:
            self._progress_indicator.start()
        logging.getLogger(__name__).info("Starting %s command", self.command_name)
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._interactive:
            self._progress_indicator.stop()
        self._restore_console_logging()
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
        summary_lines = [title, *[f"    {line}" for line in lines], detail_log_line]
        if self._interactive:
            print(file=sys.stderr)
        print("\n".join(summary_lines), file=sys.stderr)

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
