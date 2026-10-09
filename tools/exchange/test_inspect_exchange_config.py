#!/usr/bin/env python3
"""Executable tests for the exchange config inspection helper."""

from __future__ import annotations

# ruff: noqa: E402
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INSPECTOR_SCRIPT = REPO_ROOT / "tools" / "exchange" / "inspect_exchange_config.py"
sys.path.insert(0, str(REPO_ROOT / "tools" / "exchange"))

from test_validate_exchange_secret import _generate_exchange_fixture, _generate_v2_exchange_fixture


def test_inspector_help_lists_key_inputs() -> None:
    """Check that the inspector help advertises path and environment key inputs.

    Args:
        None; this function takes no arguments.

    Returns:
        None.
    """
    completed = subprocess.run(
        [sys.executable, str(INSPECTOR_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert completed.returncode == 0
    assert "--exchange-config" in completed.stdout
    assert "--private-key" in completed.stdout
    assert "--private-key-env" in completed.stdout


def test_inspector_prints_v1_summary() -> None:
    """Check that the summary includes v1 metadata and the resolved private-key role.

    Args:
        None; this function takes no arguments.

    Returns:
        None.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        exchange_config_path, _, recipient_private_key_path = _generate_exchange_fixture(tmp_path, "shared-secret")
        completed = subprocess.run(
            [
                sys.executable,
                str(INSPECTOR_SCRIPT),
                "--exchange-config",
                str(exchange_config_path),
                "--private-key",
                str(recipient_private_key_path),
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

    assert completed.returncode == 0, completed.stderr
    assert "Crypto suite" in completed.stdout
    assert "Config version  : 1" in completed.stdout
    assert "Private key role : recipient" in completed.stdout
    assert "Sender" in completed.stdout
    assert "Recipient" in completed.stdout


def test_inspector_prints_v2_summary() -> None:
    """Check that the summary includes v2 suite and bundle identifiers.

    Args:
        None; this function takes no arguments.

    Returns:
        None.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        exchange_config_path, _, recipient_private_bundle_path = _generate_v2_exchange_fixture(
            tmp_path, "shared-v2-secret"
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(INSPECTOR_SCRIPT),
                "--exchange-config",
                str(exchange_config_path),
                "--private-key",
                str(recipient_private_bundle_path),
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

    assert completed.returncode == 0, completed.stderr
    assert "Crypto suite    : suite-pq-v1" in completed.stdout
    assert "Config version  : 2" in completed.stdout
    assert "Private key role : recipient" in completed.stdout
    assert "Sender    : sha256:" in completed.stdout
    assert "Recipient : sha256:" in completed.stdout


def test_inspector_outputs_v2_payload_as_json() -> None:
    """Check that JSON output contains the decrypted v2 payload.

    Args:
        None; this function takes no arguments.

    Returns:
        None.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        exchange_config_path, _, recipient_private_bundle_path = _generate_v2_exchange_fixture(
            tmp_path, "json-v2-secret"
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(INSPECTOR_SCRIPT),
                "--exchange-config",
                str(exchange_config_path),
                "--private-key",
                str(recipient_private_bundle_path),
                "--json",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["cryptoSuite"] == "suite-pq-v1"
    assert payload["hashingSecretEncoding"] == "base64url"


def main() -> int:
    """Run the inspection tests as a simple executable script.

    Args:
        None; this function takes no arguments.

    Returns:
        Exit code 0 when all tests pass, or 1 when any test fails.
    """
    tests = [
        test_inspector_help_lists_key_inputs,
        test_inspector_prints_v1_summary,
        test_inspector_prints_v2_summary,
        test_inspector_outputs_v2_payload_as_json,
    ]

    print("Running inspect_exchange_config.py tests")
    print("=" * 48)
    all_passed = True
    for test in tests:
        try:
            test()
        except AssertionError as error:
            all_passed = False
            print(f"FAIL: {test.__name__}: {error}")
        except Exception as error:  # pragma: no cover - script-level failure reporting
            all_passed = False
            print(f"FAIL: {test.__name__}: {error}")
        else:
            print(f"PASS: {test.__name__}")

    print("=" * 48)
    if all_passed:
        print("All inspect_exchange_config.py tests PASSED")
        return 0

    print("inspect_exchange_config.py tests FAILED")
    return 1


if __name__ == "__main__":
    exit_code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
