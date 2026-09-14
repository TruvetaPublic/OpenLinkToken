#!/usr/bin/env python3
"""Measure standalone CLI time to first output and command completion."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path


def _measure_once(executable: Path, arguments: list[str], environment: dict[str, str]) -> dict[str, float | None]:
    """Run one CLI command and record first output and completion timings."""
    started = time.perf_counter()
    process = subprocess.Popen(
        [str(executable), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=environment,
    )
    first_line = process.stdout.readline() if process.stdout is not None else ""
    first_output_ms = (time.perf_counter() - started) * 1000 if first_line else None
    remaining_output, _ = process.communicate()
    completed_ms = (time.perf_counter() - started) * 1000
    if process.returncode:
        raise RuntimeError(f"{executable} {' '.join(arguments)} failed with exit code {process.returncode}")
    return {
        "first_output_ms": first_output_ms,
        "completed_ms": completed_ms,
    }


def measure(executable: Path, arguments: list[str], environment: dict[str, str], repeats: int = 3) -> dict[str, object]:
    """Measure cold startup and repeated invocations of one CLI command."""
    return {
        "arguments": arguments,
        "runs": [_measure_once(executable, arguments, environment) for _ in range(repeats)],
    }


def main() -> int:
    """Measure the supported startup commands and write JSON results."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("startup-measurements.json"))
    args = parser.parse_args()

    environment = os.environ.copy()
    environment["OLT_DISABLE_UPDATE_CHECK"] = "1"
    with tempfile.TemporaryDirectory(prefix="olt-startup-") as home:
        environment["HOME"] = home
        environment["USERPROFILE"] = home
        commands = [["--help"], ["--version"], ["generate-key-pair", "--help"]]
        measurements = [measure(args.executable, command, environment) for command in commands]

    result = {"executable": str(args.executable), "measurements": measurements}
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
