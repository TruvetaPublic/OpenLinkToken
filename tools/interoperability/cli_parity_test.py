#!/usr/bin/env python3
"""
Cross-language CLI parity tests for OpenToken.

Ensures that Java and Python CLIs provide identical command structures,
help output, and behavior parity across all subcommands.
"""

import subprocess
import sys
import os
import re
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


def run_java_cli(*args):
    """Run Java CLI and return output."""
    repo_root = find_repo_root()
    jar_dir = repo_root / "lib/java/opentoken-cli/target"
    jar_candidates = sorted(
        [
            path
            for path in jar_dir.glob("opentoken-cli-*.jar")
            if path.is_file() and not path.name.startswith("original-")
        ]
    )

    if not jar_candidates:
        raise FileNotFoundError(
            f"Java JAR not found in {jar_dir}. Run: cd lib/java && mvn clean package -DskipTests"
        )

    jar_path = jar_candidates[-1]
    
    result = subprocess.run(
        ["java", "-jar", str(jar_path)] + list(args),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def run_python_cli(*args):
    """Run Python CLI and return output."""
    repo_root = find_repo_root()
    cli_dir = repo_root / "lib/python/opentoken-cli"
    
    # Set PYTHONPATH to include the CLI directory
    env = os.environ.copy()
    python_path = str(cli_dir / "src/main")
    core_path = str(repo_root / "lib/python/opentoken/src/main")
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{python_path}:{core_path}:{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = f"{python_path}:{core_path}"
    
    result = subprocess.run(
        [sys.executable, "-m", "opentoken_cli.main"] + list(args),
        capture_output=True,
        text=True,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


def test_help_command():
    """Test that both CLIs support the help command."""
    print(f"\n{YELLOW}Testing help command...{RESET}")
    
    # Test root help
    java_code, java_out, java_err = run_java_cli("--help")
    python_code, python_out, python_err = run_python_cli("--help")
    
    assert java_code == 0, f"Java --help failed with code {java_code}"
    assert python_code == 0, f"Python --help failed with code {python_code}"
    
    # Check both outputs contain command names
    commands = ["tokenize", "encrypt", "decrypt", "package", "help"]
    for cmd in commands:
        assert cmd in java_out, f"Java help missing '{cmd}' command"
        assert cmd in python_out, f"Python help missing '{cmd}' command"
    
    print(f"{GREEN}✓ Both CLIs support --help and list all commands{RESET}")
    
    # Test explicit help command
    java_code, java_out, java_err = run_java_cli("help")
    python_code, python_out, python_err = run_python_cli("help")
    
    assert java_code == 0, f"Java 'help' command failed with code {java_code}"
    assert python_code == 0, f"Python 'help' command failed with code {python_code}"
    
    print(f"{GREEN}✓ Both CLIs support 'help' command{RESET}")


def test_help_for_subcommands():
    """Test that both CLIs support help for each subcommand."""
    print(f"\n{YELLOW}Testing help for subcommands...{RESET}")
    
    commands = ["tokenize", "encrypt", "decrypt", "package"]
    
    for cmd in commands:
        # Test with --help flag
        java_code, java_out, java_err = run_java_cli(cmd, "--help")
        python_code, python_out, python_err = run_python_cli(cmd, "--help")
        
        assert java_code == 0, f"Java '{cmd} --help' failed with code {java_code}"
        assert python_code == 0, f"Python '{cmd} --help' failed with code {python_code}"
        
        # Check for required parameters in help output
        if cmd in ["tokenize", "package"]:
            assert "--hashingsecret" in java_out or "hashingsecret" in java_out, \
                f"Java '{cmd}' help missing hashingsecret"
            assert "--hashingsecret" in python_out or "hashingsecret" in python_out, \
                f"Python '{cmd}' help missing hashingsecret"
        
        if cmd in ["encrypt", "decrypt", "package"]:
            assert "--encryptionkey" in java_out or "encryptionkey" in java_out, \
                f"Java '{cmd}' help missing encryptionkey"
            assert "--encryptionkey" in python_out or "encryptionkey" in python_out, \
                f"Python '{cmd}' help missing encryptionkey"
        
        # Test with help command
        java_code, java_out, java_err = run_java_cli("help", cmd)
        python_code, python_out, python_err = run_python_cli("help", cmd)
        
        assert java_code == 0, f"Java 'help {cmd}' failed with code {java_code}"
        assert python_code == 0, f"Python 'help {cmd}' failed with code {python_code}"
        
        print(f"{GREEN}✓ Both CLIs support help for '{cmd}'{RESET}")


def test_command_existence():
    """Test that both CLIs recognize all required commands."""
    print(f"\n{YELLOW}Testing command existence...{RESET}")
    
    commands = ["tokenize", "encrypt", "decrypt", "package", "help"]
    
    for cmd in commands:
        # Just test that the command is recognized (not that it succeeds without args)
        # We expect these to fail with missing arguments, but not with "unknown command"
        java_code, java_out, java_err = run_java_cli(cmd)
        python_code, python_out, python_err = run_python_cli(cmd)
        
        # Check that we don't get "unknown command" errors
        java_combined = java_out + java_err
        python_combined = python_out + python_err
        
        assert "Unknown command" not in java_combined, f"Java doesn't recognize '{cmd}' command"
        assert "unknown command" not in python_combined.lower(), f"Python doesn't recognize '{cmd}' command"
        
        print(f"{GREEN}✓ Both CLIs recognize '{cmd}' command{RESET}")


def test_version_flag():
    """Test that both CLIs support the --version flag."""
    print(f"\n{YELLOW}Testing --version flag...{RESET}")
    
    java_code, java_out, java_err = run_java_cli("--version")
    python_code, python_out, python_err = run_python_cli("--version")
    
    assert java_code == 0, f"Java --version failed with code {java_code}"
    assert python_code == 0, f"Python --version failed with code {python_code}"
    
    # Both should output version information
    java_combined = java_out + java_err
    python_combined = python_out + python_err
    version_pattern = re.compile(r"\b\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?\b")
    
    assert version_pattern.search(java_combined) or "OpenToken" in java_combined, \
        "Java version output missing version info"
    assert version_pattern.search(python_combined) or "OpenToken" in python_combined, \
        "Python version output missing version info"
    
    print(f"{GREEN}✓ Both CLIs support --version{RESET}")


def main():
    """Run all CLI parity tests."""
    print(f"\n{YELLOW}{'='*70}{RESET}")
    print(f"{YELLOW}OpenToken CLI Parity Tests{RESET}")
    print(f"{YELLOW}{'='*70}{RESET}")
    
    try:
        test_help_command()
        test_help_for_subcommands()
        test_command_existence()
        test_version_flag()
        
        print(f"\n{GREEN}{'='*70}{RESET}")
        print(f"{GREEN}All CLI parity tests passed!{RESET}")
        print(f"{GREEN}{'='*70}{RESET}\n")
        return 0
        
    except AssertionError as e:
        print(f"\n{RED}{'='*70}{RESET}")
        print(f"{RED}Test failed: {e}{RESET}")
        print(f"{RED}{'='*70}{RESET}\n")
        return 1
    except Exception as e:
        print(f"\n{RED}{'='*70}{RESET}")
        print(f"{RED}Unexpected error: {e}{RESET}")
        print(f"{RED}{'='*70}{RESET}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
