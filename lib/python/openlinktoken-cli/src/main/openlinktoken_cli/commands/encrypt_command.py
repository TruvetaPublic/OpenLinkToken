# SPDX-License-Identifier: MIT

import contextlib
import logging
import sys
import tempfile
from pathlib import Path

from openlinktoken.tokens.token import Token
from openlinktoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from openlinktoken.tokentransformer.jwe_match_token_formatter import JweMatchTokenFormatter
from openlinktoken_cli.io.csv.token_csv_reader import TokenCSVReader
from openlinktoken_cli.io.csv.token_csv_writer import TokenCSVWriter
from openlinktoken_cli.io.parquet.token_parquet_reader import TokenParquetReader
from openlinktoken_cli.io.parquet.token_parquet_writer import TokenParquetWriter
from openlinktoken_cli.processor.token_constants import TokenConstants
from openlinktoken_cli.processor.token_transformation_processor import TokenTransformationSummary
from openlinktoken_cli.util.cli_error_reporter import archive_cli_error, format_error_reference_message
from openlinktoken_cli.util.cli_run_reporter import CliRunReporter
from openlinktoken_cli.util.exchange_config import derive_transport_encryption_key, resolve_exchange_config
from openlinktoken_cli.util.file_type_detector import FileTypeDetector
from openlinktoken_cli.util.path_utils import get_auto_output_path
from openlinktoken_cli.util.ring_id_utils import resolve_ring_id
from openlinktoken_cli.util.zip_utils import bundle_into_zip

logger = logging.getLogger(__name__)


