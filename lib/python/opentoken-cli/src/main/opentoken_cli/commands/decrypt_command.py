"""
Copyright (c) Truveta. All rights reserved.
"""

import logging

from opentoken.tokentransformer.decrypt_token_transformer import DecryptTokenTransformer
from opentoken_cli.io.csv.token_csv_reader import TokenCSVReader
from opentoken_cli.io.csv.token_csv_writer import TokenCSVWriter
from opentoken_cli.io.parquet.token_parquet_reader import TokenParquetReader
from opentoken_cli.io.parquet.token_parquet_writer import TokenParquetWriter
from opentoken_cli.processor.token_transformation_processor import TokenTransformationProcessor
from opentoken_cli.util import StringMaskingUtil

logger = logging.getLogger(__name__)


class DecryptCommand:
    """
    Decrypt command - decrypts encrypted tokens.
    """

    TYPE_CSV = "csv"
    TYPE_PARQUET = "parquet"

    @staticmethod
    def register_subcommand(subparsers):
        """Register the decrypt subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "decrypt",
            help="Decrypt encrypted tokens using encryption key",
            description="Decrypt encrypted tokens using encryption key",
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
            help="Input file path with encrypted tokens",
        )

        parser.add_argument(
            "-o",
            "--output",
            required=True,
            dest="output_path",
            help="Output file path for decrypted tokens",
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
            help="Encryption key for token decryption",
        )

        parser.set_defaults(func=DecryptCommand.execute)

    @staticmethod
    def execute(args):
        """Execute the decrypt command."""
        logger.info("Running decrypt command")

        # Default output type to input type if not specified
        output_type = args.output_type if args.output_type else args.input_type

        # Log parameters (mask key)
        logger.info(f"Input: {args.input_path} ({args.input_type})")
        logger.info(f"Output: {args.output_path} ({output_type})")
        logger.info(f"Encryption Key: {StringMaskingUtil.mask_string(args.encryption_key)}")

        # Validate key
        if not args.encryption_key or not args.encryption_key.strip():
            logger.error("Encryption key is required")
            return 1

        try:
            DecryptCommand._decrypt_tokens(
                args.input_path,
                args.output_path,
                args.input_type,
                output_type,
                args.encryption_key,
            )
            logger.info("Token decryption completed successfully")
            return 0
        except Exception as e:
            logger.error(f"Error during token decryption: {e}", exc_info=True)
            return 1

    @staticmethod
    def _decrypt_tokens(
        input_path: str,
        output_path: str,
        input_type: str,
        output_type: str,
        encryption_key: str,
    ):
        """Decrypt tokens from input file."""
        try:
            decryptor = DecryptTokenTransformer(encryption_key)

            with DecryptCommand._create_token_reader(
                input_path, input_type
            ) as reader, DecryptCommand._create_token_writer(output_path, output_type) as writer:
                TokenTransformationProcessor.process(reader, writer, decryptor, "decrypted")

        except Exception as e:
            logger.error(f"Error during token decryption: {e}", exc_info=True)
            raise

    @staticmethod
    def _create_token_reader(path: str, file_type: str):
        """Create a TokenReader based on file type."""
        file_type_lower = file_type.lower()
        if file_type_lower == DecryptCommand.TYPE_CSV:
            return TokenCSVReader(path)
        elif file_type_lower == DecryptCommand.TYPE_PARQUET:
            return TokenParquetReader(path)
        else:
            raise ValueError(f"Unsupported input type: {file_type}")

    @staticmethod
    def _create_token_writer(path: str, file_type: str):
        """Create a TokenWriter based on file type."""
        file_type_lower = file_type.lower()
        if file_type_lower == DecryptCommand.TYPE_CSV:
            return TokenCSVWriter(path)
        elif file_type_lower == DecryptCommand.TYPE_PARQUET:
            return TokenParquetWriter(path)
        else:
            raise ValueError(f"Unsupported output type: {file_type}")
