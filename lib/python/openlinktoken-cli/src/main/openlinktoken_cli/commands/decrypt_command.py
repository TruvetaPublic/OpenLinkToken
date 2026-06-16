# SPDX-License-Identifier: MIT

import logging
import sys

from openlinktoken.tokentransformer.decrypt_token_transformer import DecryptTokenTransformer
from openlinktoken_cli.io.csv.token_csv_reader import TokenCSVReader
from openlinktoken_cli.io.csv.token_csv_writer import TokenCSVWriter
from openlinktoken_cli.io.parquet.token_parquet_reader import TokenParquetReader
from openlinktoken_cli.io.parquet.token_parquet_writer import TokenParquetWriter
from openlinktoken_cli.processor.token_decryption_processor import TokenDecryptionProcessor
from openlinktoken_cli.processor.token_transformation_processor import TokenTransformationSummary
from openlinktoken_cli.util.cli_error_reporter import archive_cli_error, format_error_reference_message
from openlinktoken_cli.util.cli_run_reporter import CliRunReporter
from openlinktoken_cli.util.exchange_config import derive_transport_encryption_key, resolve_exchange_config
from openlinktoken_cli.util.file_type_detector import FileTypeDetector
from openlinktoken_cli.util.path_utils import get_auto_output_path

logger = logging.getLogger(__name__)


class DecryptCommand:
    """Decrypt command - decrypts encrypted tokens."""

    @staticmethod
    def register_subcommand(subparsers):
        """Register the decrypt subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "decrypt",
            help="Decrypt encrypted tokens using the exchange config",
            description="Decrypt encrypted tokens using the exchange config",
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
            help="Input file path with encrypted tokens",
        )

        parser.add_argument(
            "-o",
            "--output",
            required=False,
            dest="output_path",
            help="Output file path for decrypted tokens (defaults to input filename with '_decrypted' suffix)",
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
            "-q",
            "--no-progress",
            action="store_true",
            default=False,
            help="Suppress interactive progress indicator (e.g. for non-interactive / CI environments)",
            )

        parser.set_defaults(func=DecryptCommand.execute)

    @staticmethod
    def execute(args):
        """Execute the decrypt command."""
        input_type = FileTypeDetector.detect_input_type(args.input_path)
        if not input_type:
            logger.error("Unable to auto-detect input type. Supported input formats: csv, parquet")
            return 1

        # Resolve output path if not provided
        output_path = args.output_path if args.output_path else get_auto_output_path(args.input_path, "decrypt")

        output_type = FileTypeDetector.detect_output_type(output_path)
        if not output_type:
            logger.error("Unable to auto-detect output type from provided/generated path.")
            return 1

        reporter = CliRunReporter("decrypt", no_progress=args.no_progress)
        try:
            with reporter:
                try:
                    logger.info("Running decrypt command")
                    logger.info(f"Input: {args.input_path} ({input_type})")
                    logger.info(f"Output: {output_path} ({output_type})")

                    reporter.update_status("Resolving exchange config")
                    exchange = resolve_exchange_config(
                        args.exchange_config,
                        private_key_path=args.private_key,
                        private_key_env=args.private_key_env,
                    )
                    encryption_key = derive_transport_encryption_key(exchange)
                    logger.info(f"Exchange config: {exchange.path}")

                    reporter.update_status("Decrypting tokens")
                    # Determine total rows for parquet to enable %/ETA
                    total_rows: int | None = None
                    if input_type == FileTypeDetector.TYPE_PARQUET:
                        try:
                            import pyarrow.parquet as pq
                            total_rows = len(pq.ParquetFile(args.input_path))
                        except Exception:
                            pass
                    if total_rows is not None:
                        reporter.set_total_rows(total_rows)
                    summary = DecryptCommand._decrypt_tokens(
                        args.input_path,
                        output_path,
                        input_type,
                        output_type,
                        encryption_key,
                        progress_callback=reporter.make_progress_callback("Decrypting tokens", "tokens"),
                    )
                    logger.info("Token decryption completed successfully")
                except Exception as error:
                    logger.error("Error during token decryption: %s", error)
                    raise
            reporter.finish_success("Decrypt complete", DecryptCommand._build_summary_lines(output_path, summary))
            return 0
        except Exception as error:
            report = archive_cli_error(error, command_name="decrypt", existing_report=reporter.log_report)
            print(f"Error: {error}", file=sys.stderr)
            print(format_error_reference_message(report), file=sys.stderr)
            return 1

    @staticmethod
    def _decrypt_tokens(
        input_path: str,
        output_path: str,
        input_type: str,
        output_type: str,
        encryption_key: bytes,
        progress_callback=None,
    ) -> TokenTransformationSummary:
        """Decrypt tokens from input file."""
        try:
            decryptor = DecryptTokenTransformer(encryption_key)

            with (
                DecryptCommand._create_token_reader(input_path, input_type) as reader,
                DecryptCommand._create_token_writer(output_path, output_type) as writer,
            ):
                return TokenDecryptionProcessor.process_with_key(
                    reader,
                    writer,
                    decryptor,
                    encryption_key,
                    progress_callback,
                )

        except Exception:
            raise

    @staticmethod
    def _build_summary_lines(output_path: str, summary: TokenTransformationSummary) -> list[str]:
        return [
            f"Output: {output_path}",
            f"Tokens processed: {summary.total_tokens:,}",
            f"Successfully decrypted: {summary.transformed_tokens:,}",
            f"Failed to decrypt: {summary.failed_tokens:,}",
        ]

    @staticmethod
    def _create_token_reader(path: str, file_type: str):
        """Create a TokenReader based on file type."""
        file_type_lower = file_type.lower()
        if file_type_lower == FileTypeDetector.TYPE_CSV:
            return TokenCSVReader(path)
        elif file_type_lower == FileTypeDetector.TYPE_PARQUET:
            return TokenParquetReader(path)
        else:
            raise ValueError(f"Unsupported input type: {file_type}")

    @staticmethod
    def _create_token_writer(path: str, file_type: str):
        """Create a TokenWriter based on file type."""
        file_type_lower = file_type.lower()
        if file_type_lower == FileTypeDetector.TYPE_CSV:
            return TokenCSVWriter(path)
        elif file_type_lower == FileTypeDetector.TYPE_PARQUET:
            return TokenParquetWriter(path)
        else:
            raise ValueError(f"Unsupported output type: {file_type}")
