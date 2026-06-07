#!/usr/bin/env python3
"""Tests for the local CLI matrix exercise harness."""

from __future__ import annotations

# ruff: noqa: E402
import sys
from pathlib import Path
from subprocess import CompletedProcess

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "cli"))

from run_cli_matrix import CommandResult, CommandSpec, build_command_plan, execute_command_plan, format_summary


def test_build_command_plan_covers_all_cli_subcommands(tmp_path: Path) -> None:
    """The default command plan should touch every subcommand with local-safe invocations."""
    plan = build_command_plan(tmp_path, pause_seconds=0.25)

    command_names = {spec.name for spec in plan}
    assert command_names >= {
        "root-help",
        "help-overview",
        "help-package",
        "tokenize-help",
        "tokenize-demo",
        "tokenize-hash",
        "tokenize-auto-output",
        "encrypt-help",
        "encrypt-tokenized-output",
        "decrypt-help",
        "decrypt-encrypted-output",
        "package-help",
        "package-csv",
        "package-auto-output",
        "generate-key-pair-help",
        "generate-key-pair-recipient",
        "initiate-exchange-help",
        "initiate-exchange-local",
        "update-help",
    }
    assert "update-dry-run" not in command_names
    assert all(spec.pause_after_seconds == 0.25 for spec in plan[:-1])
    assert plan[-1].pause_after_seconds == 0.0


def test_build_command_plan_can_opt_into_live_update_check(tmp_path: Path) -> None:
    """Live update dry-run should be included only when explicitly requested."""
    plan = build_command_plan(tmp_path, pause_seconds=0.0, include_live_update=True)

    update_step = next(spec for spec in plan if spec.name == "update-dry-run")
    assert update_step.args[-3:] == ["update", "--dry-run", "--yes"]


def test_execute_command_plan_pauses_between_steps() -> None:
    """Execution should sleep between commands and preserve per-command results."""
    calls: list[list[str]] = []
    pauses: list[float] = []

    def fake_runner(args: list[str], **_: object) -> CompletedProcess[str]:
        calls.append(args)
        return CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    def fake_sleep(seconds: float) -> None:
        pauses.append(seconds)

    plan = [
        CommandSpec(name="first", args=["python", "--help"], pause_after_seconds=0.5),
        CommandSpec(name="second", args=["python", "-V"], pause_after_seconds=0.25),
        CommandSpec(name="third", args=["python", "-c", "print('done')"], pause_after_seconds=0.0),
    ]

    results = execute_command_plan(plan, runner=fake_runner, sleeper=fake_sleep)

    assert [result.spec.name for result in results] == ["first", "second", "third"]
    assert calls == [spec.args for spec in plan]
    assert pauses == [0.5, 0.25]
    assert all(result.returncode == 0 for result in results)


def test_format_summary_reports_failures_and_slowest_command() -> None:
    """The summary should make failures and timing hotspots easy to spot."""
    plan = [
        CommandSpec(name="quick-help", args=["python", "--help"], pause_after_seconds=0.0),
        CommandSpec(name="slow-flow", args=["python", "-V"], pause_after_seconds=0.0),
    ]
    results = [
        CommandResult(spec=plan[0], returncode=0, duration_seconds=0.11, stdout="help", stderr=""),
        CommandResult(spec=plan[1], returncode=1, duration_seconds=1.45, stdout="", stderr="boom"),
    ]

    summary = format_summary(results)

    assert "Commands run: 2" in summary
    assert "Passed: 1" in summary
    assert "Failed: 1" in summary
    assert "slowest" in summary.lower()
    assert "slow-flow" in summary
