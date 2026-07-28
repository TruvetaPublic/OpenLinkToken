# SPDX-License-Identifier: MIT

import base64
import csv as csv_module
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from openlinktoken.core.ai.tokens.rotation_config import RotationConfig
from openlinktoken_cli.commands.open_link_token_command import OpenLinkTokenCommand
from openlinktoken_cli.commands.package_command import PackageCommand
from openlinktoken_cli.commands.tokenize_command import TokenizeCommand
from openlinktoken_cli.processor.person_attributes_processor import (
    PersonAttributesProcessingSummary,
)
from openlinktoken_cli.util.ec_key_utils import generate_key_pair

HASHING_SECRET = "TestHashingSecret"

EXPECTED_METADATA_KEYS = {
    "PythonVersion",
    "Platform",
    "Version",
    "TotalRows",
    "TotalRowsWithInvalidAttributes",
    "InvalidAttributesByType",
    "BlankTokensByRule",
}


class TestPackageCommandZipOutput:
    """Integration tests for ``olt package -o output.zip``."""

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        """Create a temporary directory with a two-row CSV input."""
        input_csv = tmp_path / "input.csv"
        input_csv.write_text(
            "RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber\n"
            "rec-001,John,Doe,98004,Male,2000-01-15,123-45-6789\n"
            "rec-002,Jane,Smith,12345,Female,1990-05-20,234-56-7890\n"
        )
        return tmp_path

    def _create_exchange_config(self, temp_dir: Path, name: str = "pkg-zip") -> tuple[Path, Path]:
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
                    HASHING_SECRET,
                ]
            )

        assert exit_code == 0
        return exchange_config_path, temp_dir / ".openlinktoken" / f"{name}.private.pem"

    # ------------------------------------------------------------------
    # Success cases
    # ------------------------------------------------------------------

    def test_package_creates_zip_file(self, temp_dir: Path):
        """package command with a .zip output path must create a ZIP file."""
        exchange_config, private_key = self._create_exchange_config(temp_dir)
        zip_path = temp_dir / "output.zip"

        exit_code = OpenLinkTokenCommand.execute(
            [
                "package",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(zip_path),
                "--exchange-config",
                str(exchange_config),
                "--private-key",
                str(private_key),
                "--disable-ml1",
            ]
        )

        assert exit_code == 0
        assert zip_path.exists()

    def test_zip_contains_csv_and_metadata(self, temp_dir: Path):
        """The ZIP must contain a CSV token file and a metadata JSON file."""
        exchange_config, private_key = self._create_exchange_config(temp_dir)
        zip_path = temp_dir / "output.zip"

        OpenLinkTokenCommand.execute(
            [
                "package",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(zip_path),
                "--exchange-config",
                str(exchange_config),
                "--private-key",
                str(private_key),
                "--disable-ml1",
            ]
        )

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()

        assert "output.csv" in names
        assert "output.metadata.json" in names

    def test_embedded_csv_has_token_rows(self, temp_dir: Path):
        """The CSV inside the ZIP must contain token rows for the two input records."""
        exchange_config, private_key = self._create_exchange_config(temp_dir)
        zip_path = temp_dir / "output.zip"

        OpenLinkTokenCommand.execute(
            [
                "package",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(zip_path),
                "--exchange-config",
                str(exchange_config),
                "--private-key",
                str(private_key),
                "--disable-ml1",
            ]
        )

        with zipfile.ZipFile(zip_path) as zf:
            csv_text = zf.read("output.csv").decode("utf-8")

        rows = list(csv_module.DictReader(csv_text.splitlines()))
        assert len(rows) > 0, "Expected at least one token row in the embedded CSV"
        record_ids = {row["RecordId"] for row in rows}
        assert "rec-001" in record_ids
        assert "rec-002" in record_ids

    def test_embedded_metadata_has_expected_keys(self, temp_dir: Path):
        """The metadata JSON inside the ZIP must contain all standard metadata keys."""
        exchange_config, private_key = self._create_exchange_config(temp_dir)
        zip_path = temp_dir / "output.zip"

        OpenLinkTokenCommand.execute(
            [
                "package",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(zip_path),
                "--exchange-config",
                str(exchange_config),
                "--private-key",
                str(private_key),
                "--disable-ml1",
            ]
        )

        with zipfile.ZipFile(zip_path) as zf:
            metadata = json.loads(zf.read("output.metadata.json").decode("utf-8"))

        assert set(metadata) == EXPECTED_METADATA_KEYS

    def test_no_sibling_metadata_file_written(self, temp_dir: Path):
        """When output is a ZIP, no sibling .metadata.json should be written alongside it."""
        exchange_config, private_key = self._create_exchange_config(temp_dir)
        zip_path = temp_dir / "output.zip"

        OpenLinkTokenCommand.execute(
            [
                "package",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(zip_path),
                "--exchange-config",
                str(exchange_config),
                "--private-key",
                str(private_key),
                "--disable-ml1",
            ]
        )

        sibling_metadata = temp_dir / "output.metadata.json"
        assert not sibling_metadata.exists(), "Metadata must be embedded inside the ZIP, not written as a sibling file"

    def test_embedded_metadata_row_count(self, temp_dir: Path):
        """TotalRows in the embedded metadata must match the input row count."""
        exchange_config, private_key = self._create_exchange_config(temp_dir)
        zip_path = temp_dir / "output.zip"

        OpenLinkTokenCommand.execute(
            [
                "package",
                "-i",
                str(temp_dir / "input.csv"),
                "-o",
                str(zip_path),
                "--exchange-config",
                str(exchange_config),
                "--private-key",
                str(private_key),
                "--disable-ml1",
            ]
        )

        with zipfile.ZipFile(zip_path) as zf:
            metadata = json.loads(zf.read("output.metadata.json").decode("utf-8"))

        assert metadata["TotalRows"] == 2

    @pytest.mark.parametrize(
        ("rotation_iv", "expected_iv"),
        [
            (b"artifact-iv", "artifact-iv"),
            (b"t\xecst-rotation-iv", base64.b64encode(b"t\xecst-rotation-iv").decode("ascii")),
        ],
    )
    def test_package_applies_exchange_rotation_configuration(
        self, temp_dir: Path, rotation_iv: bytes, expected_iv: str
    ):
        """Package must configure ML1 rotation exactly as tokenize does before processing."""
        exchange = SimpleNamespace(
            path=temp_dir / "test.exchange.json",
            hashing_secret=b"hashing-secret",
            rotation_iv=rotation_iv,
            rotation_count=2,
            bin_width=0.25,
            dimension_bias=[0.1, 0.2, 0.3],
        )
        summary = PersonAttributesProcessingSummary(0, 0, {}, {})
        RotationConfig.configure(enable=True, rotation_iv="default-iv")

        with (
            patch(
                "openlinktoken_cli.commands.package_command.resolve_exchange_config",
                return_value=exchange,
            ),
            patch(
                "openlinktoken_cli.commands.package_command.derive_transport_encryption_key",
                return_value=b"encryption-key",
            ),
            patch.object(
                PackageCommand,
                "_process_tokens",
                return_value=(summary, str(temp_dir / "output.metadata.json")),
            ),
        ):
            exit_code = OpenLinkTokenCommand.execute(
                [
                    "package",
                    "-i",
                    str(temp_dir / "input.csv"),
                    "-o",
                    str(temp_dir / "output.csv"),
                    "--exchange-config",
                    str(exchange.path),
                    "--private-key",
                    str(temp_dir / "test.private.pem"),
                    "--ring-id",
                    "test-ring",
                    "--no-progress",
                ]
            )

        assert exit_code == 0
        assert RotationConfig.get_rotation_iv() == expected_iv
        assert RotationConfig.get_rotation_count() == 2
        assert RotationConfig.get_bin_width() == 0.25
        assert RotationConfig.get_dimension_bias() == [0.1, 0.2, 0.3]

    @pytest.mark.parametrize(
        ("rotation_iv", "expected_iv"),
        [
            (b"tokenize-iv", "tokenize-iv"),
            (b"t\xecst-rotation-iv", base64.b64encode(b"t\xecst-rotation-iv").decode("ascii")),
        ],
    )
    def test_tokenize_applies_exchange_rotation_iv_encoding(self, rotation_iv: bytes, expected_iv: str):
        """Tokenize must use the same IV conversion as package."""
        exchange = SimpleNamespace(
            rotation_iv=rotation_iv,
            rotation_count=2,
            bin_width=0.25,
            dimension_bias=[0.1, 0.2, 0.3],
        )

        TokenizeCommand._configure_rotation(exchange, None)

        assert RotationConfig.get_rotation_iv() == expected_iv

    # ------------------------------------------------------------------
    # Error cases
    # ------------------------------------------------------------------

    def test_unsupported_input_type_rejected(self, temp_dir: Path):
        """An unsupported input extension must cause a non-zero exit code."""
        exchange_config, private_key = self._create_exchange_config(temp_dir)
        bad_input = temp_dir / "input.json"
        bad_input.write_text("{}")

        exit_code = OpenLinkTokenCommand.execute(
            [
                "package",
                "-i",
                str(bad_input),
                "-o",
                str(temp_dir / "output.zip"),
                "--exchange-config",
                str(exchange_config),
                "--private-key",
                str(private_key),
                "--disable-ml1",
            ]
        )

        assert exit_code != 0