class EncryptCommand:
    """Encrypt command - encrypts hashed tokens."""

    @staticmethod
    def register_subcommand(subparsers):
        """Register the encrypt subcommand with the argument parser."""
        parser = subparsers.add_parser(
              "encrypt",
            help="Encrypt hashed tokens using the exchange config",
            description="Encrypt hashed tokens using the exchange config",
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
            help="Input file path with hashed tokens",
         )

        parser.add_argument(
              "-o",
              "--output",
            required=False,
            dest="output_path",
            help="Output file path for encrypted tokens (defaults to input filename with '_encrypted' suffix)",
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

          # --no-progress / -q: suppress interactive progress indicator
        parser.add_argument(
              "--no-progress",
              "-q",
            action="store_true",
            default=False,
            dest="no_progress",
            help="Suppress interactive progress indicator (e.g. for non-interactive / CI environments)",
         )

        parser.set_defaults(func=EncryptCommand.execute)

    @staticmethod
    def execute(args):
        """Execute the encrypt command."""
        input_type = FileTypeDetector.detect_input_type(args.input_path)
        if not input_type:
            logger.error("Unable to auto-detect input type. Supported input formats: csv, parquet")
            return 1

          # Resolve output path if not provided
        output_path = args.output_path if args.output_path else get_auto_output_path(args.input_path, "encrypt")

        output_type = FileTypeDetector.detect_output_type(output_path)
        if not output_type:
            logger.error("Unable to auto-detect output type from provided/generated path.")
            return 1
        ring_id = resolve_ring_id(args.ring_id)
        reporter = CliRunReporter("encrypt", no_progress=args.no_progress)

        try:
            with reporter:
                try:
                    logger.info("Running encrypt command")
                    logger.info(f"Input: {args.input_path} ({input_type})")
                    logger.info(f"Output: {output_path} ({output_type})")
                    logger.info(f"Ring ID: {ring_id}")

                    reporter.update_status("Resolving exchange config")
                    exchange = resolve_exchange_config(
                        args.exchange_config,
                        private_key_path=args.private_key,
                        private_key_env=args.private_key_env,
                       )
                    encryption_key = derive_transport_encryption_key(exchange)
                    logger.info(f"Exchange config: {exchange.path}")

                    reporter.update_status("Encrypting tokens")
                    is_zip = output_type == FileTypeDetector.TYPE_ZIP

                    if is_zip:
                        if not exchange.path:
                            raise ValueError(
                                  "ZIP output requires an exchange config file path. "
                                  "Ensure the exchange config was loaded from a file (exchange.path must not be None)."
                               )
                        logger.info("ZIP output: encrypted tokens and exchange config will be bundled")

                       # Determine total rows to enable %/ETA
                    total_rows: int | None = None
                    try:
                        reader = EncryptCommand._create_token_reader(input_path, input_type)
                        total_rows = reader.row_count()
                        reader.close()
                    except Exception:
                        total_rows = None

                    with contextlib.ExitStack() as stack:
                        if is_zip:
                            temp_dir = stack.enter_context(tempfile.TemporaryDirectory())
                            zip_path = Path(output_path)
                            token_output_path = str(Path(temp_dir) / f"{zip_path.stem}.{input_type}")
                            token_output_type = input_type
                        else:
                            token_output_path = output_path
                            token_output_type = output_type

                          # Wire total_rows to reporter if known
                        if total_rows is not None:
                            reporter.set_total_rows(total_rows)

                        summary = EncryptCommand._encrypt_tokens(
                            args.input_path,
                            token_output_path,
                            input_type,
                            token_output_type,
                            encryption_key,
                            ring_id,
                            progress_callback=reporter.make_progress_callback("Encrypting tokens", "tokens"),
                         )

                        if is_zip:
                            bundle_into_zip(output_path, token_output_path, exchange.path)
                    logger.info("Token encryption completed successfully")
                except Exception as error:
                    logger.error("Error during token encryption: %s", error)
                    raise
            reporter.finish_success("Encrypt complete", EncryptCommand._build_summary_lines(output_path, summary))
            return 0
        except Exception as error:
            report = archive_cli_error(error, command_name="encrypt", existing_report=reporter.log_report)
            print(f"Error: {error}", file=sys.stderr)
            print(format_error_reference_message(report), file=sys.stderr)
            return 1

    @staticmethod
    def _encrypt_tokens(
        input_path: str,
        output_path: str,
        input_type: str,
        output_type: str,
        encryption_key: bytes,
        ring_id: str,
        progress_callback=None,
     ) -> TokenTransformationSummary:
        """Encrypt tokens from input file."""
        try:
            encryptor = EncryptTokenTransformer(encryption_key)
            jwe_formatters: dict[str, JweMatchTokenFormatter] = {}
            row_counter = 0
            encrypted_counter = 0
            error_counter = 0
            last_reported_count = 0

            with (
                EncryptCommand._create_token_reader(input_path, input_type) as reader,
                EncryptCommand._create_token_writer(output_path, output_type) as writer,
              ):
                for row in reader:
                    row_counter += 1

                    token = row.get(TokenConstants.TOKEN)
                    if token and token != Token.BLANK:
                        try:
                            encrypted_token = encryptor.transform(token)
                            wrapped_token = EncryptCommand._wrap_as_v1_token(
                                encrypted_token,
                                row,
                                encryption_key,
                                ring_id,
                                jwe_formatters,
                               )
                            row[TokenConstants.TOKEN] = wrapped_token
                            encrypted_counter += 1
                        except Exception as e:
                            logger.error(
                                  f"Failed to encrypt token for RecordId {row.get(TokenConstants.RECORD_ID)}, "
                                   f"RuleId {row.get(TokenConstants.RULE_ID)}: {e}"
                               )
                            error_counter += 1

                    writer.write_token(row)

                    if row_counter % 10000 == 0:
                        logger.info(f'Processed "{row_counter:,}" tokens')
                        last_reported_count = row_counter
                        if progress_callback is not None:
                            progress_callback(row_counter)

                  # Final flush
                if progress_callback is not None and row_counter > 0:
                    progress_callback(row_counter)

                logger.info(f"Processed a total of {row_counter:,} tokens")
                logger.info(f"Successfully encrypted {encrypted_counter:,} tokens")
                if error_counter > 0:
                    logger.warning(f"Failed to encrypt {error_counter:,} tokens")

                return TokenTransformationSummary(
                    total_tokens=row_counter,
                    transformed_tokens=encrypted_counter,
                    failed_tokens=error_counter,
                  )

        except Exception:
            raise

    @staticmethod
    def _build_summary_lines(output_path: str, summary: TokenTransformationSummary) -> list[str]:
        return [
             f"Output: {output_path}",
            f"Tokens processed: {summary.total_tokens:,}",
            f"Successfully encrypted: {summary.transformed_tokens:,}",
             f"Failed to encrypt: {summary.failed_tokens:,}",
          ]

    @staticmethod
    def _wrap_as_v1_token(
        encrypted_token: str,
        row: dict,
        encryption_key: bytes,
        ring_id: str,
        jwe_formatters: dict[str, JweMatchTokenFormatter],
     ) -> str:
        rule_id = row.get(TokenConstants.RULE_ID)
        if not rule_id:
            return encrypted_token

        formatter = jwe_formatters.get(rule_id)
        if formatter is None:
            formatter = JweMatchTokenFormatter(encryption_key, ring_id, rule_id, "org.openlinktoken")
            jwe_formatters[rule_id] = formatter

        return formatter.transform(encrypted_token)

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
