# SPDX-License-Identifier: MIT

import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from openlinktoken_cli.commands.open_link_token_command import OpenLinkTokenCommand
from openlinktoken_cli.util.ec_key_utils import generate_key_pair

# SHA-256 produces 32 bytes; hex encoding produces exactly 64 characters
HASH_ONLY_TOKEN_LENGTH = 64

# HMAC-SHA256 over 32 bytes → base64 → always exactly 44 characters
NORMAL_MODE_TOKEN_LENGTH = 44

# Token.BLANK sentinel written when a rule cannot produce a valid token
BLANK_TOKEN = "0" * 64


class TestTokenizeCommandHashOnly:
    """Tests for the --hash-only flag on the tokenize subcommand."""

    HASHING_SECRET = "TestHashingSecret"

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory with a two-row CSV input."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber\n"
            "test-001,John,Doe,98004,Male,2000-01-15,123-45-6789\n"
            "test-002,Jane,Smith,12345,Female,1990-05-20,234-56-7890\n"
        )
        return tmp_path

    def _create_exchange_config(self, temp_dir: Path, name: str = "hash-only") -> tuple[Path, Path]:
        """Create an exchange config and return ``(exchange_config_path, private_key_path)``."""
        _, partner_public_pem = generate_key_pair("P-256")
        partner_public_key_path = temp_dir / f"{name}.partner.public.pem"
        partner_public_key_path.write_bytes(partner_public_pem)
        exchange_config_path = temp_dir / f"{name}.exchange.json"

        with patch("pathlib.Path.home", return_value=temp_dir):
            exit_code = OpenLinkTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    name,
                    "--public-key",
                    str(partner_public_key_path),
                    "--output",
                    str(exchange_config_path),
                    "--hashingsecret",
                    self.HASHING_SECRET,
                ]
            )

        assert exit_code == 0
        return exchange_config_path, temp_dir / ".openlinktoken" / f"{name}.private.pem"

    # ------------------------------------------------------------------
    # Mode selection
    # ------------------------------------------------------------------

    def test_hash_only_mode_succeeds_without_exchange_config(self, temp_dir: Path):
        """Hash-only mode should not require an exchange config."""
        exit_code = OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(temp_dir / "output.csv"),
                "--hash-only",
            ]
        )
        assert exit_code == 0

    def test_hash_only_mode_accepts_bare_csv_paths_from_working_directory(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Bare CSV filenames should resolve relative to the working directory."""
        monkeypatch.chdir(temp_dir)

        exit_code = OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                "input.csv",
                "-o",
                "output.csv",
                "--hash-only",
            ]
        )

        assert exit_code == 0
        assert (temp_dir / "output.csv").exists()
        assert (temp_dir / "output.metadata.json").exists()

    def test_hash_only_mode_rejects_exchange_config(self, temp_dir: Path):
        """Hash-only mode should reject --exchange-config."""
        exchange_config, _ = self._create_exchange_config(temp_dir, "hash-with-config")
        exit_code = OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(temp_dir / "output.csv"),
                "--hash-only",
                "--exchange-config",
                str(exchange_config),
            ]
        )
        assert exit_code != 0

    def test_hash_only_mode_rejects_private_key(self, temp_dir: Path):
        """Hash-only mode should reject --private-key."""
        _, private_key = self._create_exchange_config(temp_dir, "hash-with-key")
        exit_code = OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(temp_dir / "output.csv"),
                "--hash-only",
                "--private-key",
                str(private_key),
            ]
        )
        assert exit_code != 0

    def test_hash_only_and_demo_mode_are_mutually_exclusive(self, temp_dir: Path):
        """--hash-only and --demo-mode cannot be used together."""
        exit_code = OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(temp_dir / "output.csv"),
                "--hash-only",
                "--demo-mode",
            ]
        )
        assert exit_code != 0

    # ------------------------------------------------------------------
    # Output shape
    # ------------------------------------------------------------------

    def test_hash_only_tokens_are_64_char_hex(self, temp_dir: Path):
        """Hash-only tokens are SHA-256 hex encoded, always exactly 64 characters."""
        output_csv = temp_dir / "output.csv"
        OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(output_csv),
                "--hash-only",
            ]
        )

        tokens = _extract_tokens(output_csv)
        assert tokens, "Expected at least one non-blank token in hash-only mode"

        for token in tokens:
            assert len(token) == HASH_ONLY_TOKEN_LENGTH, (
                f"Hash-only token must be a 64-char hex string, got {len(token)} chars: {token!r}"
            )
            assert all(c in "0123456789abcdef" for c in token), f"Hash-only token must be lowercase hex, got: {token!r}"

    def test_hash_only_and_normal_mode_produce_different_tokens(self, temp_dir: Path):
        """Hash-only and normal-mode outputs must differ for the same input."""
        hash_only_output = temp_dir / "hash_only_output.csv"
        normal_output = temp_dir / "normal_output.csv"
        exchange_config, private_key = self._create_exchange_config(temp_dir, "hash-vs-normal")

        OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(hash_only_output),
                "--hash-only",
            ]
        )
        OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(normal_output),
                "--exchange-config",
                str(exchange_config),
                "--private-key",
                str(private_key),
            ]
        )

        assert hash_only_output.read_text() != normal_output.read_text()

    def test_hash_only_and_demo_mode_produce_different_tokens(self, temp_dir: Path):
        """Hash-only and demo-mode outputs must differ for the same input."""
        hash_only_output = temp_dir / "hash_only_output.csv"
        demo_output = temp_dir / "demo_output.csv"

        OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(hash_only_output),
                "--hash-only",
            ]
        )
        OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(demo_output),
                "--demo-mode",
            ]
        )

        assert hash_only_output.read_text() != demo_output.read_text()

    def test_hash_only_tokens_are_deterministic(self, temp_dir: Path):
        """Running hash-only twice on the same input must produce identical output."""
        output1 = temp_dir / "output1.csv"
        output2 = temp_dir / "output2.csv"

        for out in (output1, output2):
            OpenLinkTokenCommand.execute(
                [
                    "tokenize",
                    "-i",
                    str(temp_dir / "input.csv"),
                    "-o",
                    str(out),
                    "--hash-only",
                ]
            )

        assert output1.read_text() == output2.read_text()

    def test_hash_only_logs_deterministic_sha256_warning(self, temp_dir: Path, caplog: pytest.LogCaptureFixture):
        """Hash-only mode should warn that output is deterministic SHA-256 and not for exchange use."""
        with caplog.at_level(logging.WARNING, logger="openlinktoken_cli.commands.tokenize_command"):
            exit_code = OpenLinkTokenCommand.execute(
                [
                    "tokenize",
                    "-i",
                    str(temp_dir / "input.csv"),
                    "-o",
                    str(temp_dir / "output.csv"),
                    "--hash-only",
                ]
            )

        assert exit_code == 0
        assert "output tokens are deterministic SHA-256 hashes without HMAC" in caplog.text
        assert "Do not use hash-only output for production or cross-organisation exchange." in caplog.text

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def test_hash_only_metadata_omits_hashing_secret_hash(self, temp_dir: Path):
        """Hash-only mode must not write HashingSecretHash to the metadata file."""
        OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(temp_dir / "output.csv"),
                "--hash-only",
            ]
        )

        metadata = _read_metadata(temp_dir / "output.metadata.json")
        assert "HashingSecretHash" not in metadata, "Hash-only mode must not include HashingSecretHash in metadata"

    def test_hash_only_metadata_contains_processing_counters(self, temp_dir: Path):
        """Hash-only mode metadata must still record row and attribute statistics."""
        OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(temp_dir / "output.csv"),
                "--hash-only",
            ]
        )

        metadata = _read_metadata(temp_dir / "output.metadata.json")
        assert metadata.get("TotalRows") == 2, f"Expected TotalRows=2 but got {metadata.get('TotalRows')}"

    # ------------------------------------------------------------------
    # --hash-record-ids compatibility
    # ------------------------------------------------------------------

    def test_hash_only_supports_hash_record_ids(self, temp_dir: Path):
        """--hash-only should work together with --hash-record-ids."""
        output_csv = temp_dir / "output.csv"
        exit_code = OpenLinkTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(output_csv),
                "--hash-only",
                "--hash-record-ids",
            ]
        )
        assert exit_code == 0

        lines = output_csv.read_text().splitlines()
        headers = [h.strip() for h in lines[0].split(",")]
        record_id_col = headers.index("RecordId")

        for line in lines[1:]:
            cols = line.split(",")
            if len(cols) > record_id_col:
                record_id = cols[record_id_col].strip()
                # SHA-256 hex of the original IDs → 64-char hex
                assert len(record_id) == 64, f"Expected hashed 64-char RecordId, got: {record_id!r}"
                assert all(c in "0123456789abcdef" for c in record_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_tokens(csv_path: Path) -> list[str]:
    """Return non-blank, non-sentinel token values from the Token column of a CSV."""
    lines = csv_path.read_text().splitlines()
    if not lines:
        return []

    headers = [h.strip() for h in lines[0].split(",")]
    try:
        token_col = headers.index("Token")
    except ValueError:
        return []

    tokens = []
    for line in lines[1:]:
        cols = line.split(",")
        if len(cols) > token_col:
            token = cols[token_col].strip()
            if token and token != BLANK_TOKEN:
                tokens.append(token)
    return tokens


def _read_metadata(path: Path) -> dict:
    """Read and parse a metadata JSON file."""
    return json.loads(path.read_text())
