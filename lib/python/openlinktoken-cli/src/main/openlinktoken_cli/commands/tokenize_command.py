# SPDX-License-Identifier: MIT

import logging
import sys
from typing import List

from openlinktoken.metadata import Metadata
from openlinktoken.tokens.tokenizer.passthrough_tokenizer import PassthroughTokenizer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer
from openlinktoken_cli.io.csv.person_attributes_csv_reader import PersonAttributesCSVReader
from openlinktoken_cli.io.csv.person_attributes_csv_writer import PersonAttributesCSVWriter
from openlinktoken_cli.io.json.metadata_json_writer import MetadataJsonWriter
from openlinktoken_cli.io.parquet.person_attributes_parquet_reader import (
    PersonAttributesParquetReader,
)
from openlinktoken_cli.io.parquet.person_attributes_parquet_writer import (
    PersonAttributesParquetWriter,
)
from openlinktoken_cli.processor.person_attributes_processor import (
    PersonAttributesProcessingSummary,
    PersonAttributesProcessor,
)
from openlinktoken_cli.util.cli_error_reporter import archive_cli_error, format_error_reference_message
from openlinktoken_cli.util.cli_run_reporter import CliRunReporter
from openlinktoken_cli.util.exchange_config import resolve_exchange_config
from openlinktoken_cli.util.file_type_detector import FileTypeDetector

logger = logging.getLogger(__name__)


