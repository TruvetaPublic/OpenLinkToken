# SPDX-License-Identifier: MIT

import contextlib
import logging
import sys
import tempfile
from pathlib import Path
from typing import List

from openlinktoken.metadata import Metadata
from openlinktoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer
from openlinktoken_cli.commands.tokenization_config_helper import TokenizationConfigHelper
from openlinktoken_cli.io.csv.person_attributes_csv_writer import PersonAttributesCSVWriter
from openlinktoken_cli.io.json.metadata_json_writer import MetadataJsonWriter
from openlinktoken_cli.io.parquet.person_attributes_parquet_writer import PersonAttributesParquetWriter
from openlinktoken_cli.processor.person_attributes_processor import (
    PersonAttributesProcessingSummary,
    PersonAttributesProcessor,
)
from openlinktoken_cli.util.cli_error_reporter import archive_cli_error, format_error_reference_message
from openlinktoken_cli.util.cli_run_reporter import CliRunReporter
from openlinktoken_cli.util.exchange_config import derive_transport_encryption_key, resolve_exchange_config
from openlinktoken_cli.util.file_type_detector import FileTypeDetector
from openlinktoken_cli.util.path_utils import get_auto_output_path
from openlinktoken_cli.util.ring_id_utils import resolve_ring_id
from openlinktoken_cli.util.zip_utils import bundle_into_zip

logger = logging.getLogger(__name__)


