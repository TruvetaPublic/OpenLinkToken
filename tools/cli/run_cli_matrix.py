#!/usr/bin/env python3
"""Run a local OpenToken CLI command matrix against the current worktree."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess
from typing import Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_SOURCE_ROOT = REPO_ROOT / "lib" / "python" / "opentoken-cli" / "src" / "main"
CORE_SOURCE_ROOT = REPO_ROOT / "lib" / "python" / "opentoken" / "src" / "main"

DEFAULT_HASHING_SECRET = "LocalHarnessHashingSecret"
DEFAULT_ENCRYPTION_KEY = "0123456789abcdef0123456789abcdef"


@dataclass(frozen=True)
class CommandSpec:
    """Describe one CLI command execution in the local matrix plan."""

    name: str
    args: list[str]
    pause_after_seconds: float
    cwd: Path = REPO_ROOT
    env: dict[str, str] | None = None


@dataclass(frozen=True)
class CommandResult:
    """Capture the outcome of one CLI command execution."""

    spec: CommandSpec
    returncode: int
    duration_seconds: float
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        """Return whether the command succeeded."""
        return self.returncode == 0


def build_command_plan(
    tmp_path: Path,
    pause_seconds: float = 0.25,
    include_live_update: bool = False,
) -> list[CommandSpec]:
    """Build a local-safe CLI exercise plan covering all subcommands.

    Args:
        tmp_path: Temporary workspace root for generated fixtures and overridden HOME.
        pause_seconds: Delay inserted after each non-final command.
        include_live_update: When True, append a networked ``update --dry-run --yes``
            step after the help-only update coverage.

    Returns:
        A list of command specifications ready for execution.
    """
    if pause_seconds < 0:
        raise ValueError("pause_seconds must be non-negative")

    workspace_root = tmp_path.resolve()
    input_dir = workspace_root / "inputs"
    output_dir = workspace_root / "outputs"
    home_dir = workspace_root / "home"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    home_dir.mkdir(parents=True, exist_ok=True)

    person_csv = input_dir / "people.csv"
    person_csv.write_text(_build_people_csv_fixture(), encoding="utf-8")

    tokenized_demo_csv = output_dir / "tokenized-demo.csv"
    tokenized_hash_csv = output_dir / "tokenized-hash.csv"
    encrypted_csv = output_dir / "encrypted.csv"
    decrypted_csv = output_dir / "decrypted.csv"
    packaged_csv = output_dir / "packaged.csv"
    exchange_json = output_dir / "local.exchange.json"
    recipient_public_key = home_dir / ".opentoken" / "recipient.public.pem"

    env = _build_command_env(home_dir)
    plan = [
        CommandSpec("root-help", _cli_args("--no-update-check", "--help"), pause_seconds, env=env),
        CommandSpec("help-overview", _cli_args("--no-update-check", "help"), pause_seconds, env=env),
        CommandSpec("help-package", _cli_args("--no-update-check", "help", "package"), pause_seconds, env=env),
        CommandSpec("tokenize-help", _cli_args("--no-update-check", "tokenize", "--help"), pause_seconds, env=env),
        CommandSpec(
            "tokenize-demo",
            _cli_args(
                "--no-update-check",
                "tokenize",
                "--input",
                str(person_csv),
                "--input-type",
                "csv",
                "--output",
                str(tokenized_demo_csv),
                "--demo-mode",
            ),
            pause_seconds,
            env=env,
        ),
        CommandSpec(
            "tokenize-hash",
            _cli_args(
                "--no-update-check",
                "tokenize",
                "--input",
                str(person_csv),
                "--input-type",
                "csv",
                "--output",
                str(tokenized_hash_csv),
                "--hashingsecret",
                DEFAULT_HASHING_SECRET,
            ),
            pause_seconds,
            env=env,
        ),
        CommandSpec("encrypt-help", _cli_args("--no-update-check", "encrypt", "--help"), pause_seconds, env=env),
        CommandSpec(
            "encrypt-tokenized-output",
            _cli_args(
                "--no-update-check",
                "encrypt",
                "--input",
                str(tokenized_hash_csv),
                "--input-type",
                "csv",
                "--output",
                str(encrypted_csv),
                "--encryptionkey",
                DEFAULT_ENCRYPTION_KEY,
            ),
            pause_seconds,
            env=env,
        ),
        CommandSpec("decrypt-help", _cli_args("--no-update-check", "decrypt", "--help"), pause_seconds, env=env),
        CommandSpec(
            "decrypt-encrypted-output",
            _cli_args(
                "--no-update-check",
                "decrypt",
                "--input",
                str(encrypted_csv),
                "--input-type",
                "csv",
                "--output",
                str(decrypted_csv),
                "--encryptionkey",
                DEFAULT_ENCRYPTION_KEY,
            ),
            pause_seconds,
            env=env,
        ),
        CommandSpec("package-help", _cli_args("--no-update-check", "package", "--help"), pause_seconds, env=env),
        CommandSpec(
            "package-csv",
            _cli_args(
                "--no-update-check",
                "package",
                "--input",
                str(person_csv),
                "--input-type",
                "csv",
                "--output",
                str(packaged_csv),
                "--hashingsecret",
                DEFAULT_HASHING_SECRET,
                "--encryptionkey",
                DEFAULT_ENCRYPTION_KEY,
            ),
            pause_seconds,
            env=env,
        ),
        CommandSpec(
            "generate-key-pair-help",
            _cli_args("--no-update-check", "generate-key-pair", "--help"),
            pause_seconds,
            env=env,
        ),
        CommandSpec(
            "generate-key-pair-recipient",
            _cli_args(
                "--no-update-check",
                "generate-key-pair",
                "--name",
                "recipient",
            ),
            pause_seconds,
            env=env,
        ),
        CommandSpec(
            "initiate-exchange-help",
            _cli_args("--no-update-check", "initiate-exchange", "--help"),
            pause_seconds,
            env=env,
        ),
        CommandSpec(
            "initiate-exchange-local",
            _cli_args(
                "--no-update-check",
                "initiate-exchange",
                "--name",
                "sender-local",
                "--public-key",
                str(recipient_public_key),
                "--output",
                str(exchange_json),
                "--hashingsecret",
                DEFAULT_HASHING_SECRET,
            ),
            pause_seconds,
            env=env,
        ),
        CommandSpec("update-help", _cli_args("--no-update-check", "update", "--help"), pause_seconds, env=env),
    ]

    if include_live_update:
        plan.append(
            CommandSpec(
                "update-dry-run",
                _cli_args("--no-update-check", "update", "--dry-run", "--yes"),
                pause_seconds,
                env=env,
            )
        )

    return _apply_pause_configuration(plan, pause_seconds)


def execute_command_plan(
    plan: Sequence[CommandSpec],
    runner: Callable[..., CompletedProcess[str]] = subprocess.run,
    sleeper: Callable[[float], None] = time.sleep,
) -> list[CommandResult]:
    """Execute the CLI matrix plan and capture a result object for each step.

    Args:
        plan: The command plan to run in order.
        runner: Injectable subprocess runner, primarily for testing.
        sleeper: Injectable sleep function, primarily for testing.

    Returns:
        A result object for each command in execution order.
    """
    results: list[CommandResult] = []

    for spec in plan:
        started = time.perf_counter()
        try:
            completed = runner(
                spec.args,
                capture_output=True,
                text=True,
                check=False,
                cwd=str(spec.cwd),
                env=spec.env,
            )
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            return_code = completed.returncode
        except Exception as error:  # pragma: no cover - defensive path for local execution failures
            stdout = ""
            stderr = f"{type(error).__name__}: {error}"
            return_code = 1

        duration_seconds = time.perf_counter() - started
        results.append(
            CommandResult(
                spec=spec,
                returncode=return_code,
                duration_seconds=duration_seconds,
                stdout=stdout,
                stderr=stderr,
            )
        )

        if spec.pause_after_seconds > 0:
            sleeper(spec.pause_after_seconds)

    return results


def format_summary(results: Sequence[CommandResult]) -> str:
    """Render a readable text summary for a completed CLI matrix run."""
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    failed = total - passed

    lines = [
        "OpenToken CLI matrix summary",
        f"Commands run: {total}",
        f"Passed: {passed}",
        f"Failed: {failed}",
    ]

    if results:
        slowest = max(results, key=lambda result: result.duration_seconds)
        lines.append(f"Slowest command: {slowest.spec.name} ({slowest.duration_seconds:.2f}s, rc={slowest.returncode})")
    else:
        lines.append("Slowest command: n/a")

    lines.append("")
    lines.append("Per-command results:")

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"  {status:<4} {result.spec.name:<28} {result.duration_seconds:>6.2f}s  rc={result.returncode}")

        stderr_preview = _preview_output(result.stderr)
        stdout_preview = _preview_output(result.stdout)
        if not result.passed and stderr_preview:
            lines.append(f"        stderr: {stderr_preview}")
        elif result.passed and stdout_preview:
            lines.append(f"        stdout: {stdout_preview}")

    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the local CLI command matrix harness."""
    parser = argparse.ArgumentParser(
        description=(
            "Run a local OpenToken CLI command matrix against the current worktree "
            "using 'python -m opentoken_cli.main'."
        )
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=0.25,
        help="Pause duration inserted after each non-final command (default: 0.25).",
    )
    parser.add_argument(
        "--include-live-update",
        action="store_true",
        default=False,
        help="Also run 'update --dry-run --yes' after the default help-only update coverage.",
    )
    args = parser.parse_args(argv)
    if args.pause_seconds < 0:
        parser.error("--pause-seconds must be non-negative")

    with tempfile.TemporaryDirectory(prefix="opentoken-cli-matrix-") as temp_dir:
        workspace = Path(temp_dir)
        print(f"Using temporary workspace: {workspace}")
        plan = build_command_plan(
            workspace,
            pause_seconds=args.pause_seconds,
            include_live_update=args.include_live_update,
        )
        results = execute_command_plan(plan)
        print(format_summary(results))

    return 1 if any(result.returncode != 0 for result in results) else 0


