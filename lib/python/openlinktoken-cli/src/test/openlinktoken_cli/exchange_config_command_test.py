# SPDX-License-Identifier: MIT

import json
import os
from pathlib import Path
from unittest.mock import patch

from jwcrypto import jwe, jwk

from openlinktoken.exchange_jwe import (
    EXCHANGE_JWE_CONTENT_TYPE,
    EXCHANGE_JWE_ENCRYPTION,
    EXCHANGE_JWE_RECIPIENT_ALGORITHM,
    EXCHANGE_JWE_TYPE,
    build_exchange_envelope,
)
from openlinktoken_cli.commands.open_link_token_command import OpenLinkTokenCommand
from openlinktoken_cli.util.ec_key_utils import fingerprint_to_kid, generate_key_pair, public_key_fingerprint
from openlinktoken_cli.util.exchange_config import default_exchange_config_path


class TestExchangeConfigCommands:
    """Focused command tests for exchange-config-driven secret resolution."""

    def test_tokenize_rejects_future_v2_exchange_config(self, tmp_path: Path, caplog) -> None:
        """Tokenize should reject unsupported v2 configs during exchange-config loading."""
        input_csv = _write_input_csv(tmp_path)
        output_csv = tmp_path / "output.csv"
        exchange_config_path, private_key_path = _write_future_v2_exchange_config(tmp_path)

        exit_code = OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(input_csv),
                "-t",
                "csv",
                "-o",
                str(output_csv),
                "--exchange-config",
                str(exchange_config_path),
                "--private-key",
                str(private_key_path),
            ]
        )

        assert exit_code != 0
        assert "Unsupported exchange config version '2'. Supported versions: 1." in caplog.text

    def test_encrypt_rejects_future_v2_exchange_config(self, tmp_path: Path, caplog) -> None:
        """Encrypt should reject unsupported v2 configs during exchange-config loading."""
        input_csv = _write_tokenized_csv(tmp_path)
        output_csv = tmp_path / "encrypted.csv"
        exchange_config_path, private_key_path = _write_future_v2_exchange_config(tmp_path)

        exit_code = OpenLinkTokenCommand.execute(
            [
                "encrypt",
                "-i",
                str(input_csv),
                "-t",
                "csv",
                "-o",
                str(output_csv),
                "--exchange-config",
                str(exchange_config_path),
                "--private-key",
                str(private_key_path),
            ]
        )

        assert exit_code != 0
        assert "Unsupported exchange config version '2'. Supported versions: 1." in caplog.text

    def test_tokenize_uses_default_date_based_exchange_config_path(self, tmp_path: Path) -> None:
        """Consumer commands should use the same date-based default config name as initiate-exchange."""
        input_csv = _write_input_csv(tmp_path)
        output_csv = tmp_path / "output.csv"
        default_config_path = tmp_path / default_exchange_config_path().name
        private_key_path = _write_current_exchange_config(default_config_path, tmp_path)

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("pathlib.Path.home", return_value=tmp_path):
                exit_code = OpenLinkTokenCommand.execute(
                    [
                        "tokenize",
                        "-i",
                        str(input_csv),
                        "-t",
                        "csv",
                        "-o",
                        str(output_csv),
                    ]
                )
        finally:
            os.chdir(original_cwd)

        assert exit_code == 0
        assert output_csv.exists()
        assert private_key_path.exists()

    def test_missing_default_exchange_config_fails_clearly(self, tmp_path: Path, caplog) -> None:
        """Omitting --exchange-config should fail clearly when the default path does not exist."""
        input_csv = _write_input_csv(tmp_path)
        output_csv = tmp_path / "output.csv"

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            with patch("pathlib.Path.home", return_value=tmp_path):
                exit_code = OpenLinkTokenCommand.execute(
                    [
                        "tokenize",
                        "-i",
                        str(input_csv),
                        "-t",
                        "csv",
                        "-o",
                        str(output_csv),
                    ]
                )
        finally:
            os.chdir(original_cwd)

        assert exit_code != 0
        assert "Exchange config" in caplog.text
        assert "initiate-exchange" in caplog.text

    def test_encrypt_and_decrypt_round_trip_using_derived_transport_key(self, tmp_path: Path) -> None:
        """Encrypt and decrypt should round-trip using the exchange-derived transport key."""
        input_csv = _write_input_csv(tmp_path)
        tokenized_csv = tmp_path / "tokenized.csv"
        encrypted_csv = tmp_path / "encrypted.csv"
        decrypted_csv = tmp_path / "decrypted.csv"
        exchange_config_path = tmp_path / "roundtrip.exchange.json"
        private_key_path = _write_current_exchange_config(exchange_config_path, tmp_path)

        tokenize_exit_code = OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(input_csv),
                "-t",
                "csv",
                "-o",
                str(tokenized_csv),
                "--exchange-config",
                str(exchange_config_path),
                "--private-key",
                str(private_key_path),
            ]
        )
        encrypt_exit_code = OpenLinkTokenCommand.execute(
            [
                "encrypt",
                "-i",
                str(tokenized_csv),
                "-t",
                "csv",
                "-o",
                str(encrypted_csv),
                "--exchange-config",
                str(exchange_config_path),
                "--private-key",
                str(private_key_path),
            ]
        )
        decrypt_exit_code = OpenLinkTokenCommand.execute(
            [
                "decrypt",
                "-i",
                str(encrypted_csv),
                "-t",
                "csv",
                "-o",
                str(decrypted_csv),
                "--exchange-config",
                str(exchange_config_path),
                "--private-key",
                str(private_key_path),
            ]
        )

        assert tokenize_exit_code == 0
        assert encrypt_exit_code == 0
        assert decrypt_exit_code == 0
        assert decrypted_csv.read_text() == tokenized_csv.read_text()


