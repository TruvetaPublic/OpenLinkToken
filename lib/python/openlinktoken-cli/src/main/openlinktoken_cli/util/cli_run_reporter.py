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


@dataclass(frozen=True)
class CountSummary:
    """Summary item for a named count."""

    name: str
    count: int


class _ProgressIndicator:
    """Internal progress indicator with spinner, percentage, ETA, and throughput."""

    _FRAMES = ("\u280b", "\u2819", "\u2839", "\u2838", "\u283c", "\u2834", "\u2826", "\u2827", "\u2807", "\u280f")

    def __init__(self):
        self._total_rows = 0
        self._done = 0
        self._stage = ""
        self._start_time = time.perf_counter()
        self._lock = threading.Lock()
        self._frame_index = 0
        self._frame_lock = threading.Lock()
        self._running = threading.Event()

    def start(self, progress_frames: int = 4) -> None:
        """Start the background render thread."""
        self._start_time = time.perf_counter()
        self._running.set()
        self._thread = threading.Thread(target=self._render, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the spinner gracefully."""
        self._running.clear()
        if hasattr(self, "_thread") and self._thread.is_alive():
            self._thread.join(timeout=1)

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
        """Format seconds as HH:MM:SS or NN:MM:SS."""
        seconds = int(seconds)
        if seconds >= 24 * 3600:
            hours = seconds // 3600
        else:
            hours = 0
        mins = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0 or seconds >= 3600:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def _format_percentage(self, done: int, total: int) -> str:
        """Format done/total as a percentage string."""
        if total > 0:
            return f"{done / total * 100:.1f}%"
        return "N/A"

    def _render(self) -> None:
        """Render the spinner and progress info on stderr at ~8 FPS."""
        try:
            while self._running.is_set():
                with self._frame_lock:
                    frame = self._FRAMES[self._frame_index % len(self._FRAMES)]
                    self._frame_index += 1

                time.sleep(0.125)  # ~8 FPS

                if not self._running.is_set():
                    break

                with self._lock:
                    stage = self._stage
                    done = self._done
                    total = self._total_rows
                    start_time = self._start_time

                now = time.perf_counter()
                elapsed = now - start_time

                pct_str = self._format_percentage(done, total)

                parts = [frame, stage, pct_str]

                if total > 0 and elapsed > 0 and done > 0:
                    rate = done / elapsed
                    if rate > 0 and elapsed < 24 * 3600:
                        remaining = total - done
                        if remaining > 0:
                            eta_seconds = remaining / rate
                            eta_str = self._format_elapsed(eta_seconds)
                        else:
                            eta_str = self._format_elapsed(0)
                        throughput = f"{rate:.0f} rows/s"
                        parts.append(eta_str)
                        parts.append(throughput)
                    else:
                        elapsed_str = self._format_elapsed(elapsed)
                        parts.append(elapsed_str)
                else:
                    elapsed_str = self._format_elapsed(elapsed)
                    parts.append(elapsed_str)

                line = " ".join(parts)
                sys.stderr.write("\r" + line + "\r")
                sys.stderr.flush()

        except KeyboardInterrupt:
            pass

    def finish(self) -> None:
        """No-op cleanup method."""
        pass


class CliRunReporter:
    """Manage per-run logging, TTY progress, and end-of-run summaries."""

    def __init__(self, command_name: str):
        self.command_name = command_name
        self.log_report = create_cli_log_report(command_name)
        self._console_handler: logging.Handler | None = None
        self._console_handler_level: int | None = None
        self._file_handler: logging.Handler | None = None
        self._interactive = bool(getattr(sys.stderr, "isatty", None) and sys.stderr.isatty())
        self._interactive = self._interactive and not os.getenv("NO_COLOR")
        self._progress_indicator = _ProgressIndicator()

    def __enter__(self) -> "CliRunReporter":
        self._attach_file_logging()
        self._mute_console_logging()
        self._progress_indicator.start()
        logging.getLogger(__name__).info("Starting %s command", self.command_name)
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self._progress_indicator.stop()
        self._restore_console_logging()
        self._detach_file_logging()

    def update_status(self, stage: str, processed_count: int | None = None, unit_label: str | None = None) -> None:
        message = stage
        if processed_count is not None and unit_label:
            message = f"{stage} ({processed_count:,} {unit_label})"
        self._progress_indicator.update(stage, processed_count or 0)

    def make_progress_callback(self, stage: str, unit_label: str) -> Callable[[int], None]:
        def _callback(processed_count: int) -> None:
            self.update_status(stage, processed_count=processed_count, unit_label=unit_label)

        return _callback

    def finish_success(self, title: str, lines: Sequence[str]) -> None:
        detail_log_line = format_dimmed_stderr_message(f"  Detailed log: {self.log_report.log_path}")
        summary_lines = [title, *[f"    {line}" for line in lines], detail_log_line]
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

        return [f"{label}:", *[f"    {item.name}: {item.count:,}" for item in summary_items]]

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