def _apply_pause_configuration(plan: Sequence[CommandSpec], pause_seconds: float) -> list[CommandSpec]:
    """Return plan copies with pauses on all non-final commands and zero on the final command."""
    configured_plan: list[CommandSpec] = []
    last_index = len(plan) - 1

    for index, spec in enumerate(plan):
        configured_pause = pause_seconds if index < last_index else 0.0
        configured_plan.append(
            CommandSpec(
                name=spec.name,
                args=list(spec.args),
                pause_after_seconds=configured_pause,
                cwd=spec.cwd,
                env=dict(spec.env) if spec.env is not None else None,
            )
        )

    return configured_plan


def _build_command_env(home_dir: Path) -> dict[str, str]:
    """Build a subprocess environment that targets local source and a temporary HOME."""
    env = os.environ.copy()
    pythonpath_entries = [str(CLI_SOURCE_ROOT), str(CORE_SOURCE_ROOT)]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        pythonpath_entries.append(existing_pythonpath)

    env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    env["HOME"] = str(home_dir)
    env["NO_COLOR"] = "1"
    return env


def _build_people_csv_fixture() -> str:
    """Return a compact but valid CSV fixture for local CLI exercises."""
    return textwrap.dedent(
        """\
        RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber
        demo-001,John,Doe,98004,Male,2000-01-01,123-45-6789
        demo-002,Jane,Smith,12345,Female,1990-05-15,234-56-7890
        """
    )


def _cli_args(*command_args: str) -> list[str]:
    """Build a current-source CLI invocation."""
    return [sys.executable, "-m", "opentoken_cli.main", *command_args]


def _preview_output(output: str, limit: int = 120) -> str:
    """Return a one-line preview of command output suitable for summaries."""
    collapsed = " ".join(output.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3]}..."


if __name__ == "__main__":
    raise SystemExit(main())
