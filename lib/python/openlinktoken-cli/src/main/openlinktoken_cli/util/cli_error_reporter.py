# SPDX-License-Identifier: MIT

import os
import re
import sys
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from openlinktoken_cli.util.app_paths import get_logs_dir


@dataclass(frozen=True)
class CliErrorReport:
    """Archived traceback details for a CLI failure."""

    reference_id: str
    log_path: Path


_SENSITIVE_FLAG_PATTERNS = [
    re.compile(r"(?i)(--hashingsecret)(\s+)(\S+)"),
    re.compile(r"(?i)(--hashingsecret=)(\S+)"),
]
_SENSITIVE_KV_PATTERN = re.compile(
    r"(?i)\b(hashingsecret|password|passwd|secret|token|api[_-]?key|private[_-]?key)\b(\s*[:=]\s*)([^\s,;]+)"
)


def _redact_sensitive_text(value: str) -> str:
    redacted = value
    for pattern in _SENSITIVE_FLAG_PATTERNS:
        redacted = pattern.sub(
            lambda match: (
                f"{match.group(1)}{match.group(2) if match.lastindex and match.lastindex >= 2 else ''}[REDACTED]"
            ),
            redacted,
        )
    redacted = _SENSITIVE_KV_PATTERN.sub(r"\1\2[REDACTED]", redacted)
    return redacted


def archive_cli_error(error: BaseException, command_name: str | None = None) -> CliErrorReport:
    """Persist an exception traceback under the Open Link Token logs directory."""
    logs_dir = get_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)

    reference_id = uuid.uuid4().hex[:8]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = logs_dir / f"{timestamp}-{reference_id}.log"

    command_line = _redact_sensitive_text(command_name or "<unknown>")
    traceback_text = _redact_sensitive_text(
        "".join(traceback.format_exception(type(error), error, error.__traceback__))
    )
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


def archive_unexpected_error(error: BaseException, command_name: str | None = None) -> CliErrorReport:
    """Backward-compatible wrapper for archived unexpected failures."""
    return archive_cli_error(error, command_name=command_name)


def format_error_reference_message(report: CliErrorReport) -> str:
    """Build the shared stderr handoff for archived CLI failures."""
    stack_trace_message = f"Stack trace: {report.log_path}"
    isatty = getattr(sys.stderr, "isatty", None)
    use_color = not os.getenv("NO_COLOR") and bool(isatty and isatty())
    if not use_color:
        return stack_trace_message

    return f"\033[90m{stack_trace_message}\033[0m"


def format_unexpected_error_message(report: CliErrorReport, command_name: str | None = None) -> str:
    """Build the stderr message shown to users for archived unexpected failures."""
    command_context = f" while running '{command_name}'" if command_name else ""
    return f"Error: Unexpected internal error{command_context}.\n{format_error_reference_message(report)}"
