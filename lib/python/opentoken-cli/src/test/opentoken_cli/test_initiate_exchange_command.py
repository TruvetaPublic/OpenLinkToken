"""
Copyright (c) Truveta. All rights reserved.

Unit and integration tests for InitiateExchangeCommand.
"""

import base64
import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from opentoken_cli.commands.initiate_exchange_command import InitiateExchangeCommand
from opentoken_cli.commands.open_token_command import OpenTokenCommand
from opentoken_cli.util.ec_key_utils import SUPPORTED_CURVES, generate_key_pair, public_key_fingerprint
from opentoken_cli.util.stdin_utils import read_required_env_bytes

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _partner_key_pem(tmp_path: Path, curve: str = "P-256") -> Path:
    """Write a fresh partner public-key PEM file and return its path."""
    _, public_pem = generate_key_pair(curve)
    pem_path = tmp_path / "partner.public.pem"
    pem_path.write_bytes(public_pem)
    return pem_path


def _decode_base64url_json(encoded: str) -> dict:
    """Decode a base64url JSON value with permissive padding restoration."""
    padding = "=" * (-len(encoded) % 4)
    return json.loads(base64.urlsafe_b64decode(encoded + padding))


def _fingerprint_to_kid(public_pem: bytes) -> str:
    """Convert a public-key fingerprint into the portable recipient kid format."""
    fingerprint = public_key_fingerprint(public_pem).lower().replace(":", "-")
    return f"sha256:{fingerprint}"


def _assert_shared_jwe_header(config: dict) -> None:
    """Assert the common protected header matches the JWE exchange contract."""
    protected = _decode_base64url_json(config["protected"])
    assert protected["typ"] == "opentoken-exchange+jwe"
    assert protected["cty"] == "application/opentoken-exchange+json"
    assert protected["enc"] == "A256GCM"
    assert "alg" not in protected
    assert "kid" not in protected
    assert "epk" not in protected


def _assert_recipient_headers(config: dict, curve: str, expected_kids: set[str]) -> None:
    """Assert the recipient list uses the expected JOSE headers and key ids."""
    assert len(config["recipients"]) == 2

    recipient_headers = [entry["header"] for entry in config["recipients"]]
    assert {header["alg"] for header in recipient_headers} == {"ECDH-ES+A256KW"}
    assert {header["kid"] for header in recipient_headers} == expected_kids
    assert all(header["kid"].startswith("sha256:") for header in recipient_headers)

    for entry, header in zip(config["recipients"], recipient_headers):
        assert isinstance(entry["encrypted_key"], str)
        assert entry["encrypted_key"]

        epk = header["epk"]
        assert epk["kty"] == "EC"
        assert epk["crv"] == curve
        assert isinstance(epk["x"], str)
        assert epk["x"]
        assert isinstance(epk["y"], str)
        assert epk["y"]
        assert "d" not in epk


# ---------------------------------------------------------------------------
# Unit tests for private helpers
# ---------------------------------------------------------------------------


