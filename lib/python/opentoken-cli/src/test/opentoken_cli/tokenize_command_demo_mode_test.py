"""
Copyright (c) Truveta. All rights reserved.
"""

import json
from pathlib import Path

import pytest
from opentoken_cli.commands.open_token_command import OpenTokenCommand

# HMAC-SHA256 over 32 bytes → base64 → always exactly 44 characters
NORMAL_MODE_TOKEN_LENGTH = 44

# Token.BLANK sentinel written when a rule cannot produce a valid token
BLANK_TOKEN = "0" * 64


class TestTokenizeCommandDemoMode:
    """Tests for the --demo-mode flag on the tokenize subcommand."""

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

    # ------------------------------------------------------------------
    # Mode selection
    # ------------------------------------------------------------------

    def test_demo_mode_succeeds_without_hashing_secret(self, temp_dir: Path):
        """Demo mode should not require --hashingsecret."""
        args = [
            "tokenize",
            "-i",
            str(temp_dir / "input.csv"),
            "-t",
            "csv",
            "-o",
            str(temp_dir / "output.csv"),
            "--demo-mode",
        ]
        exit_code = OpenTokenCommand.execute(args)
        assert exit_code == 0

    def test_normal_mode_fails_without_hashing_secret(self, temp_dir: Path):
        """Normal mode must reject execution when --hashingsecret is absent."""
        args = [
            "tokenize",
            "-i",
            str(temp_dir / "input.csv"),
            "-t",
            "csv",
            "-o",
            str(temp_dir / "output.csv"),
        ]
        exit_code = OpenTokenCommand.execute(args)
        assert exit_code != 0

    def test_demo_mode_accepts_optional_hashing_secret(self, temp_dir: Path):
        """Demo mode should succeed even when --hashingsecret is provided (ignored)."""
        args = [
            "tokenize",
            "-i",
            str(temp_dir / "input.csv"),
            "-t",
            "csv",
            "-o",
            str(temp_dir / "output.csv"),
            "--demo-mode",
            "--hashingsecret",
            self.HASHING_SECRET,
        ]
        exit_code = OpenTokenCommand.execute(args)
        assert exit_code == 0

    def test_normal_mode_succeeds_with_hashing_secret(self, temp_dir: Path):
        """Normal mode should succeed when --hashingsecret is provided."""
        args = [
            "tokenize",
            "-i",
            str(temp_dir / "input.csv"),
            "-t",
            "csv",
            "-o",
            str(temp_dir / "output.csv"),
            "--hashingsecret",
            self.HASHING_SECRET,
        ]
        exit_code = OpenTokenCommand.execute(args)
        assert exit_code == 0

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------

    def test_normal_mode_fails_with_blank_hashing_secret(self, temp_dir: Path):
        """A blank (whitespace-only) hashing secret must be rejected in normal mode."""
        args = [
            "tokenize",
            "-i",
            str(temp_dir / "input.csv"),
            "-t",
            "csv",
            "-o",
            str(temp_dir / "output.csv"),
            "--hashingsecret",
            "   ",
        ]
        exit_code = OpenTokenCommand.execute(args)
        assert exit_code != 0

    def test_invalid_input_type_rejected(self, temp_dir: Path):
        """An unrecognised -t value should always be rejected."""
        args = [
            "tokenize",
            "-i",
            str(temp_dir / "input.csv"),
            "-t",
            "json",
            "-o",
            str(temp_dir / "output.csv"),
            "--demo-mode",
        ]
        exit_code = OpenTokenCommand.execute(args)
        assert exit_code != 0

    # ------------------------------------------------------------------
    # Output shape
    # ------------------------------------------------------------------

    def test_demo_mode_tokens_are_not_hmac_base64(self, temp_dir: Path):
        """
        Demo tokens use PassthroughTokenizer so they are never 44-char HMAC base64.
        Multi-attribute rules (T1-T4) produce pipe-separated signatures; at least
        one such token must appear in the output.
        """
        output_csv = temp_dir / "output.csv"
        OpenTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-t",
                "csv",
                "-o",
                str(output_csv),
                "--demo-mode",
            ]
        )

        tokens = _extract_tokens(output_csv)
        assert tokens, "Expected at least one non-blank token in demo mode"

        # At least one multi-attribute rule should produce a pipe-separated token
        assert any(
            "|" in t for t in tokens
        ), "Expected at least one pipe-separated signature token (T1-T4 rules)"

        # None of the tokens should be a 44-char HMAC-SHA256 base64 string
        for token in tokens:
            assert (
                len(token) != NORMAL_MODE_TOKEN_LENGTH
            ), f"Demo-mode token must not be a 44-char HMAC base64 string, got: {token}"

    def test_normal_mode_tokens_are_44_char_hmac_base64(self, temp_dir: Path):
        """Normal mode tokens are HMAC-SHA256 base64, always exactly 44 characters."""
        output_csv = temp_dir / "output.csv"
        OpenTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-t",
                "csv",
                "-o",
                str(output_csv),
                "--hashingsecret",
                self.HASHING_SECRET,
            ]
        )

        tokens = _extract_tokens(output_csv)
        assert tokens, "Expected at least one non-blank token in normal mode"

        for token in tokens:
            assert (
                len(token) == NORMAL_MODE_TOKEN_LENGTH
            ), f"Normal-mode token must be a 44-char HMAC base64 string, got: {token!r}"

    def test_demo_and_normal_mode_produce_different_tokens(self, temp_dir: Path):
        """Demo-mode and normal-mode outputs must differ for the same input."""
        demo_output = temp_dir / "demo_output.csv"
        normal_output = temp_dir / "normal_output.csv"

        OpenTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-t",
                "csv",
                "-o",
                str(demo_output),
                "--demo-mode",
            ]
        )
        OpenTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-t",
                "csv",
                "-o",
                str(normal_output),
                "--hashingsecret",
                self.HASHING_SECRET,
            ]
        )

        assert demo_output.read_text() != normal_output.read_text()

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def test_demo_mode_metadata_omits_hashing_secret_hash(self, temp_dir: Path):
        """Demo mode must not write HashingSecretHash to the metadata file."""
        OpenTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-t",
                "csv",
                "-o",
                str(temp_dir / "output.csv"),
                "--demo-mode",
            ]
        )

        metadata = _read_metadata(temp_dir / "output.metadata.json")
        assert (
            "HashingSecretHash" not in metadata
        ), "Demo mode must not include HashingSecretHash in metadata"

    def test_normal_mode_metadata_contains_hashing_secret_hash(self, temp_dir: Path):
        """Normal mode must write HashingSecretHash to the metadata file."""
        OpenTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-t",
                "csv",
                "-o",
                str(temp_dir / "output.csv"),
                "--hashingsecret",
                self.HASHING_SECRET,
            ]
        )

        metadata = _read_metadata(temp_dir / "output.metadata.json")
        assert (
            "HashingSecretHash" in metadata
        ), "Normal mode must include HashingSecretHash in metadata"

    def test_demo_mode_metadata_contains_processing_counters(self, temp_dir: Path):
        """Demo mode metadata must still record row and attribute statistics."""
        OpenTokenCommand.execute(
            [
                "tokenize",
                "-i",
                str(temp_dir / "input.csv"),
                "-t",
                "csv",
                "-o",
                str(temp_dir / "output.csv"),
                "--demo-mode",
            ]
        )

        metadata = _read_metadata(temp_dir / "output.metadata.json")
        assert (
            metadata.get("TotalRows") == 2
        ), f"Expected TotalRows=2 but got {metadata.get('TotalRows')}"


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
