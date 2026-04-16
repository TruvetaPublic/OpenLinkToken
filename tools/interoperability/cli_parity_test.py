#!/usr/bin/env python3
"""
Python CLI tests for Open Link Token.

Ensures that the Python CLI provides the expected command structure,
help output, and behavior for all subcommands.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def find_repo_root():
    """Find the repository root directory."""
    current = Path(__file__).resolve()
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find repository root")


def run_python_cli(*args):
    """Run Python CLI and return output."""
    repo_root = find_repo_root()
    cli_dir = repo_root / "lib/python/openlinktoken-cli"

    # Set PYTHONPATH to include the CLI directory
    env = os.environ.copy()
    python_path = str(cli_dir / "src/main")
    core_path = str(repo_root / "lib/python/openlinktoken/src/main")
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{python_path}:{core_path}:{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = f"{python_path}:{core_path}"

    result = subprocess.run(
        [sys.executable, "-m", "openlinktoken_cli.main"] + list(args),
        capture_output=True,
        text=True,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


def test_help_command():
    """Test that the Python CLI supports the help command."""
    print(f"\n{YELLOW}Testing help command...{RESET}")

    # Test root help
    python_code, python_out, python_err = run_python_cli("--help")

    assert python_code == 0, f"Python --help failed with code {python_code}"

    # Check output contains command names
    commands = ["tokenize", "encrypt", "decrypt", "package", "help"]
    for cmd in commands:
        assert cmd in python_out, f"Python help missing '{cmd}' command"

    print(f"{GREEN}✓ Python CLI supports --help and lists all commands{RESET}")

    # Test explicit help command
    python_code, python_out, python_err = run_python_cli("help")

    assert python_code == 0, f"Python 'help' command failed with code {python_code}"

    print(f"{GREEN}✓ Python CLI supports 'help' command{RESET}")


def test_help_for_subcommands():
    """Test that the Python CLI supports help for each subcommand."""
    print(f"\n{YELLOW}Testing help for subcommands...{RESET}")

    commands = ["tokenize", "encrypt", "decrypt", "package"]

    for cmd in commands:
        # Test with --help flag
        python_code, python_out, python_err = run_python_cli(cmd, "--help")

        assert python_code == 0, f"Python '{cmd} --help' failed with code {python_code}"

        # Check for required parameters in help output
        if cmd in ["tokenize", "package"]:
            assert "--hashingsecret" in python_out or "hashingsecret" in python_out, (
                f"Python '{cmd}' help missing hashingsecret"
            )

        if cmd in ["encrypt", "decrypt", "package"]:
            assert "--encryptionkey" in python_out or "encryptionkey" in python_out, (
                f"Python '{cmd}' help missing encryptionkey"
            )

        # Test with help command
        python_code, python_out, python_err = run_python_cli("help", cmd)

        assert python_code == 0, f"Python 'help {cmd}' failed with code {python_code}"

        print(f"{GREEN}✓ Python CLI supports help for '{cmd}'{RESET}")


def test_command_existence():
    """Test that the Python CLI recognizes all required commands."""
    print(f"\n{YELLOW}Testing command existence...{RESET}")

    commands = ["tokenize", "encrypt", "decrypt", "package", "help"]

    for cmd in commands:
        # Just test that the command is recognized (not that it succeeds without args)
        # We expect these to fail with missing arguments, but not with "unknown command"
        python_code, python_out, python_err = run_python_cli(cmd)

        # Check that we don't get "unknown command" errors
        python_combined = python_out + python_err

        assert "unknown command" not in python_combined.lower(), f"Python doesn't recognize '{cmd}' command"

        print(f"{GREEN}✓ Python CLI recognizes '{cmd}' command{RESET}")


def test_version_flag():
    """Test that the Python CLI supports the --version flag."""
    print(f"\n{YELLOW}Testing --version flag...{RESET}")

    python_code, python_out, python_err = run_python_cli("--version")

    assert python_code == 0, f"Python --version failed with code {python_code}"

    # Should output version information
    python_combined = python_out + python_err
    version_pattern = re.compile(r"\b\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?\b")

    assert version_pattern.search(python_combined) or "Open Link Token" in python_combined, (
        "Python version output missing version info"
    )

    print(f"{GREEN}✓ Python CLI supports --version{RESET}")


def main():
    """Run all CLI parity tests."""
    print(f"\n{YELLOW}{'=' * 70}{RESET}")
    print(f"{YELLOW}Open Link Token Python CLI Tests{RESET}")
    print(f"{YELLOW}{'=' * 70}{RESET}")

    try:
        test_help_command()
        test_help_for_subcommands()
        test_command_existence()
        test_version_flag()

        print(f"\n{GREEN}{'=' * 70}{RESET}")
        print(f"{GREEN}All CLI parity tests passed!{RESET}")
        print(f"{GREEN}{'=' * 70}{RESET}\n")
        return 0

    except AssertionError as e:
        print(f"\n{RED}{'=' * 70}{RESET}")
        print(f"{RED}Test failed: {e}{RESET}")
        print(f"{RED}{'=' * 70}{RESET}\n")
        return 1
    except Exception as e:
        print(f"\n{RED}{'=' * 70}{RESET}")
        print(f"{RED}Unexpected error: {e}{RESET}")
        print(f"{RED}{'=' * 70}{RESET}\n")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
