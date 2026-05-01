# SPDX-License-Identifier: MIT

from pathlib import Path

from openlinktoken_cli.util.cli_error_reporter import format_dimmed_stderr_message
from openlinktoken_cli.util.cli_run_reporter import CliRunReporter


class TestCliRunReporter:
    """Unit tests for CLI run summary rendering helpers."""

    def test_summarize_count_lines_sorts_multiple_items_alphabetically(self):
        """Multi-item summaries should be expanded into alphabetized detail lines."""
        lines = CliRunReporter.summarize_count_lines(
            "Blank tokens by rule",
            {"T2": 8, "T4": 7, "T1": 6},
        )

        assert lines == [
            "Blank tokens by rule:",
            "  T1: 6",
            "  T2: 8",
            "  T4: 7",
        ]

    def test_summarize_count_lines_limits_invalid_attributes_before_sorting(self):
        """Limited summaries should keep the highest counts, then render them alphabetically."""
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

        assert lines == [
            "Top invalid attributes:",
            "  BirthDate: 3",
            "  LastName: 2",
            "  SocialSecurityNumber: 4",
        ]

    def test_format_dimmed_stderr_message_uses_dark_grey_for_interactive_terminals(self, monkeypatch):
        """Interactive terminals should render reference lines with the shared dim styling."""
        monkeypatch.setattr("sys.stderr.isatty", lambda: True)

        message = format_dimmed_stderr_message(f"Detailed log: {Path('/tmp/run.log')}")

        assert message == "\x1b[90mDetailed log: /tmp/run.log\x1b[0m"
