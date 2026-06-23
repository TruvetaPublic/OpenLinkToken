# SPDX-License-Identifier: MIT

import logging
import sys
from typing import List, Optional

from openlinktoken.metadata import Metadata
from openlinktoken_cli.commands.tokenization_config_helper import TokenizationConfigHelper
from openlinktoken_cli.tokens.config.dynamic_attribute_factory import DynamicAttributeFactory
from openlinktoken_cli.tokens.config.dynamic_token_definition import DynamicTokenDefinition
from openlinktoken_cli.tokens.config.tokenization_config import TokenizationConfig
from openlinktoken.tokens.tokenizer.passthrough_tokenizer import PassthroughTokenizer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer
from openlinktoken_cli.io.csv.person_attributes_csv_writer import PersonAttributesCSVWriter
from openlinktoken_cli.io.json.metadata_json_writer import MetadataJsonWriter
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
from openlinktoken_cli.util.path_utils import get_auto_output_path

logger = logging.getLogger(__name__)


class TokenizeCommand:
    """
    Tokenize command - generates tokens from person attributes.

    Default mode (``--mode default`` or omitted): applies SHA-256 then
    HMAC-SHA256 hashing on the token signature using the hashing secret from the
    exchange config.

    Hash-only mode (``--mode hash-only``): applies SHA-256 only (no HMAC). No
    exchange config or secret is required. Output tokens are 64-character hex
    strings. This mode is deterministic and keyless — **not** suitable for
    production or cross-organisation exchange where keyed HMAC hashing is
    required.

    Demo mode (``--mode demo``): skips all hashing so tokens are the raw
    pipe-separated attribute signature strings. No secret is needed, making it easy
    to explore the output without managing secrets. Demo-mode output is
    **not** suitable for production or cross-organisation exchange.
    """

    _MODE_DEFAULT = "default"
    _MODE_HASH_ONLY = "hash-only"
    _MODE_DEMO = "demo"

    @staticmethod
    def register_subcommand(subparsers):
        """Register the tokenize subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "tokenize",
            help="Generate tokens from person attributes (--mode default|hash-only|demo)",
            description=(
                "Generate tokens from person attributes.\n\n"
                "Default mode (--mode default or omitted): tokens are HMAC-SHA256 hashed "
                "using the exchange config.\n"
                "Hash-only mode (--mode hash-only): tokens are SHA-256 hashed (no HMAC, no secret). "
                "Output is deterministic and NOT suitable for production or cross-organisation exchange.\n"
                "Demo mode (--mode demo): tokens are plain attribute signature strings; no secret needed."
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
            required=False,
            dest="output_path",
            help="Output file path (defaults to input filename with '_tokenized' suffix)",
        )

        parser.add_argument(
            "--mode",
            choices=[TokenizeCommand._MODE_DEFAULT, TokenizeCommand._MODE_HASH_ONLY, TokenizeCommand._MODE_DEMO],
            default=TokenizeCommand._MODE_DEFAULT,
            dest="mode",
            help=(
                "Tokenization mode: 'default' uses SHA-256 + HMAC-SHA256 with the exchange config; "
                "'hash-only' uses deterministic SHA-256 only with no exchange config or secret; "
                "'demo' outputs raw pipe-separated attribute signature strings."
            ),
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
                "This is a one-way operation with no traceability. "
                "Supported in default tokenize mode only."
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

        parser.set_defaults(func=TokenizeCommand.execute)

    @staticmethod
    def execute(args):
        """Execute the tokenize command."""
        mode = getattr(args, "mode", TokenizeCommand._MODE_DEFAULT)
        hash_record_ids = getattr(args, "hash_record_ids", False)
        tokenization_config_path = getattr(args, "tokenization_config", None)

        input_type = FileTypeDetector.detect_input_type(args.input_path)
        if not input_type:
            logger.error("Unable to auto-detect input type. Supported input formats: csv, parquet")
            return 1

        # Resolve output path if not provided
        output_path = args.output_path if args.output_path else get_auto_output_path(args.input_path, "tokenize")

        output_type = FileTypeDetector.detect_output_type(output_path)
        if not output_type:
            logger.error("Unable to auto-detect output type from provided/generated path.")
            return 1

        if mode == TokenizeCommand._MODE_DEMO and hash_record_ids:
            logger.error("--mode demo cannot be combined with --hash-record-ids.")
            return 1

        if mode == TokenizeCommand._MODE_DEMO and args.exchange_config:
            logger.error("--mode demo cannot be combined with --exchange-config.")
            return 1

        if mode == TokenizeCommand._MODE_HASH_ONLY and args.exchange_config:
            logger.error("--mode hash-only cannot be combined with --exchange-config.")
            return 1

        if mode == TokenizeCommand._MODE_HASH_ONLY and hash_record_ids:
            logger.error("--mode hash-only cannot be combined with --hash-record-ids.")
            return 1

        if mode == TokenizeCommand._MODE_HASH_ONLY and (args.private_key or args.private_key_env):
            logger.error("--mode hash-only cannot be combined with --private-key or --private-key-env.")
            return 1

        reporter = CliRunReporter("tokenize", no_progress=args.no_progress)
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
                            "Running in HASH-ONLY MODE - output tokens are deterministic SHA-256 hashes "
                            "without HMAC. Do not use hash-only output for production or "
                            "cross-organisation exchange."
                        )
                    else:
                        logger.info("Running tokenize command (default mode)")
                    logger.info(f"Input: {args.input_path} ({input_type})")
                    logger.info(f"Output: {output_path} ({output_type})")
                    if hash_record_ids:
                        logger.info("Record ID hashing enabled: RecordIds will be SHA-256 hashed in output")

                        # Count total rows via reader to enable %/ETA
                    total_rows: int | None = None
                    try:
                        reader = TokenizationConfigHelper.create_reader(args.input_path, input_type)
                        total_rows = reader.row_count()
                        reader.close()
                    except Exception:
                        total_rows = None

                    if total_rows is not None:
                        reporter.set_total_rows(total_rows)

                    if mode == TokenizeCommand._MODE_DEMO:
                        reporter.update_status("Tokenizing records")
                        summary, metadata_path = TokenizeCommand._process_tokens_demo(
                            args.input_path,
                            output_path,
                            input_type,
                            output_type,
                            tokenization_config_path,
                            progress_callback=reporter.make_progress_callback("Tokenizing records", "records"),
                        )
                    elif mode == TokenizeCommand._MODE_HASH_ONLY:
                        reporter.update_status("Tokenizing records")
                        summary, metadata_path = TokenizeCommand._process_tokens_hash_only(
                            args.input_path,
                            output_path,
                            input_type,
                            output_type,
                            hash_record_ids,
                            tokenization_config_path,
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
                            output_path,
                            input_type,
                            output_type,
                            exchange.hashing_secret,
                            hash_record_ids,
                            tokenization_config_path,
                            progress_callback=reporter.make_progress_callback("Tokenizing records", "records"),
                        )
                    logger.info("Token generation completed successfully")
                except Exception as error:
                    logger.error("Error during token generation: %s", error)
                    raise
            # Final progress flush
            reporter.finish_success(
                "Tokenize complete",
                TokenizeCommand._build_summary_lines(
                    output_path,
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
        tokenization_config_path: Optional[str] = None,
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
            config, factory, token_definition = TokenizeCommand._load_tokenization_config(tokenization_config_path)
            with (
                TokenizeCommand._create_reader(input_path, input_type, config, factory) as reader,
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
                    token_definition=token_definition,
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
        tokenization_config_path: Optional[str] = None,
        progress_callback=None,
    ) -> tuple[PersonAttributesProcessingSummary, str]:
        """Process tokens in hash-only mode using SHA-256 only (no HMAC, no secret)."""
        try:
            config, factory, token_definition = TokenizationConfigHelper.load_tokenization_config(
                tokenization_config_path
            )
            with (
                TokenizationConfigHelper.create_reader(input_path, input_type, config, factory) as reader,
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
                    token_definition=token_definition,
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
        tokenization_config_path: Optional[str] = None,
        progress_callback=None,
    ) -> tuple[PersonAttributesProcessingSummary, str]:
        """Process tokens in demo mode using PassthroughTokenizer (no hashing)."""
        try:
            config, factory, token_definition = TokenizationConfigHelper.load_tokenization_config(
                tokenization_config_path
            )
            with (
                TokenizationConfigHelper.create_reader(input_path, input_type, config, factory) as reader,
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
                    token_definition=token_definition,
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
            TokenizeCommand._MODE_DEFAULT: "default HMAC-SHA256",
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
    def _create_reader(
        path: str,
        file_type: str,
        config: Optional[TokenizationConfig] = None,
        factory: Optional[DynamicAttributeFactory] = None,
    ):
        """Create a PersonAttributesReader based on file type."""
        return TokenizationConfigHelper.create_reader(path, file_type, config, factory)

    @staticmethod
    def _load_tokenization_config(
        tokenization_config_path: Optional[str] = None,
    ) -> tuple[TokenizationConfig | None, DynamicAttributeFactory | None, DynamicTokenDefinition | None]:
        """Load tokenization config via helper."""
        return TokenizationConfigHelper.load_tokenization_config(tokenization_config_path)

    @staticmethod
    def _build_configured_input_attribute_map(
        config: TokenizationConfig,
        factory: DynamicAttributeFactory,
    ) -> dict:
        """Build attribute map via helper."""
        return TokenizationConfigHelper.build_configured_input_attribute_map(config, factory)

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