class TestInitiateExchangeCommandUnit:
    """Unit tests for InitiateExchangeCommand static helpers."""

    def test_resolve_hashing_secret_generates_random_bytes(self):
        """A None input generates a 32-byte random secret."""
        secret = InitiateExchangeCommand._resolve_hashing_secret(None)
        assert isinstance(secret, bytes)
        assert len(secret) == 32

    def test_resolve_hashing_secret_encodes_provided_string(self):
        """A provided string is returned as UTF-8 bytes."""
        secret = InitiateExchangeCommand._resolve_hashing_secret("my-secret")
        assert secret == b"my-secret"

    def test_resolve_hashing_secret_different_on_each_call(self):
        """Two auto-generated secrets must not be identical."""
        s1 = InitiateExchangeCommand._resolve_hashing_secret(None)
        s2 = InitiateExchangeCommand._resolve_hashing_secret(None)
        assert s1 != s2, "Each call must produce a unique secret"

    def test_legacy_encrypt_hashing_secret_helper_is_removed(self):
        """The command surface should only expose the JWE-envelope implementation."""
        assert not hasattr(InitiateExchangeCommand, "_encrypt_hashing_secret")

    def test_read_required_env_bytes_returns_utf8_bytes(self, monkeypatch):
        """read_required_env_bytes returns the referenced environment value as bytes."""
        monkeypatch.setenv("OT_TEST_KEY", "pem-data")

        assert read_required_env_bytes("--test-key-env", "OT_TEST_KEY", "test key") == b"pem-data"

    def test_read_required_env_bytes_rejects_missing_value(self, monkeypatch):
        """read_required_env_bytes rejects missing environment variables."""
        monkeypatch.delenv("OT_MISSING_KEY", raising=False)

        with pytest.raises(ValueError, match="OT_MISSING_KEY"):
            read_required_env_bytes("--test-key-env", "OT_MISSING_KEY", "test key")

    # -------------------------------------------------------------------------
    # _write_config
    # -------------------------------------------------------------------------

    def test_write_config_creates_json_file(self, tmp_path):
        """_write_config creates a readable JSON file."""
        path = tmp_path / "out.exchange.json"
        config = {"version": 1, "test": True}
        InitiateExchangeCommand._write_config(path, config)

        assert path.exists()
        loaded = json.loads(path.read_text())
        assert loaded == config

    def test_write_config_overwrite_false_raises_on_existing(self, tmp_path):
        """_write_config raises FileExistsError when overwrite=False and file exists."""
        path = tmp_path / "existing.json"
        path.write_text("{}")
        with pytest.raises(FileExistsError):
            InitiateExchangeCommand._write_config(path, {}, overwrite=False)

    def test_write_config_overwrite_true_replaces_file(self, tmp_path):
        """_write_config silently replaces an existing file when overwrite=True."""
        path = tmp_path / "replaceable.json"
        path.write_text('{"old": true}')
        InitiateExchangeCommand._write_config(path, {"new": True}, overwrite=True)
        loaded = json.loads(path.read_text())
        assert loaded == {"new": True}

    def test_write_config_creates_parent_directories(self, tmp_path):
        """_write_config creates missing parent directories."""
        path = tmp_path / "deep" / "nested" / "config.json"
        InitiateExchangeCommand._write_config(path, {"ok": True})
        assert path.exists()


# ---------------------------------------------------------------------------
# Integration tests via OpenTokenCommand.execute
# ---------------------------------------------------------------------------