class TokenizeCommand:
    """
    Tokenize command - generates tokens from person attributes.

    Normal mode (default): applies SHA-256 then HMAC-SHA256 hashing on the token
    signature using the hashing secret from the exchange config.

    Hash-only mode (``--hash-only``): applies SHA-256 only (no HMAC). No exchange
    config or secret is required. Output tokens are 64-character hex strings.
    This mode is deterministic and keyless — **not** suitable for production or
    cross-organisation exchange where keyed HMAC hashing is required.

    Demo mode (``--demo-mode``): skips all hashing so tokens are the raw
    pipe-separated attribute signature strings. No secret is needed, making it easy
    to explore the output without managing secrets. Demo-mode output is
    **not** suitable for production or cross-organisation exchange.
    """

    _MODE_NORMAL = "normal"
    _MODE_HASH_ONLY = "hash-only"
    _MODE_DEMO = "demo"

    @staticmethod
    def register_subcommand(subparsers):
        """Register the tokenize subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "tokenize",
            help="Generate tokens from person attributes (normal: HMAC-SHA256; hash-only: SHA-256; demo: plain)",
            description=(
                "Generate tokens from person attributes.\n\n"
                "Normal mode: tokens are HMAC-SHA256 hashed using the exchange config.\n"
                "Hash-only mode (--hash-only): tokens are SHA-256 hashed (no HMAC, no secret). "
                "Output is deterministic and NOT suitable for production or cross-organisation exchange.\n"
                "Demo mode (--demo-mode): tokens are plain attribute signature strings; no secret needed."
            ),
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

        mode_group = parser.add_mutually_exclusive_group()
        mode_group.add_argument(
            "--hash-only",
            action="store_true",
            default=False,
            dest="hash_only",
            help=(
                "Hash-only mode: apply SHA-256 without HMAC. No exchange config or secret is needed. "
                "Output tokens are 64-character hex strings. "
                "WARNING: output is deterministic and keyless — NOT suitable for production or "
                "cross-organisation exchange where keyed HMAC hashing is required."
            ),
        )
        mode_group.add_argument(
            "--demo-mode",
            action="store_true",
            default=False,
            dest="demo_mode",
            help=(
                "Enable demo mode: output raw pipe-separated attribute signature strings with no hashing. "
                "--exchange-config is not allowed in this mode. "
                "Demo output is NOT suitable for production or cross-organisation exchange."
            ),
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
            help="Path to the private key PEM used to decrypt the exchange config",
        )
        private_key_group.add_argument(
            "--private-key-env",
            dest="private_key_env",
            metavar="ENV_VAR",
            help="Read the private key PEM from the named environment variable",
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

        parser.set_defaults(func=TokenizeCommand.execute)

    @staticmethod
    def execute(args):
        """Execute the tokenize command."""
        demo_mode = getattr(args, "demo_mode", False)
        hash_only = getattr(args, "hash_only", False)
        hash_record_ids = getattr(args, "hash_record_ids", False)

        input_type = FileTypeDetector.detect_input_type(args.input_path)
        if not input_type:
            logger.error("Unable to auto-detect input type. Supported input formats: csv, parquet")
            return 1

        output_type = FileTypeDetector.detect_output_type(args.output_path)
        if not output_type:
            logger.error("Unable to auto-detect output type. Supported output formats: csv, parquet, zip")
            return 1

        if demo_mode and args.exchange_config:
            logger.error("--demo-mode cannot be combined with --exchange-config.")
            return 1

        if hash_only and args.exchange_config:
            logger.error("--hash-only cannot be combined with --exchange-config.")
            return 1

        if hash_only and (args.private_key or args.private_key_env):
            logger.error("--hash-only cannot be combined with --private-key or --private-key-env.")
            return 1

        if hash_only:
            mode = TokenizeCommand._MODE_HASH_ONLY
        elif demo_mode:
            mode = TokenizeCommand._MODE_DEMO
        else:
            mode = TokenizeCommand._MODE_NORMAL

        reporter = CliRunReporter("tokenize")
        try:
            with reporter:
                try:
                    if mode == TokenizeCommand._MODE_DEMO:
                        logger.warning(
                            "Running in DEMO MODE - tokens are raw attribute signature strings with no hashing. "
                            "Do not use demo-mode output in production or share it externally."
                        )
                    elif mode == TokenizeCommand._MODE_HASH_ONLY:
                        logger.warning(
                            "Running in HASH-ONLY MODE - tokens are SHA-256 hashed without HMAC. "
                            "Output is deterministic and keyless. "
                            "Do not use hash-only output for production or cross-organisation exchange."
                        )
                    else:
                        logger.info("Running tokenize command (normal mode)")
                    logger.info(f"Input: {args.input_path} ({input_type})")
                    logger.info(f"Output: {args.output_path} ({output_type})")
                    if hash_record_ids:
                        logger.info("Record ID hashing enabled: RecordIds will be SHA-256 hashed in output")

                    if mode == TokenizeCommand._MODE_DEMO:
                        reporter.update_status("Tokenizing records")
                        summary, metadata_path = TokenizeCommand._process_tokens_demo(
                            args.input_path,
                            args.output_path,
                            input_type,
                            output_type,
                            progress_callback=reporter.make_progress_callback("Tokenizing records", "records"),
                        )
                    elif mode == TokenizeCommand._MODE_HASH_ONLY:
                        reporter.update_status("Tokenizing records")
                        summary, metadata_path = TokenizeCommand._process_tokens_hash_only(
                            args.input_path,
                            args.output_path,
                            input_type,
                            output_type,
                            hash_record_ids,
                            progress_callback=reporter.make_progress_callback("Tokenizing records", "records"),
                        )
                    else:
                        reporter.update_status("Resolving exchange config")
                        exchange = resolve_exchange_config(
                            args.exchange_config,
                            private_key_path=args.private_key,
                            private_key_env=args.private_key_env,
                        )
                        logger.info(f"Exchange config: {exchange.path}")
                        reporter.update_status("Tokenizing records")
                        summary, metadata_path = TokenizeCommand._process_tokens(
                            args.input_path,
                            args.output_path,
                            input_type,
                            output_type,
                            exchange.hashing_secret,
                            hash_record_ids,
                            progress_callback=reporter.make_progress_callback("Tokenizing records", "records"),
                        )
                    logger.info("Token generation completed successfully")
                except Exception as error:
                    logger.error("Error during token generation: %s", error)
                    raise
            reporter.finish_success(
                "Tokenize complete",
                TokenizeCommand._build_summary_lines(
                    args.output_path,
                    metadata_path,
                    summary,
                    mode,
                    hash_record_ids,
                ),
            )
            return 0
        except Exception as error:
            report = archive_cli_error(error, command_name="tokenize", existing_report=reporter.log_report)
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
        hash_record_ids: bool = False,
        progress_callback=None,
    ) -> tuple[PersonAttributesProcessingSummary, str]:
        """Process tokens in normal mode using SHA-256 + HMAC-SHA256."""
        token_transformer_list: List[TokenTransformer] = []

        try:
            # Add only hash transformer (no encryption in tokenize mode)
            token_transformer_list.append(HashTokenTransformer(hashing_secret))
        except Exception as e:
            raise RuntimeError("Failed to initialize transformer") from e

        try:
            with (
                TokenizeCommand._create_reader(input_path, input_type) as reader,
                TokenizeCommand._create_writer(output_path, output_type) as writer,
            ):
                metadata = Metadata()
                metadata_map = metadata.initialize()
                # Only record the hashing-secret hash in normal mode
                metadata.add_hashed_secret(Metadata.HASHING_SECRET_HASH, hashing_secret)

                summary = PersonAttributesProcessor.process(
                    reader,
                    writer,
                    token_transformer_list,
                    metadata_map,
                    hash_record_ids=hash_record_ids,
                    progress_callback=progress_callback,
                )

                metadata_writer = MetadataJsonWriter(output_path)
                metadata_writer.write(metadata_map)
                return summary, metadata_writer.metadata_file_path

        except Exception:
            raise

    @staticmethod
    def _process_tokens_hash_only(
        input_path: str,
        output_path: str,
        input_type: str,
        output_type: str,
        hash_record_ids: bool = False,
        progress_callback=None,
    ) -> tuple[PersonAttributesProcessingSummary, str]:
        """Process tokens in hash-only mode using SHA-256 only (no HMAC, no secret)."""
        try:
            with (
                TokenizeCommand._create_reader(input_path, input_type) as reader,
                TokenizeCommand._create_writer(output_path, output_type) as writer,
            ):
                metadata = Metadata()
                metadata_map = metadata.initialize()
                # Deliberately omit add_hashed_secret — no secret used in hash-only mode

                summary = PersonAttributesProcessor.process(
                    reader,
                    writer,
                    [],
                    metadata_map,
                    hash_record_ids=hash_record_ids,
                    progress_callback=progress_callback,
                )

                metadata_writer = MetadataJsonWriter(output_path)
                metadata_writer.write(metadata_map)
                return summary, metadata_writer.metadata_file_path

        except Exception:
            raise

    @staticmethod
    def _process_tokens_demo(
        input_path: str,
        output_path: str,
        input_type: str,
        output_type: str,
        progress_callback=None,
    ) -> tuple[PersonAttributesProcessingSummary, str]:
        """Process tokens in demo mode using PassthroughTokenizer (no hashing)."""
        try:
            with (
                TokenizeCommand._create_reader(input_path, input_type) as reader,
                TokenizeCommand._create_writer(output_path, output_type) as writer,
            ):
                metadata = Metadata()
                metadata_map = metadata.initialize()
                # Deliberately omit add_hashed_secret — no secret used in demo mode

                summary = PersonAttributesProcessor.process_with_tokenizer(
                    reader,
                    writer,
                    PassthroughTokenizer([]),
                    metadata_map,
                    progress_callback=progress_callback,
                )

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
        mode: str,
        hash_record_ids: bool,
    ) -> list[str]:
        mode_labels = {
            TokenizeCommand._MODE_NORMAL: "normal HMAC-SHA256",
            TokenizeCommand._MODE_HASH_ONLY: "hash-only SHA-256",
            TokenizeCommand._MODE_DEMO: "demo plain signatures",
        }
        lines = [
            f"Output: {output_path}",
            f"Metadata: {metadata_path}",
            f"Mode: {mode_labels.get(mode, mode)}",
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
