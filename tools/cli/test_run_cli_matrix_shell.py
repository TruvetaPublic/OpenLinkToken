#!/usr/bin/env python3
"""Tests for the review-friendly shell CLI matrix harness."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "tools" / "cli" / "run_cli_matrix.sh"


def test_shell_harness_dry_run_prints_reviewable_commands() -> None:
    """The shell harness should expose the exact planned CLI calls without executing them."""
    completed = subprocess.run(
        [str(SCRIPT_PATH), "--dry-run", "--pause-seconds", "0"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Dry run" in completed.stdout
    assert "root-help" in completed.stdout
    assert "tokenize-demo" in completed.stdout
    assert "generate-key-pair-recipient" in completed.stdout
    assert "generate-key-pair-p384" in completed.stdout
    assert "generate-key-pair-p521" in completed.stdout
    assert "initiate-exchange-local" in completed.stdout
    assert "update-help" in completed.stdout
    assert "python -m opentoken_cli.main" in completed.stdout
    assert "command: python -m opentoken_cli.main --no-update-check --help" in completed.stdout
    assert "environment:" not in completed.stdout
    assert "$ HOME=" not in completed.stdout


def test_shell_harness_prompts_before_advancing_by_default() -> None:
    """The default mode should wait for confirmation before moving to the next step."""
    completed = subprocess.run(
        [str(SCRIPT_PATH), "--pause-seconds", "0"],
        input="q\n",
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Press Enter to continue" in completed.stdout
    assert "Stopping at user request." in completed.stdout
    assert "Commands run: 1" in completed.stdout


def test_shell_harness_auto_continue_runs_without_confirmation() -> None:
    """The opt-out flag should run the full matrix without interactive prompts."""
    completed = subprocess.run(
        [str(SCRIPT_PATH), "--pause-seconds", "0", "--auto-continue"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Press Enter to continue" not in completed.stdout
    assert "Commands run: 19" in completed.stdout
