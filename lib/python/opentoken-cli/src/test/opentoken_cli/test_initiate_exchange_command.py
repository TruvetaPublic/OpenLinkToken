"""
Copyright (c) Truveta. All rights reserved.

Unit and integration tests for InitiateExchangeCommand.
"""

import base64
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from opentoken_cli.commands.initiate_exchange_command import (
    EXCHANGE_CONFIG_VERSION,
    InitiateExchangeCommand,
)
from opentoken_cli.commands.open_token_command import OpenTokenCommand
from opentoken_cli.util.ec_key_utils import SUPPORTED_CURVES, generate_key_pair, public_key_fingerprint

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _partner_key_pem(tmp_path: Path, curve: str = "P-256") -> Path:
    """Write a fresh partner public-key PEM file and return its path."""
    _, public_pem = generate_key_pair(curve)
    pem_path = tmp_path / "partner.public.pem"
    pem_path.write_bytes(public_pem)
    return pem_path


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

    # -------------------------------------------------------------------------
    # _encrypt_hashing_secret
    # -------------------------------------------------------------------------

    @pytest.mark.parametrize("curve", SUPPORTED_CURVES)
    def test_encrypt_produces_base64_nonce_and_ciphertext(self, curve):
        """_encrypt_hashing_secret returns valid base64 nonce and ciphertext."""
        private_pem, partner_public_pem = generate_key_pair(curve)
        payload = InitiateExchangeCommand._encrypt_hashing_secret(private_pem, partner_public_pem, b"test-secret")
        assert "nonce" in payload
        assert "ciphertext" in payload
        # Must be valid base64
        nonce_bytes = base64.b64decode(payload["nonce"])
        ct_bytes = base64.b64decode(payload["ciphertext"])
        assert len(nonce_bytes) == 12, "AES-GCM nonce must be 12 bytes"
        assert len(ct_bytes) > 0

    def test_encrypt_different_nonce_each_call(self):
        """Each encryption call must use a fresh nonce."""
        private_pem, partner_public_pem = generate_key_pair("P-256")
        p1 = InitiateExchangeCommand._encrypt_hashing_secret(private_pem, partner_public_pem, b"s")
        p2 = InitiateExchangeCommand._encrypt_hashing_secret(private_pem, partner_public_pem, b"s")
        assert p1["nonce"] != p2["nonce"], "Each encryption call must use a unique nonce"

    def test_encrypt_rejects_invalid_partner_pem(self):
        """Invalid partner PEM raises ValueError."""
        private_pem, _ = generate_key_pair("P-256")
        with pytest.raises(ValueError, match="Failed to load partner public key"):
            InitiateExchangeCommand._encrypt_hashing_secret(private_pem, b"not-a-pem", b"secret")

    def test_decrypt_round_trip(self):
        """The encrypted hashing secret can be recovered by the partner's private key."""
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric.ec import ECDH
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

        from opentoken_cli.util.ec_key_utils import HKDF_INFO

        # Sender: local private key, partner key pair
        sender_private_pem, sender_public_pem = generate_key_pair("P-256")
        partner_private_pem, partner_public_pem = generate_key_pair("P-256")

        plaintext = b"supersecret-hashing-key"
        payload = InitiateExchangeCommand._encrypt_hashing_secret(sender_private_pem, partner_public_pem, plaintext)

        # Partner decrypts using their own private key + sender's public key
        partner_private_key = load_pem_private_key(partner_private_pem, password=None)
        sender_public_key = load_pem_public_key(sender_public_pem)
        shared_secret = partner_private_key.exchange(ECDH(), sender_public_key)

        hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=HKDF_INFO)
        aes_key = hkdf.derive(shared_secret)

        nonce = base64.b64decode(payload["nonce"])
        ciphertext = base64.b64decode(payload["ciphertext"])
        recovered = AESGCM(aes_key).decrypt(nonce, ciphertext, None)

        assert recovered == plaintext

    # -------------------------------------------------------------------------
    # _build_config
    # -------------------------------------------------------------------------

    def test_build_config_contains_required_keys(self):
        """_build_config produces a dict with all required top-level keys."""
        _, local_public_pem = generate_key_pair("P-256")
        _, partner_public_pem = generate_key_pair("P-256")
        config = InitiateExchangeCommand._build_config(
            name="test",
            curve="P-256",
            local_public_pem=local_public_pem,
            partner_public_pem=partner_public_pem,
            partner_fingerprint="AA:BB:CC",
            encrypted_payload={"nonce": "abc", "ciphertext": "def"},
        )

        required_keys = {
            "version",
            "exchangeName",
            "keyAgreement",
            "curve",
            "localKey",
            "partnerKey",
            "kdf",
            "encryption",
            "encryptedHashingSecret",
        }
        assert required_keys.issubset(config.keys())

    def test_build_config_can_omit_private_key_when_internal_callers_pass_none(self):
        """_build_config still omits private key material when internal callers explicitly pass none."""
        _, local_public_pem = generate_key_pair("P-256")
        _, partner_public_pem = generate_key_pair("P-256")
        config = InitiateExchangeCommand._build_config(
            name="test",
            curve="P-256",
            local_public_pem=local_public_pem,
            partner_public_pem=partner_public_pem,
            partner_fingerprint="AA:BB:CC",
            encrypted_payload={"nonce": "abc", "ciphertext": "def"},
        )

        assert "privateKey" not in config["localKey"]
        assert "privateKeyFingerprint" not in config["localKey"]

    def test_build_config_version(self):
        """Config version matches EXCHANGE_CONFIG_VERSION."""
        _, local_public_pem = generate_key_pair("P-256")
        _, partner_public_pem = generate_key_pair("P-256")
        config = InitiateExchangeCommand._build_config(
            name="v",
            curve="P-256",
            local_public_pem=local_public_pem,
            partner_public_pem=partner_public_pem,
            partner_fingerprint="FP",
            encrypted_payload={"nonce": "n", "ciphertext": "c"},
        )
        assert config["version"] == EXCHANGE_CONFIG_VERSION

    def test_build_config_never_contains_private_key(self):
        """Config must not contain any private key material."""
        private_pem, local_public_pem = generate_key_pair("P-256")
        _, partner_public_pem = generate_key_pair("P-256")
        config_str = json.dumps(
            InitiateExchangeCommand._build_config(
                name="check",
                curve="P-256",
                local_public_pem=local_public_pem,
                partner_public_pem=partner_public_pem,
                partner_fingerprint="FP",
                encrypted_payload={"nonce": "n", "ciphertext": "c"},
            )
        )
        assert "PRIVATE KEY" not in config_str, "Config must never contain private key material"

    def test_build_config_local_public_key_is_pem(self):
        """The local_key.public_key field must contain a PEM-encoded public key."""
        _, local_public_pem = generate_key_pair("P-256")
        _, partner_public_pem = generate_key_pair("P-256")
        config = InitiateExchangeCommand._build_config(
            name="k",
            curve="P-256",
            local_public_pem=local_public_pem,
            partner_public_pem=partner_public_pem,
            partner_fingerprint="FP",
            encrypted_payload={"nonce": "n", "ciphertext": "c"},
        )
        assert "-----BEGIN PUBLIC KEY-----" in config["localKey"]["publicKey"]

    def test_build_config_local_key_contains_public_key_fingerprint(self):
        """The localKey object carries the local public key fingerprint."""
        _, local_public_pem = generate_key_pair("P-256")
        _, partner_public_pem = generate_key_pair("P-256")
        config = InitiateExchangeCommand._build_config(
            name="k",
            curve="P-256",
            local_public_pem=local_public_pem,
            partner_public_pem=partner_public_pem,
            partner_fingerprint="FP",
            encrypted_payload={"nonce": "n", "ciphertext": "c"},
        )

        assert config["localKey"]["publicKeyFingerprint"] == public_key_fingerprint(local_public_pem)

    def test_build_config_partner_public_key_is_pem(self):
        """The partnerKey.publicKey field must contain a PEM-encoded public key."""
        _, local_public_pem = generate_key_pair("P-256")
        _, partner_public_pem = generate_key_pair("P-256")
        config = InitiateExchangeCommand._build_config(
            name="k",
            curve="P-256",
            local_public_pem=local_public_pem,
            partner_public_pem=partner_public_pem,
            partner_fingerprint="FP",
            encrypted_payload={"nonce": "n", "ciphertext": "c"},
        )
        assert "-----BEGIN PUBLIC KEY-----" in config["partnerKey"]["publicKey"]

    def test_build_config_partner_key_contains_fingerprint(self):
        """The partnerKey object carries the partner public key fingerprint."""
        _, local_public_pem = generate_key_pair("P-256")
        _, partner_public_pem = generate_key_pair("P-256")
        config = InitiateExchangeCommand._build_config(
            name="k",
            curve="P-256",
            local_public_pem=local_public_pem,
            partner_public_pem=partner_public_pem,
            partner_fingerprint="FP",
            encrypted_payload={"nonce": "n", "ciphertext": "c"},
        )

        assert config["partnerKey"]["publicKeyFingerprint"] == "FP"

    def test_build_config_local_key_contains_basename(self):
        """The local_key object carries the bundle's basename alongside key material."""
        _, local_public_pem = generate_key_pair("P-256")
        _, partner_public_pem = generate_key_pair("P-256")
        config = InitiateExchangeCommand._build_config(
            name="bundle-name",
            curve="P-256",
            local_public_pem=local_public_pem,
            partner_public_pem=partner_public_pem,
            partner_fingerprint="FP",
            encrypted_payload={"nonce": "n", "ciphertext": "c"},
        )

        assert config["localKey"]["basename"] == "bundle-name"

    def test_build_config_includes_private_key_and_fingerprint_when_requested(self):
        """_build_config includes the local private key and fingerprint when explicitly requested."""
        local_private_pem, local_public_pem = generate_key_pair("P-256")
        _, partner_public_pem = generate_key_pair("P-256")
        config = InitiateExchangeCommand._build_config(
            name="k",
            curve="P-256",
            local_public_pem=local_public_pem,
            partner_public_pem=partner_public_pem,
            partner_fingerprint="FP",
            encrypted_payload={"nonce": "n", "ciphertext": "c"},
            local_private_pem=local_private_pem,
        )

        assert "-----BEGIN PRIVATE KEY-----" in config["localKey"]["privateKey"]
        assert config["localKey"]["privateKeyFingerprint"] == public_key_fingerprint(local_public_pem)

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

    # -------------------------------------------------------------------------
    # Exchange config structure
    # -------------------------------------------------------------------------

    def test_exchange_config_structure(self, tmp_path):
        """The exchange config JSON contains all required fields."""
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
        required = {
            "version",
            "exchangeName",
            "keyAgreement",
            "curve",
            "localKey",
            "partnerKey",
            "kdf",
            "encryption",
            "encryptedHashingSecret",
        }
        assert required.issubset(config.keys())
        assert config["version"] == EXCHANGE_CONFIG_VERSION
        assert config["curve"] == "P-256"
        assert config["keyAgreement"] == "ECDH"
        assert "-----BEGIN PUBLIC KEY-----" in config["localKey"]["publicKey"]

    def test_exchange_config_includes_private_key_by_default(self, tmp_path):
        """The exchange config includes private key material by default for self-contained bundles."""
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
        assert "PRIVATE KEY" in raw
        config = json.loads(raw)
        assert config["localKey"]["publicKeyFingerprint"]
        assert config["localKey"]["privateKeyFingerprint"]

    def test_exchange_config_can_use_provided_local_private_key(self, tmp_path):
        """The CLI can use and embed a caller-supplied local private key instead of generating one."""
        partner_pem = _partner_key_pem(tmp_path)
        output_path = tmp_path / "self-contained.exchange.json"
        local_private_pem, local_public_pem = generate_key_pair("P-256")
        local_private_key_path = tmp_path / "provided.private.pem"
        local_private_key_path.write_bytes(local_private_pem)

        with patch("pathlib.Path.home", return_value=tmp_path):
            exit_code = OpenTokenCommand.execute(
                [
                    "initiate-exchange",
                    "--name",
                    "self-contained",
                    "--public-key",
                    str(partner_pem),
                    "--output",
                    str(output_path),
                    "--local-private-key",
                    str(local_private_key_path),
                ]
            )

        assert exit_code == 0
        config = json.loads(output_path.read_text())
        assert config["localKey"]["privateKey"] == local_private_pem.decode()
        assert config["localKey"]["publicKey"] == local_public_pem.decode()
        assert config["localKey"]["publicKeyFingerprint"] == public_key_fingerprint(local_public_pem)
        assert config["localKey"]["privateKeyFingerprint"]
        assert (tmp_path / ".opentoken" / "self-contained.private.pem").read_bytes() == local_private_pem
        assert (tmp_path / ".opentoken" / "self-contained.public.pem").read_bytes() == local_public_pem

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
        assert config["curve"] == curve

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
