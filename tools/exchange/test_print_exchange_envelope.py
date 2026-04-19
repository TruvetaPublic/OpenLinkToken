#!/usr/bin/env python3
"""Executable tests for the exchange envelope inspection helper."""

from __future__ import annotations

# ruff: noqa: E402
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INSPECTOR_SCRIPT = REPO_ROOT / "tools" / "exchange" / "print_exchange_envelope.py"
SAMPLE_EXCHANGE_CONFIG = REPO_ROOT / "lib" / "python" / "openlinktoken-cli" / "openlinktoken-2026-04-19.exchange.json"

from test_validate_exchange_secret import _generate_exchange_fixture


def test_inspector_help_lists_exchange_config() -> None:
    """The inspector help text should advertise the exchange and private-key inputs."""
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
    assert "--private-key-stdin" in completed.stdout


def test_inspector_prints_decoded_protected_header() -> None:
    """The inspector should print the raw envelope plus a decoded protected header."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        exchange_config_path, _, recipient_private_key_path = _generate_exchange_fixture(temp_path, "shared-secret")
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
    rendered_envelope = json.loads(completed.stdout)
    assert rendered_envelope["version"] == 1
    assert rendered_envelope["protectedDecoded"] == {
        "typ": "openlinktoken-exchange+jwe",
        "cty": "application/openlinktoken-exchange+json",
        "enc": "A256GCM",
    }
    assert len(rendered_envelope["recipients"]) == 2
    assert rendered_envelope["ciphertext"]


def test_inspector_prints_decrypted_payload_with_private_key() -> None:
    """The inspector should decrypt the JWE payload when given a matching private key."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        expected_secret = "shared-secret"
        exchange_config_path, _, recipient_private_key_path = _generate_exchange_fixture(temp_path, expected_secret)

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
    rendered_envelope = json.loads(completed.stdout)
    assert rendered_envelope["decryptedPayload"]["exchangeName"] == "sender-local"
    assert rendered_envelope["decryptedPayload"]["hashingSecretEncoding"] == "base64url"


def test_inspector_rejects_invalid_protected_header() -> None:
    """The inspector should fail clearly when the protected header is not base64url JSON."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        invalid_exchange_config_path = temp_path / "invalid.exchange.json"
        invalid_exchange_config = json.loads(SAMPLE_EXCHANGE_CONFIG.read_text(encoding="utf-8"))
        invalid_exchange_config["protected"] = "not-valid-base64"
        invalid_exchange_config_path.write_text(json.dumps(invalid_exchange_config), encoding="utf-8")

        completed = subprocess.run(
            [sys.executable, str(INSPECTOR_SCRIPT), "--exchange-config", str(invalid_exchange_config_path)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

    assert completed.returncode == 1
    assert "protected" in completed.stderr.lower()


def main() -> int:
    """Run the inspector tests as a simple executable script."""
    tests = [
        test_inspector_help_lists_exchange_config,
        test_inspector_prints_decoded_protected_header,
        test_inspector_prints_decrypted_payload_with_private_key,
        test_inspector_rejects_invalid_protected_header,
    ]

    print("Running print_exchange_envelope.py tests")
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
        print("All inspector tests PASSED")
        return 0

    print("Inspector tests FAILED")
    return 1


if __name__ == "__main__":
    exit_code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
