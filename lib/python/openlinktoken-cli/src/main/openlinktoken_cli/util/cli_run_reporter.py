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
_CONSOLE_HANDLER_MARKER = "_openlinktoken_console_handler"


def configure_default_logging() -> None:
    """Attach the default console logger once for the CLI process."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if getattr(handler, _CONSOLE_HANDLER_MARKER, False):
            return

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(RedactingFormatter(_DEFAULT_LOG_FORMAT))
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
    """Minimal TTY spinner with a mutable status line."""

    _FRAMES = ("-", "\\", "|", "/")

    def __init__(self, enabled: bool):
        self._enabled = enabled
        self._message = ""
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, initial_message: str) -> None:
        if not self._enabled:
            return
        self.update(initial_message)
        self._thread = threading.Thread(target=self._render, daemon=True)
        self._thread.start()

    def update(self, message: str) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._message = message

    def stop(self) -> None:
        if not self._enabled:
            return
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._clear_line()

    def _render(self) -> None:
        frame_index = 0
        while not self._stop_event.is_set():
            with self._lock:
                message = self._message
            frame = self._FRAMES[frame_index % len(self._FRAMES)]
            print(f"\r{frame} {message}", end="", file=sys.stderr, flush=True)
            frame_index += 1
            time.sleep(0.1)

    @staticmethod
    def _clear_line() -> None:
        print("\r\033[K", end="", file=sys.stderr, flush=True)


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
        self._progress_indicator = _ProgressIndicator(self._interactive)

    def __enter__(self) -> "CliRunReporter":
        self._attach_file_logging()
        self._mute_console_logging()
        self._progress_indicator.start(f"Starting {self.command_name}...")
        logging.getLogger(__name__).info("Starting %s command", self.command_name)
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self._progress_indicator.stop()
        self._restore_console_logging()
        self._detach_file_logging()

    def update_status(self, stage: str, processed_count: int | None = None, unit_label: str | None = None) -> None:
        """Update the live progress status shown in interactive terminals."""
        message = stage
        if processed_count is not None and unit_label:
            message = f"{stage} ({processed_count:,} {unit_label})"
        self._progress_indicator.update(message)

    def make_progress_callback(self, stage: str, unit_label: str) -> Callable[[int], None]:
        """Return a callback that updates the shared progress indicator."""

        def _callback(processed_count: int) -> None:
            self.update_status(stage, processed_count=processed_count, unit_label=unit_label)

        return _callback

    def finish_success(self, title: str, lines: Sequence[str]) -> None:
        """Render a concise success summary for the completed run."""
        detail_log_line = format_dimmed_stderr_message(f"  Detailed log: {self.log_report.log_path}")
        summary_lines = [title, *[f"  {line}" for line in lines], detail_log_line]
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

        return [f"{label}:", *[f"  {item.name}: {item.count:,}" for item in summary_items]]

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
