"""
Copyright (c) Truveta. All rights reserved.
"""

import logging
import uuid

from opentoken.tokens.token import Token
from opentoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from opentoken.tokentransformer.jwe_match_token_formatter import JweMatchTokenFormatter
from opentoken_cli.io.csv.token_csv_reader import TokenCSVReader
from opentoken_cli.io.csv.token_csv_writer import TokenCSVWriter
from opentoken_cli.io.parquet.token_parquet_reader import TokenParquetReader
from opentoken_cli.io.parquet.token_parquet_writer import TokenParquetWriter
from opentoken_cli.processor.token_constants import TokenConstants
from opentoken_cli.util import StringMaskingUtil

logger = logging.getLogger(__name__)


class EncryptCommand:
    """
    Encrypt command - encrypts hashed tokens.
    """

    TYPE_CSV = "csv"
    TYPE_PARQUET = "parquet"

    @staticmethod
    def register_subcommand(subparsers):
        """Register the encrypt subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "encrypt",
            help="Encrypt hashed tokens using encryption key",
            description="Encrypt hashed tokens using encryption key",
            add_help=False,  # Disable automatic -h for help to allow -e for encryptionkey
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
            required=True,
            dest="output_path",
            help="Output file path for encrypted tokens",
        )

        parser.add_argument(
            "-t",
            "--input-type",
            required=True,
            dest="input_type",
            choices=["csv", "parquet"],
            help="Input file type: csv or parquet",
        )

        parser.add_argument(
            "-ot",
            "--output-type",
            dest="output_type",
            choices=["csv", "parquet"],
            help="Output file type (defaults to input type): csv or parquet",
        )

        parser.add_argument(
            "-e",
            "--encryptionkey",
            required=True,
            dest="encryption_key",
            help="Encryption key for token encryption",
        )

        parser.add_argument(
            "--ring-id",
            dest="ring_id",
            default=None,
            help="Ring identifier for key management. Defaults to a random UUID if not provided",
        )

        parser.set_defaults(func=EncryptCommand.execute)

    @staticmethod
    def execute(args):
        """Execute the encrypt command."""
        logger.info("Running encrypt command")

        # Default output type to input type if not specified
        output_type = args.output_type if args.output_type else args.input_type
        ring_id = args.ring_id if args.ring_id and args.ring_id.strip() else str(uuid.uuid4())

        # Log parameters (mask key)
        logger.info(f"Input: {args.input_path} ({args.input_type})")
        logger.info(f"Output: {args.output_path} ({output_type})")
        logger.info(f"Encryption Key: {StringMaskingUtil.mask_string(args.encryption_key)}")
        logger.info(f"Ring ID: {ring_id}")

        # Validate key
        if not args.encryption_key or not args.encryption_key.strip():
            logger.error("Encryption key is required")
            return 1

        try:
            EncryptCommand._encrypt_tokens(
                args.input_path,
                args.output_path,
                args.input_type,
                output_type,
                args.encryption_key,
                ring_id,
            )
            logger.info("Token encryption completed successfully")
            return 0
        except Exception as e:
            logger.error(f"Error during token encryption: {e}", exc_info=True)
            return 1

    @staticmethod
    def _encrypt_tokens(
        input_path: str,
        output_path: str,
        input_type: str,
        output_type: str,
        encryption_key: str,
        ring_id: str,
    ):
        """Encrypt tokens from input file."""
        try:
            encryptor = EncryptTokenTransformer(encryption_key)
            jwe_formatters: dict[str, JweMatchTokenFormatter] = {}
            row_counter = 0
            encrypted_counter = 0
            error_counter = 0

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

            logger.info(f"Processed a total of {row_counter:,} tokens")
            logger.info(f"Successfully encrypted {encrypted_counter:,} tokens")
            if error_counter > 0:
                logger.warning(f"Failed to encrypt {error_counter:,} tokens")

        except Exception as e:
            logger.error(f"Error during token encryption: {e}", exc_info=True)
            raise

    @staticmethod
    def _wrap_as_v1_token(
        encrypted_token: str,
        row: dict,
        encryption_key: str,
        ring_id: str,
        jwe_formatters: dict[str, JweMatchTokenFormatter],
    ) -> str:
        rule_id = row.get(TokenConstants.RULE_ID)
        if not rule_id:
            return encrypted_token

        formatter = jwe_formatters.get(rule_id)
        if formatter is None:
            formatter = JweMatchTokenFormatter(encryption_key, ring_id, rule_id, "truveta.opentoken")
            jwe_formatters[rule_id] = formatter

        return formatter.transform(encrypted_token)

    @staticmethod
    def _create_token_reader(path: str, file_type: str):
        """Create a TokenReader based on file type."""
        file_type_lower = file_type.lower()
        if file_type_lower == EncryptCommand.TYPE_CSV:
            return TokenCSVReader(path)
        elif file_type_lower == EncryptCommand.TYPE_PARQUET:
            return TokenParquetReader(path)
        else:
            raise ValueError(f"Unsupported input type: {file_type}")

    @staticmethod
    def _create_token_writer(path: str, file_type: str):
        """Create a TokenWriter based on file type."""
        file_type_lower = file_type.lower()
        if file_type_lower == EncryptCommand.TYPE_CSV:
            return TokenCSVWriter(path)
        elif file_type_lower == EncryptCommand.TYPE_PARQUET:
            return TokenParquetWriter(path)
        else:
            raise ValueError(f"Unsupported output type: {file_type}")
