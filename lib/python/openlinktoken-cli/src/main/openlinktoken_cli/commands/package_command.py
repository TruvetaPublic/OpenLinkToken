# SPDX-License-Identifier: MIT

import logging
import sys
import uuid
from typing import List

from openlinktoken.metadata import Metadata
from openlinktoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer
from openlinktoken_cli.io.csv.person_attributes_csv_reader import PersonAttributesCSVReader
from openlinktoken_cli.io.csv.person_attributes_csv_writer import PersonAttributesCSVWriter
from openlinktoken_cli.io.json.metadata_json_writer import MetadataJsonWriter
from openlinktoken_cli.io.parquet.person_attributes_parquet_reader import PersonAttributesParquetReader
from openlinktoken_cli.io.parquet.person_attributes_parquet_writer import PersonAttributesParquetWriter
from openlinktoken_cli.processor.person_attributes_processor import (
    PersonAttributesProcessingSummary,
    PersonAttributesProcessor,
)
from openlinktoken_cli.util.cli_error_reporter import archive_cli_error, format_error_reference_message
from openlinktoken_cli.util.cli_run_reporter import CliRunReporter
from openlinktoken_cli.util.exchange_config import derive_transport_encryption_key, resolve_exchange_config
from openlinktoken_cli.util.file_type_detector import FileTypeDetector

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
            required=True,
            dest="output_path",
            help="Output file path",
        )

        parser.add_argument(
            "--exchange-config",
            required=False,
            dest="exchange_config",
            metavar="PATH",
            help="Path to the exchange config JSON (default: ./openlinktoken-YYYY-MM-DD.exchange.json)",
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

        parser.set_defaults(func=PackageCommand.execute)

    @staticmethod
    def execute(args):
        """Execute the package command."""
        input_type = FileTypeDetector.detect_input_type(args.input_path)
        if not input_type:
            logger.error("Unable to auto-detect input type. Supported input formats: csv, parquet")
            return 1

        output_type = FileTypeDetector.detect_output_type(args.output_path)
        if not output_type:
            logger.error("Unable to auto-detect output type. Supported output formats: csv, parquet, zip")
            return 1

        ring_id = args.ring_id if args.ring_id and args.ring_id.strip() else str(uuid.uuid4())
        hash_record_ids = getattr(args, "hash_record_ids", False)
        reporter = CliRunReporter("package")

        try:
            with reporter:
                try:
                    logger.info("Running package command (tokenize + encrypt)")
                    logger.info(f"Input: {args.input_path} ({input_type})")
                    logger.info(f"Output: {args.output_path} ({output_type})")
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
                    summary, metadata_path = PackageCommand._process_tokens(
                        args.input_path,
                        args.output_path,
                        input_type,
                        output_type,
                        exchange.hashing_secret,
                        encryption_key,
                        ring_id,
                        hash_record_ids,
                        progress_callback=reporter.make_progress_callback("Packaging records", "records"),
                    )
                    logger.info("Token generation and encryption completed successfully")
                except Exception as error:
                    logger.error("Error during token processing: %s", error)
                    raise
            reporter.finish_success(
                "Package complete",
                PackageCommand._build_summary_lines(args.output_path, metadata_path, summary, hash_record_ids),
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
            with (
                PackageCommand._create_reader(input_path, input_type) as reader,
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
        metadata_path: str,
        summary: PersonAttributesProcessingSummary,
        hash_record_ids: bool,
    ) -> list[str]:
        lines = [
            f"Output: {output_path}",
            f"Metadata: {metadata_path}",
            f"Rows processed: {summary.total_rows:,}",
            f"Rows with invalid attributes: {summary.total_rows_with_invalid_attributes:,}",
        ]
        lines.extend(
            CliRunReporter.summarize_count_lines("Top invalid attributes", summary.invalid_attributes_by_type, limit=3)
        )
        lines.extend(CliRunReporter.summarize_count_lines("Blank tokens by rule", summary.blank_tokens_by_rule))
        if hash_record_ids:
            lines.append("Record ID hashing: enabled")
        return lines

    @staticmethod
    def _create_reader(path: str, file_type: str):
        """Create a PersonAttributesReader based on file type."""
        file_type_lower = file_type.lower()
        if file_type_lower == FileTypeDetector.TYPE_CSV:
            return PersonAttributesCSVReader(path)
        elif file_type_lower == FileTypeDetector.TYPE_PARQUET:
            return PersonAttributesParquetReader(path)
        else:
            raise ValueError(f"Unsupported input type: {file_type}")

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