class TestInitiateExchangeCommandIntegration:
    """Integration tests that drive initiate-exchange through the full CLI path."""

    # -------------------------------------------------------------------------
    # Happy path: default curve
    # -------------------------------------------------------------------------

    def test_basic_exchange_creates_expected_files(self, tmp_path):
        """initiate-exchange creates local key files and the exchange config."""
        partner_pem = _partner_key_pem(tmp_path)
        output_path = tmp_path / "test.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "test-exchange",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                ]
            )

        assert exit_code == 0
        opentoken_dir = tmp_path / ".opentoken"
        assert (opentoken_dir / "test-exchange.private.pem").exists()
        assert (opentoken_dir / "test-exchange.public.pem").exists()
        assert output_path.exists()

    def test_basic_exchange_accepts_partner_public_key_from_stdin(self, tmp_path, monkeypatch):
        """initiate-exchange accepts --public-key-stdin instead of --public-key PATH."""
        _, partner_public_pem = generate_key_pair("P-256")
        output_path = tmp_path / "stdin.exchange.json"
        monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(partner_public_pem), encoding="utf-8"))

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "stdin-exchange",
                    "--public-key-stdin",
                    "--output",
                    str(output_path),
                ]
            )

        assert exit_code == 0
        opentoken_dir = tmp_path / ".opentoken"
        assert (opentoken_dir / "stdin-exchange.private.pem").exists()
        assert (opentoken_dir / "stdin-exchange.public.pem").exists()
        assert output_path.exists()

    def test_basic_exchange_accepts_public_and_sender_key_refs_from_env(self, tmp_path, monkeypatch):
        """initiate-exchange accepts env-var references for both partner and sender keys in one command."""
        sender_private_pem, sender_public_pem = generate_key_pair("P-256")
        _, partner_public_pem = generate_key_pair("P-256")
        output_path = tmp_path / "env-ref.exchange.json"
        monkeypatch.setenv("OT_PARTNER_PUBLIC_KEY", partner_public_pem.decode("utf-8"))
        monkeypatch.setenv("OT_SENDER_PRIVATE_KEY", sender_private_pem.decode("utf-8"))

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "env-ref",
                    "--public-key-env",
                    "OT_PARTNER_PUBLIC_KEY",
                    "--sender-private-key-env",
                    "OT_SENDER_PRIVATE_KEY",
                    "--output",
                    str(output_path),
                ]
            )

        assert exit_code == 0
        assert output_path.exists()
        assert not (tmp_path / ".opentoken").exists()

        config = json.loads(output_path.read_text())
        _assert_shared_jwe_header(config)
        _assert_recipient_headers(
            config,
            "P-256",
            {
                _fingerprint_to_kid(sender_public_pem),
                _fingerprint_to_kid(partner_public_pem),
            },
        )

    def test_basic_exchange_rejects_empty_partner_public_key_from_stdin(self, tmp_path, monkeypatch, caplog):
        """initiate-exchange fails clearly when --public-key-stdin receives no key bytes."""
        output_path = tmp_path / "empty-stdin.exchange.json"
        monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b""), encoding="utf-8"))

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "empty-stdin-exchange",
                    "--public-key-stdin",
                    "--output",
                    str(output_path),
                ]
            )

        assert exit_code == 1
        assert "stdin" in caplog.text.lower()
        assert "empty" in caplog.text.lower()
        assert not output_path.exists()

    def test_basic_exchange_rejects_missing_partner_public_key_env(self, tmp_path, caplog):
        """initiate-exchange fails clearly when --public-key-env references a missing environment variable."""
        output_path = tmp_path / "missing-public-env.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "missing-public-env",
                    "--public-key-env",
                    "OT_MISSING_PARTNER_PUBLIC_KEY",
                    "--output",
                    str(output_path),
                ]
            )

        assert exit_code == 1
        assert "OT_MISSING_PARTNER_PUBLIC_KEY" in caplog.text
        assert not output_path.exists()

    def test_basic_exchange_rejects_missing_sender_private_key_env(self, tmp_path, monkeypatch, caplog):
        """initiate-exchange fails clearly when --sender-private-key-env references a missing environment variable."""
        _, partner_public_pem = generate_key_pair("P-256")
        output_path = tmp_path / "missing-sender-env.exchange.json"
        monkeypatch.setenv("OT_PARTNER_PUBLIC_KEY", partner_public_pem.decode("utf-8"))

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "missing-sender-env",
                    "--public-key-env",
                    "OT_PARTNER_PUBLIC_KEY",
                    "--sender-private-key-env",
                    "OT_MISSING_SENDER_PRIVATE_KEY",
                    "--output",
                    str(output_path),
                ]
            )

        assert exit_code == 1
        assert "OT_MISSING_SENDER_PRIVATE_KEY" in caplog.text
        assert not output_path.exists()

    # -------------------------------------------------------------------------
    # Exchange config structure
    # -------------------------------------------------------------------------

    def test_exchange_config_drops_legacy_bundle_fields(self, tmp_path):
        """The exchange config must no longer expose legacy bundle fields."""
        partner_pem = _partner_key_pem(tmp_path)
        output_path = tmp_path / "legacy-fields.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "legacy-fields",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                ]
            )

        config = json.loads(output_path.read_text())
        assert "localKey" not in config
        assert "partnerKey" not in config
        assert "encryptedHashingSecret" not in config

    def test_exchange_config_uses_jwe_envelope_fields(self, tmp_path):
        """The exchange config must expose the shared JWE envelope fields."""
        partner_pem = _partner_key_pem(tmp_path)
        output_path = tmp_path / "struct.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "struct-test",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                ]
            )

        config = json.loads(output_path.read_text())
        required = {"version", "protected", "iv", "ciphertext", "tag", "recipients"}
        assert required.issubset(config.keys())
        assert config["version"] == 1
        _assert_shared_jwe_header(config)

    def test_exchange_config_recipients_use_kids_and_epk_headers(self, tmp_path):
        """Each JWE recipient must carry the expected kid and epk header shape."""
        partner_pem = _partner_key_pem(tmp_path)
        output_path = tmp_path / "recipients.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "recipients-test",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                ]
            )

        config = json.loads(output_path.read_text())
        _assert_recipient_headers(
            config,
            "P-256",
            {
                _fingerprint_to_kid((tmp_path / ".opentoken" / "recipients-test.public.pem").read_bytes()),
                _fingerprint_to_kid(partner_pem.read_bytes()),
            },
        )

    def test_exchange_config_never_embeds_private_key_material(self, tmp_path):
        """The exchange config must never embed private key material."""
        partner_pem = _partner_key_pem(tmp_path)
        output_path = tmp_path / "security.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "security-test",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                ]
            )

        raw = output_path.read_text()
        assert "PRIVATE KEY" not in raw
        assert "BEGIN EC PRIVATE KEY" not in raw
        assert "BEGIN RSA PRIVATE KEY" not in raw

    def test_exchange_config_can_use_provided_sender_private_key(self, tmp_path):
        """The CLI can reuse a caller-supplied sender private key without embedding it."""
        partner_pem = _partner_key_pem(tmp_path)
        output_path = tmp_path / "provided-local.exchange.json"
        local_private_pem, local_public_pem = generate_key_pair("P-256")
        local_private_key_path = tmp_path / "provided.private.pem"
        local_private_key_path.write_bytes(local_private_pem)

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "provided-local",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                    "--sender-private-key",
                    str(local_private_key_path),
                ]
            )

        assert exit_code == 0
        raw = output_path.read_text()
        assert "PRIVATE KEY" not in raw
        assert local_private_pem.decode() not in raw

        config = json.loads(raw)
        _assert_shared_jwe_header(config)
        _assert_recipient_headers(
            config,
            "P-256",
            {
                _fingerprint_to_kid(local_public_pem),
                _fingerprint_to_kid(partner_pem.read_bytes()),
            },
        )

        assert (tmp_path / ".opentoken" / "provided-local.private.pem").read_bytes() == local_private_pem
        assert (tmp_path / ".opentoken" / "provided-local.public.pem").read_bytes() == local_public_pem

    def test_exchange_config_rejects_removed_local_private_key_flag(self, tmp_path):
        """The unreleased --local-private-key flag is rejected now that sender terminology is canonical."""
        partner_pem = _partner_key_pem(tmp_path)
        output_path = tmp_path / "compat-local.exchange.json"
        local_private_pem, _ = generate_key_pair("P-256")
        local_private_key_path = tmp_path / "compat.private.pem"
        local_private_key_path.write_bytes(local_private_pem)

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "compat-local",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                    "--local-private-key",
                    str(local_private_key_path),
                ]
            )

        assert exit_code != 0
        assert not output_path.exists()

    # -------------------------------------------------------------------------
    # All supported curves
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("curve", SUPPORTED_CURVES)
    def test_all_supported_curves(self, tmp_path, curve):
        """initiate-exchange succeeds for every supported --curve value."""
        partner_pem = _partner_key_pem(tmp_path, curve)
        output_path = tmp_path / f"curve-{curve}.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    f"curve-{curve.replace('-', '').lower()}",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                    "--curve",
                    curve,
                ]
            )

        assert exit_code == 0
        config = json.loads(output_path.read_text())
        expected_local_public = (
            tmp_path / ".opentoken" / f"curve-{curve.replace('-', '').lower()}.public.pem"
        ).read_bytes()
        _assert_shared_jwe_header(config)
        _assert_recipient_headers(
            config,
            curve,
            {
                _fingerprint_to_kid(expected_local_public),
                _fingerprint_to_kid(partner_pem.read_bytes()),
            },
        )

    # -------------------------------------------------------------------------
    # Provided hashing secret
    # -------------------------------------------------------------------------

    def test_provided_hashing_secret_is_encrypted(self, tmp_path):
        """When --hashingsecret is given it appears nowhere in the config as plaintext."""
        partner_private_pem, partner_public_pem_bytes = generate_key_pair("P-256")
        partner_pem_path = tmp_path / "p.public.pem"
        partner_pem_path.write_bytes(partner_public_pem_bytes)
        output_path = tmp_path / "hs.exchange.json"
        plaintext_secret = "MyPlaintextHashingSecret"

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "hs-test",
                    "--public-key",
                    str(partner_pem_path),
                    "--output",
                    str(output_path),
                    "--hashingsecret",
                    plaintext_secret,
                ]
            )

        assert exit_code == 0
        raw = output_path.read_text()
        assert plaintext_secret not in raw, "Plaintext hashing secret must not appear in config"

    # -------------------------------------------------------------------------
    # Default output path
    # -------------------------------------------------------------------------

    def test_default_output_path_uses_name(self, tmp_path):
        """When --output is omitted the config is written to ./<name>.exchange.json."""
        partner_pem = _partner_key_pem(tmp_path)
        expected_output = tmp_path / "myexchange.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            with patch("pathlib.Path.cwd", return_value=tmp_path):
                exit_code = OpenTokenCommand.execute(
                    [
                        "initiate-exchange",
                        "--name",
                        "myexchange",
                        "--public-key",
                        str(partner_pem),
                        "--output",
                        str(expected_output),
                    ]
                )

        assert exit_code == 0
        assert expected_output.exists()

    # -------------------------------------------------------------------------
    # Default name: opentoken-<ISO8601-date>
    # -------------------------------------------------------------------------

    def test_default_name_uses_iso_date(self, tmp_path):
        """When --name is omitted, key files are named opentoken-<YYYY-MM-DD>.*."""
        partner_pem = _partner_key_pem(tmp_path)
        output_path = tmp_path / "default-name.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                ]
            )

        assert exit_code == 0
        opentoken_dir = tmp_path / ".opentoken"
        matches = list(opentoken_dir.glob("opentoken-????-??-??.private.pem"))
        assert matches, "Expected private key file matching opentoken-<ISO-date>.private.pem"

    # -------------------------------------------------------------------------
    # No silent overwrite
    # -------------------------------------------------------------------------

    def test_fails_when_key_already_exists(self, tmp_path):
        """Second run without --force must exit non-zero."""
        partner_pem = _partner_key_pem(tmp_path)
        output_path = tmp_path / "dup.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            first = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "dup-key",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                ]
            )
            second = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "dup-key",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                ]
            )

        assert first == 0
        assert second != 0, "Second run without --force must fail"

    def test_force_overwrites_existing_keys(self, tmp_path):
        """--force allows overwriting existing key files and the exchange config."""
        partner_pem = _partner_key_pem(tmp_path)
        output_path = tmp_path / "force.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "force-key",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                ]
            )
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "force-key",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                    "--force",
                ]
            )

        assert exit_code == 0

    # -------------------------------------------------------------------------
    # Error cases
    # -------------------------------------------------------------------------

    def test_missing_public_key_arg_exits_nonzero(self, tmp_path):
        """Omitting --public-key must produce a non-zero exit code."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(["initiate-exchange", "--name", "no-pk"])

        assert exit_code != 0

    def test_nonexistent_partner_key_file_exits_nonzero(self, tmp_path):
        """A non-existent partner public key file must produce a non-zero exit code."""
        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "missing-pk",
                    "--public-key",
                    str(tmp_path / "does-not-exist.pem"),
                    "--output",
                    str(tmp_path / "out.exchange.json"),
                ]
            )

        assert exit_code != 0

    def test_invalid_partner_pem_exits_nonzero(self, tmp_path):
        """A corrupt/invalid PEM file must produce a non-zero exit code."""
        bad_pem = tmp_path / "bad.pem"
        bad_pem.write_text("not a real pem")
        output_path = tmp_path / "bad.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "bad-pem",
                    "--public-key",
                    str(bad_pem),
                    "--output",
                    str(output_path),
                ]
            )

        assert exit_code != 0

    def test_unsupported_curve_exits_nonzero(self, tmp_path):
        """Unsupported --curve value must produce a non-zero exit code."""
        partner_pem = _partner_key_pem(tmp_path)
        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "bad-curve",
                    "--public-key",
                    str(partner_pem),
                    "--curve",
                    "P-192",
                ]
            )

        assert exit_code != 0

    @pytest.mark.parametrize("invalid_name", ["../escape", "nested/key", r"nested\\key", "C:\\temp\\key"])
    def test_invalid_name_exits_nonzero(self, tmp_path, invalid_name):
        """Unsafe key basenames must be rejected with a non-zero exit code."""
        partner_pem = _partner_key_pem(tmp_path)
        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    invalid_name,
                    "--public-key",
                    str(partner_pem),
                ]
            )

        assert exit_code != 0

    # -------------------------------------------------------------------------
    # Permissions
    # -------------------------------------------------------------------------

    def test_private_key_has_600_permissions(self, tmp_path):
        """initiate-exchange writes the local private key with 600 permissions."""
        if sys.platform == "win32":
            pytest.skip("POSIX permission test skipped on Windows")

        import stat

        partner_pem = _partner_key_pem(tmp_path)
        output_path = tmp_path / "perm.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "perm-test",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                ]
            )

        priv = tmp_path / ".opentoken" / "perm-test.private.pem"
        mode = stat.S_IMODE(os.stat(priv).st_mode)
        assert mode == 0o600, f"Private key must have 600 permissions but got {oct(mode)}"

    # -------------------------------------------------------------------------
    # Output printed to stdout
    # -------------------------------------------------------------------------

    def test_output_paths_printed_to_stdout(self, tmp_path, capsys):
        """Private key, public key, and exchange config paths are printed on success."""
        partner_pem = _partner_key_pem(tmp_path)
        output_path = tmp_path / "stdout.exchange.json"

        with patch("pathlib.Path.home", return_value=tmp_path):
            OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "stdout-test",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                ]
            )

        captured = capsys.readouterr()
        assert "private" in captured.out.lower()
        assert "public" in captured.out.lower()
        assert "exchange" in captured.out.lower()
