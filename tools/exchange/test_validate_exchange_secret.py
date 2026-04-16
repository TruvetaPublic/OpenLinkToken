#!/usr/bin/env python3
"""Executable tests for the JWE exchange secret validator."""

from __future__ import annotations

# ruff: noqa: E402
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_SCRIPT = REPO_ROOT / "tools" / "exchange" / "validate_exchange_secret.py"
sys.path.insert(0, str(REPO_ROOT / "tools" / "exchange"))
sys.path.insert(0, str(REPO_ROOT / "lib" / "python" / "openlinktoken-cli" / "src" / "main"))
sys.path.insert(0, str(REPO_ROOT / "lib" / "python" / "openlinktoken" / "src" / "main"))

from validate_exchange_secret import decrypt_exchange_secret

from openlinktoken_cli.commands.open_token_command import OpenLinkTokenCommand
from openlinktoken_cli.util.ec_key_utils import generate_key_pair


def _generate_exchange_fixture(tmp_path: Path, hashing_secret: str) -> tuple[Path, Path, Path]:
    """Generate an exchange config plus sender and recipient private key paths."""
    recipient_private_pem, recipient_public_pem = generate_key_pair("P-256")
    recipient_private_key_path = tmp_path / "recipient.private.pem"
    recipient_public_key_path = tmp_path / "recipient.public.pem"
    recipient_private_key_path.write_bytes(recipient_private_pem)
    recipient_public_key_path.write_bytes(recipient_public_pem)

    exchange_config_path = tmp_path / "generated.exchange.json"
    with patch("pathlib.Path.home", return_value=tmp_path):
        exit_code = OpenLinkTokenCommand.execute(
            [
                "initiate-exchange",
                "--name",
                "sender-local",
                "--public-key",
                str(recipient_public_key_path),
                "--output",
                str(exchange_config_path),
                "--hashingsecret",
                hashing_secret,
            ]
        )

    assert exit_code == 0, "initiate-exchange should generate the JWE exchange config"
    assert json.loads(exchange_config_path.read_text(encoding="utf-8"))["version"] == 1
    sender_private_key_path = tmp_path / ".openlinktoken" / "sender-local.private.pem"
    return exchange_config_path, sender_private_key_path, recipient_private_key_path


def test_sender_private_key_decrypts_generated_exchange() -> None:
    """The sender-side local private key can recover the hashing secret."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        expected_secret = "shared-secret"
        exchange_config_path, sender_private_key_path, _ = _generate_exchange_fixture(tmp_path, expected_secret)

        plaintext_secret = decrypt_exchange_secret(exchange_config_path, sender_private_key_path)

        assert plaintext_secret == expected_secret.encode("utf-8")


def test_recipient_private_key_decrypts_generated_exchange() -> None:
    """The recipient private key can recover the same hashing secret."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        expected_secret = "shared-secret"
        exchange_config_path, _, recipient_private_key_path = _generate_exchange_fixture(tmp_path, expected_secret)

        plaintext_secret = decrypt_exchange_secret(exchange_config_path, recipient_private_key_path)

        assert plaintext_secret == expected_secret.encode("utf-8")


def test_validator_help_lists_private_key_stdin() -> None:
    """The validator help text should advertise --private-key-stdin."""
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )

    assert completed.returncode == 0
    assert "--private-key-stdin" in completed.stdout


def test_validator_accepts_private_key_from_stdin() -> None:
    """The validator can read the private key PEM from stdin when requested."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        expected_secret = "shared-secret"
        exchange_config_path, _, recipient_private_key_path = _generate_exchange_fixture(tmp_path, expected_secret)

        completed = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR_SCRIPT),
                "--exchange-config",
                str(exchange_config_path),
                "--private-key-stdin",
                "--expected-secret",
                expected_secret,
            ],
            input=recipient_private_key_path.read_text(encoding="utf-8"),
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

        assert completed.returncode == 0, completed.stderr
        assert "Recovered secret matches expected secret." in completed.stdout


def test_validator_rejects_empty_private_key_from_stdin() -> None:
    """The validator fails clearly when --private-key-stdin receives no key bytes."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        expected_secret = "shared-secret"
        exchange_config_path, _, _ = _generate_exchange_fixture(tmp_path, expected_secret)

        completed = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR_SCRIPT),
                "--exchange-config",
                str(exchange_config_path),
                "--private-key-stdin",
                "--expected-secret",
                expected_secret,
            ],
            input="",
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

        assert completed.returncode == 1
        assert "stdin" in completed.stderr.lower()
        assert "empty" in completed.stderr.lower()


def test_local_private_key_is_auto_resolved_by_recipient_kid() -> None:
    """The validator can locate the sender private key from the local kid mapping."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        expected_secret = "auto-resolved-secret"
        exchange_config_path, _, _ = _generate_exchange_fixture(tmp_path, expected_secret)

        with patch("pathlib.Path.home", return_value=tmp_path):
            plaintext_secret = decrypt_exchange_secret(exchange_config_path, None)

        assert plaintext_secret == expected_secret.encode("utf-8")


def test_rejects_private_key_that_matches_no_recipient() -> None:
    """A non-recipient private key fails with a clean mismatch error."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        exchange_config_path, _, _ = _generate_exchange_fixture(tmp_path, "mismatch-secret")
        unrelated_private_pem, _ = generate_key_pair("P-256")
        unrelated_private_key_path = tmp_path / "unrelated.private.pem"
        unrelated_private_key_path.write_bytes(unrelated_private_pem)

        try:
            decrypt_exchange_secret(exchange_config_path, unrelated_private_key_path)
        except ValueError as error:
            assert "recipient" in str(error).lower()
        else:
            raise AssertionError("Expected a clean recipient-mismatch ValueError")


def main() -> int:
    """Run the validator tests as a simple executable script."""
    tests = [
        test_sender_private_key_decrypts_generated_exchange,
        test_recipient_private_key_decrypts_generated_exchange,
        test_validator_help_lists_private_key_stdin,
        test_validator_accepts_private_key_from_stdin,
        test_validator_rejects_empty_private_key_from_stdin,
        test_local_private_key_is_auto_resolved_by_recipient_kid,
        test_rejects_private_key_that_matches_no_recipient,
    ]

    print("Running validate_exchange_secret.py tests")
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
        print("All validator tests PASSED")
        return 0

    print("Validator tests FAILED")
    return 1


if __name__ == "__main__":
    exit_code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