def _write_input_csv(tmp_path: Path) -> Path:
    input_csv = tmp_path / "input.csv"
    input_csv.write_text(
        "RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber\n"
        "test-001,John,Doe,98004,Male,2000-01-01,123-45-6789\n",
        encoding="utf-8",
    )
    return input_csv


def _write_tokenized_csv(tmp_path: Path) -> Path:
    tokenized_csv = tmp_path / "tokenized.csv"
    tokenized_csv.write_text(
        "RecordId,RuleNumber,RuleExpression,RuleWeight,RuleCount,Token\ntest-001,1,T1,1.0,1,SGVsbG9Ub2tlbg==\n",
        encoding="utf-8",
    )
    return tokenized_csv


def _write_current_exchange_config(exchange_config_path: Path, tmp_path: Path) -> Path:
    sender_private_pem, sender_public_pem = generate_key_pair("P-256")
    _, recipient_public_pem = generate_key_pair("P-256")
    config = build_exchange_envelope(
        exchange_name="current",
        hashing_secret=b"legacy-hashing-secret",
        sender_public_pem=sender_public_pem,
        recipient_public_pem=recipient_public_pem,
        curve="P-256",
        created_at="2026-03-12T00:00:00Z",
        exchange_id="exchange-current",
    )
    exchange_config_path.write_text(json.dumps(config), encoding="utf-8")
    private_key_path = tmp_path / ".openlinktoken" / "current.private.pem"
    public_key_path = tmp_path / ".openlinktoken" / "current.public.pem"
    public_key_path.parent.mkdir(parents=True, exist_ok=True)
    private_key_path.write_bytes(sender_private_pem)
    public_key_path.write_bytes(sender_public_pem)
    return private_key_path


def _write_future_v2_exchange_config(tmp_path: Path) -> tuple[Path, Path]:
    sender_private_pem, sender_public_pem = generate_key_pair("P-256")
    _, recipient_public_pem = generate_key_pair("P-256")
    payload = {
        "exchangeName": "legacy",
        "hashingSecret": "bGVnYWN5LWhhc2hpbmctc2VjcmV0",
        "hashingSecretEncoding": "base64url",
        "senderKeyFingerprint": public_key_fingerprint(sender_public_pem),
        "recipientKeyFingerprint": public_key_fingerprint(recipient_public_pem),
        "curve": "P-256",
        "createdAt": "2026-03-12T00:00:00Z",
        "exchangeId": "exchange-legacy",
    }
    protected = {
        "typ": EXCHANGE_JWE_TYPE,
        "cty": EXCHANGE_JWE_CONTENT_TYPE,
        "enc": EXCHANGE_JWE_ENCRYPTION,
    }
    envelope = jwe.JWE(
        json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        protected=json.dumps(protected, separators=(",", ":")),
    )
    for public_pem in (sender_public_pem, recipient_public_pem):
        envelope.add_recipient(
            jwk.JWK.from_pem(public_pem),
            header=json.dumps(
                {
                    "alg": EXCHANGE_JWE_RECIPIENT_ALGORITHM,
                    "kid": fingerprint_to_kid(public_key_fingerprint(public_pem)),
                },
                separators=(",", ":"),
            ),
        )

    exchange_config_path = tmp_path / "future.exchange.json"
    serialized = json.loads(envelope.serialize(compact=False))
    serialized["version"] = 2
    exchange_config_path.write_text(json.dumps(serialized), encoding="utf-8")

    private_key_path = tmp_path / ".openlinktoken" / "future.private.pem"
    public_key_path = tmp_path / ".openlinktoken" / "future.public.pem"
    public_key_path.parent.mkdir(parents=True, exist_ok=True)
    private_key_path.write_bytes(sender_private_pem)
    public_key_path.write_bytes(sender_public_pem)
    return exchange_config_path, private_key_path
