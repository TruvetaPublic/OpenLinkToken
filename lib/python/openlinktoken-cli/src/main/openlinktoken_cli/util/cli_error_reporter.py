# SPDX-License-Identifier: MIT

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import traceback
import uuid

from openlinktoken_cli.util.app_paths import get_logs_dir


@dataclass(frozen=True)
class CliErrorReport:
    """Archived traceback details for an unexpected CLI failure."""

    reference_id: str
    log_path: Path


def archive_unexpected_error(error: BaseException, command_name: str | None = None) -> CliErrorReport:
    """Persist an unexpected exception traceback under the Open Link Token logs directory."""
    logs_dir = get_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)

    reference_id = uuid.uuid4().hex[:8]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = logs_dir / f"{timestamp}-{reference_id}.log"

    command_line = command_name or "<unknown>"
    traceback_text = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    log_path.write_text(
        "\n".join(
            [
                f"Reference: {reference_id}",
                f"Timestamp: {timestamp}",
                f"Command: {command_line}",
                "",
                traceback_text,
            ]
        ),
        encoding="utf-8",
    )

    return CliErrorReport(reference_id=reference_id, log_path=log_path)


def format_unexpected_error_message(report: CliErrorReport, command_name: str | None = None) -> str:
    """Build the stderr message shown to users for archived unexpected failures."""
    command_context = f" while running '{command_name}'" if command_name else ""
    return (
        f"Error: Unexpected internal error{command_context}.\n"
        f"Reference: {report.reference_id}\n"
        f"Details: {report.log_path}"
    )