class PackageCommand:
    """
    Package command - combines tokenize and encrypt in one command.
    This is the default workflow: hash + encrypt.
    """

    @staticmethod
    def register_subcommand(subparsers):
        """Register the package subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "package",
            help="Generate and encrypt tokens in one step using the exchange config",
            description="Generate and encrypt tokens in one step using the exchange config",
            add_help=False,
        )

        # Manually add --help (without -h short form)
        parser.add_argument(
            "--help",
            action="help",
            help="Show this help message and exit",
        )

        parser.add_argument(
            "-i",
            "--input",
            required=True,
            dest="input_path",
            help="Input file path",
        )

        parser.add_argument(
            "-o",
            "--output",
            required=False,
            dest="output_path",
            help="Output file path (defaults to input filename with '_packaged' and .zip suffix)",
        )

        parser.add_argument(
            "--exchange-config",
            required=False,
            dest="exchange_config",
            metavar="PATH",
            help="Path to the exchange config JSON (default: ./openlinktoken-YYYY-MM-DD.exchange.json)",
        )

        parser.add_argument(
            "--config",
            required=False,
            dest="tokenization_config",
            metavar="PATH",
            help=(
                "Path to a YAML tokenization config that defines input field mappings and token rules. "
                "Supported for CSV and Parquet input."
            ),
        )

        private_key_group = parser.add_mutually_exclusive_group(required=False)
        private_key_group.add_argument(
            "--private-key",
            dest="private_key",
            metavar="PATH",
            help="Path to the private key PEM used to decrypt the exchange config and derive the transport key",
        )
        private_key_group.add_argument(
            "--private-key-env",
            dest="private_key_env",
            metavar="ENV_VAR",
            help="Read the private key PEM from the named environment variable",
        )

        parser.add_argument(
            "--ring-id",
            dest="ring_id",
            default=None,
            help="Ring identifier for key management. Defaults to a random UUID if not provided",
        )

        parser.add_argument(
            "--hash-record-ids",
            action="store_true",
            default=False,
            dest="hash_record_ids",
            help=(
                "Hash input RecordId values using SHA-256 before writing to output. "
                "The hashed value (not the original) appears in the output file. "
                "This is a one-way operation with no traceability."
            ),
        )

         # --no-progress / -q: suppress interactive progress indicator
        parser.add_argument(
              "--no-progress",
              "-q",
            action="store_true",
            default=False,
            dest="no_progress",
            help="Suppress interactive progress indicator (e.g. for non-interactive / CI environments)",
            )

        parser.set_defaults(func=PackageCommand.execute)

    @staticmethod
    def execute(args):
        """Execute the package command."""
        input_type = FileTypeDetector.detect_input_type(args.input_path)
        if not input_type:
            logger.error("Unable to auto-detect input type. Supported input formats: csv, parquet")
            return 1

        # Resolve output path if not provided
        output_path = args.output_path if args.output_path else get_auto_output_path(args.input_path, "package")

        output_type = FileTypeDetector.detect_output_type(output_path)
        if not output_type:
            logger.error("Unable to auto-detect output type from provided/generated path.")
            return 1
        ring_id = resolve_ring_id(args.ring_id)
        hash_record_ids = getattr(args, "hash_record_ids", False)
        tokenization_config_path = getattr(args, "tokenization_config", None)
        reporter = CliRunReporter("package", no_progress=args.no_progress)

        try:
            with reporter:
                try:
                    logger.info("Running package command (tokenize + encrypt)")
                    logger.info(f"Input: {args.input_path} ({input_type})")
                    logger.info(f"Output: {output_path} ({output_type})")
                    logger.info(f"Ring ID: {ring_id}")
                    if hash_record_ids:
                        logger.info("Record ID hashing enabled: RecordIds will be SHA-256 hashed in output")

                    reporter.update_status("Resolving exchange config")
                    exchange = resolve_exchange_config(
                        args.exchange_config,
                        private_key_path=args.private_key,
                        private_key_env=args.private_key_env,
                    )
                    encryption_key = derive_transport_encryption_key(exchange)
                    logger.info(f"Exchange config: {exchange.path}")

                    reporter.update_status("Packaging records")
                    # Determine total rows via reader to enable %/ETA
                    total_rows: int | None = None
                    try:
                        reader = TokenizationConfigHelper.create_reader(
                            args.input_path, input_type)
                        total_rows = reader.row_count()
                        reader.close()
                    except Exception:
                        total_rows = None

                    # Wire total_rows to reporter if known
                    if total_rows is not None:
                        reporter.set_total_rows(total_rows)

                    is_zip = output_type == FileTypeDetector.TYPE_ZIP

                    if is_zip:
                        if not exchange.path:
                            raise ValueError(
                                "ZIP output requires an exchange config file path. "
                                "Ensure the exchange config was loaded from a file (exchange.path must not be None)."
                            )
                        logger.info("ZIP output: tokens, metadata, and exchange config will be bundled")

                    with contextlib.ExitStack() as stack:
                        if is_zip:
                            temp_dir = stack.enter_context(tempfile.TemporaryDirectory())
                            zip_path = Path(output_path)
                            token_output_path = str(
                                Path(temp_dir) / f"{zip_path.stem}.{FileTypeDetector.TYPE_PARQUET}",
                            )
                            token_output_type = FileTypeDetector.TYPE_PARQUET
                        else:
                            token_output_path = output_path
                            token_output_type = output_type

                        summary, metadata_path = PackageCommand._process_tokens(
                            args.input_path,
                            token_output_path,
                            input_type,
                            token_output_type,
                            exchange.hashing_secret,
                            encryption_key,
                            ring_id,
                            hash_record_ids,
                            tokenization_config_path,
                            progress_callback=reporter.make_progress_callback("Packaging records", "records"),
                        )

                        if is_zip:
                            bundle_into_zip(output_path, token_output_path, metadata_path, exchange.path)
                            metadata_path = None
                    logger.info("Token generation and encryption completed successfully")
                except Exception as error:
                    logger.error("Error during token processing: %s", error)
                    raise
            reporter.finish_success(
                "Package complete",
                PackageCommand._build_summary_lines(
                    output_path,
                    None if is_zip else metadata_path,
                    summary,
                    hash_record_ids,
                ),
            )
            return 0
        except Exception as error:
            report = archive_cli_error(error, command_name="package", existing_report=reporter.log_report)
            print(f"Error: {error}", file=sys.stderr)
            print(format_error_reference_message(report), file=sys.stderr)
            return 1

    @staticmethod
    def _process_tokens(
        input_path: str,
        output_path: str,
        input_type: str,
        output_type: str,
        hashing_secret: str | bytes,
        encryption_key: bytes,
        ring_id: str,
        hash_record_ids: bool = False,
        tokenization_config_path: str = None,
        progress_callback=None,
    ) -> tuple[PersonAttributesProcessingSummary, str]:
        """Process tokens from person attributes."""
        token_transformer_list: List[TokenTransformer] = []

        try:
            # Add both hash and encryption transformers
            token_transformer_list.append(HashTokenTransformer(hashing_secret))
            token_transformer_list.append(EncryptTokenTransformer(encryption_key))
        except Exception as e:
            raise RuntimeError("Failed to initialize transformers") from e

        try:
            config, factory, token_definition = TokenizationConfigHelper.load_tokenization_config(tokenization_config_path)
            with (
                TokenizationConfigHelper.create_reader(input_path, input_type, config, factory) as reader,
                PackageCommand._create_writer(output_path, output_type) as writer,
            ):
                # Create metadata
                metadata = Metadata()
                metadata_map = metadata.initialize()
                metadata.add_hashed_secret(Metadata.HASHING_SECRET_HASH, hashing_secret)
                metadata.add_hashed_secret(Metadata.ENCRYPTION_SECRET_HASH, encryption_key)

                # Process data with JWE wrapping support for v1 token format
                summary = PersonAttributesProcessor.process(
                    reader,
                    writer,
                    token_transformer_list,
                    metadata_map,
                    encryption_key,
                    ring_id,
                    hash_record_ids,
                    token_definition=token_definition,
                    progress_callback=progress_callback,
                )

                # Write metadata
                metadata_writer = MetadataJsonWriter(output_path)
                metadata_writer.write(metadata_map)
                return summary, metadata_writer.metadata_file_path

        except Exception:
            raise

    @staticmethod
    def _build_summary_lines(
        output_path: str,
        metadata_path: str | None,
        summary: PersonAttributesProcessingSummary,
        hash_record_ids: bool,
    ) -> list[str]:
        lines = [
            f"Output: {output_path}",
        ]
        if metadata_path:
            lines.append(f"Metadata: {metadata_path}")
        lines.extend(
            [
                f"Rows processed: {summary.total_rows:,}",
                f"Rows with invalid attributes: {summary.total_rows_with_invalid_attributes:,}",
            ]
        )
        lines.extend(
            CliRunReporter.summarize_count_lines("Top invalid attributes", summary.invalid_attributes_by_type, limit=3)
        )
        lines.extend(CliRunReporter.summarize_count_lines("Blank tokens by rule", summary.blank_tokens_by_rule))
        if hash_record_ids:
            lines.append("Record ID hashing: enabled")
        return lines

    @staticmethod
    def _create_writer(path: str, file_type: str):
        """Create a PersonAttributesWriter based on file type."""
        file_type_lower = file_type.lower()
        if file_type_lower == FileTypeDetector.TYPE_CSV:
            return PersonAttributesCSVWriter(path)
        elif file_type_lower == FileTypeDetector.TYPE_PARQUET:
            return PersonAttributesParquetWriter(path)
        else:
            raise ValueError(f"Unsupported output type: {file_type}")
