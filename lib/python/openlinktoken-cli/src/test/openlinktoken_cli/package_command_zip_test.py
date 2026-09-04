# SPDX-License-Identifier: MIT

import base64
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from openlinktoken.core.ai.tokens.ml1_inference_config import ML1InferenceConfig
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

    def test_package_does_not_accept_rotation_iv_override(self):
        """Package must use the rotation IV from the exchange config."""
        parser = OpenLinkTokenCommand.create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["package", "-i", "input.csv", "--rotation-iv", "cli-iv"])

    def test_tokenize_does_not_accept_rotation_iv_override(self):
        """Tokenize must use the rotation IV from the exchange config."""
        parser = OpenLinkTokenCommand.create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(["tokenize", "-i", "input.csv", "--rotation-iv", "cli-iv"])

    def test_package_uses_inferencing_option_names(self):
        """Package exposes the same inferencing option names as tokenize."""
        parser = OpenLinkTokenCommand.create_parser()

        args = parser.parse_args(
            [
                "package",
                "-i",
                "input.csv",
                "--disable-inferencing",
                "--inferencing-batch-size",
                "32",
                "--inferencing-num-threads",
                "2",
            ]
        )

        assert args.disable_inferencing is True
        assert args.inferencing_batch_size == 32
        assert args.inferencing_num_threads == 2

        for option in ("--disable-ml1", "--ml1-batch-size", "--ml1-num-threads"):
            option_args = ["package", "-i", "input.csv", option]
            if option != "--disable-ml1":
                option_args.append("2")
            with pytest.raises(SystemExit):
                parser.parse_args(option_args)

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

        with patch.object(ML1InferenceConfig, "configure", wraps=ML1InferenceConfig.configure) as configure:
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
                    "--disable-inferencing",
                ]
            )

        assert exit_code == 0
        assert zip_path.exists()
        assert configure.call_args.kwargs["configured_model_path"] == ML1InferenceConfig.DEFAULT_MODEL_PATH
        assert configure.call_args.kwargs["configured_tokenizer_path"] == ML1InferenceConfig.DEFAULT_TOKENIZER_PATH
        assert (
            configure.call_args.kwargs["configured_max_sequence_length"]
            == ML1InferenceConfig.DEFAULT_MAX_SEQUENCE_LENGTH
        )
        assert configure.call_args.kwargs["configured_num_threads"] == ML1InferenceConfig.DEFAULT_NUM_THREADS

    def test_custom_tokenization_disables_ml1_and_omits_custom_ml1_rule(self, temp_dir: Path):
        """Custom tokenization must not produce built-in or explicitly configured ML1 output."""
        exchange_config, private_key = self._create_exchange_config(temp_dir, "custom-tokenization")
        config_path = temp_dir / "tokenization-config.yaml"
        config_path.write_text(
            """
column_mappings:
  RecordId:
    column_name: "RecordId"
    type: RecordId
  FirstName:
    column_name: "FirstName"
    type: FirstName
token_rules:
  T1:
    - field: FirstName
      expression: "T|U"
  ML1:
    - field: FirstName
      expression: "T|U"
""".strip(),
            encoding="utf-8",
        )
        zip_path = temp_dir / "custom-output.zip"
        previous_enabled = ML1InferenceConfig.is_enabled()

        try:
            with patch.object(ML1InferenceConfig, "configure", wraps=ML1InferenceConfig.configure) as configure:
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
                        "--config",
                        str(config_path),
                    ]
                )

            assert exit_code == 0
            assert configure.call_args.kwargs["enable_ml1"] is False

            with zipfile.ZipFile(zip_path) as zf:
                table = pq.read_table(pa.BufferReader(zf.read("custom-output.parquet")))
            assert all(row["RuleId"] != "ML1" for row in table.to_pylist())
        finally:
            ML1InferenceConfig.configure(
                enable_ml1=previous_enabled,
                configured_model_path=ML1InferenceConfig.DEFAULT_MODEL_PATH,
                configured_tokenizer_path=ML1InferenceConfig.DEFAULT_TOKENIZER_PATH,
                configured_max_sequence_length=ML1InferenceConfig.DEFAULT_MAX_SEQUENCE_LENGTH,
                configured_batch_size=ML1InferenceConfig.DEFAULT_BATCH_SIZE,
                configured_num_threads=ML1InferenceConfig.DEFAULT_NUM_THREADS,
            )

    def test_zip_contains_parquet_and_metadata(self, temp_dir: Path):
        """The ZIP must contain a Parquet token file and a metadata JSON file."""
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
                "--disable-inferencing",
            ]
        )

        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()

        assert "output.parquet" in names
        assert "output.metadata.json" in names

    def test_embedded_parquet_has_token_rows(self, temp_dir: Path):
        """The Parquet inside the ZIP must contain token rows for the two input records."""
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
                "--disable-inferencing",
            ]
        )

        with zipfile.ZipFile(zip_path) as zf:
            table = pq.read_table(pa.BufferReader(zf.read("output.parquet")))

        rows = table.to_pylist()
        assert len(rows) > 0, "Expected at least one token row in the embedded Parquet file"
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
                "--disable-inferencing",
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
                "--disable-inferencing",
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
                "--disable-inferencing",
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

        TokenizeCommand._configure_rotation(exchange)

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
                "--disable-inferencing",
            ]
        )

        assert exit_code != 0
