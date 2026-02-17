"""
Copyright (c) Truveta. All rights reserved.
"""

import logging
from typing import List

from opentoken.metadata import Metadata
from opentoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from opentoken.tokentransformer.token_transformer import TokenTransformer
from opentoken_cli.io.csv.person_attributes_csv_reader import PersonAttributesCSVReader
from opentoken_cli.io.csv.person_attributes_csv_writer import PersonAttributesCSVWriter
from opentoken_cli.util import mask_string
from opentoken_cli.io.json.metadata_json_writer import MetadataJsonWriter
from opentoken_cli.io.parquet.person_attributes_parquet_reader import PersonAttributesParquetReader
from opentoken_cli.io.parquet.person_attributes_parquet_writer import PersonAttributesParquetWriter
from opentoken_cli.processor.person_attributes_processor import PersonAttributesProcessor

logger = logging.getLogger(__name__)


class TokenizeCommand:
    """
    Tokenize command - generates hashed tokens from person attributes.
    This is hash-only mode without encryption.
    """

    TYPE_CSV = "csv"
    TYPE_PARQUET = "parquet"

    @staticmethod
    def register_subcommand(subparsers):
        """Register the tokenize subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "tokenize",
            help="Generate hashed tokens from person attributes (hash-only mode)",
            description="Generate hashed tokens from person attributes without encryption",
            add_help=False,  # Disable automatic -h for help to allow -h for hashingsecret
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
            "-h",
            "--hashingsecret",
            required=True,
            dest="hashing_secret",
            help="Hashing secret for token generation",
        )

        parser.set_defaults(func=TokenizeCommand.execute)

    @staticmethod
    def execute(args):
        """Execute the tokenize command."""
        logger.info("Running tokenize command (hash-only mode)")

        # Default output type to input type if not specified
        output_type = args.output_type if args.output_type else args.input_type

        # Log parameters (mask secret)
        logger.info(f"Input: {args.input_path} ({args.input_type})")
        logger.info(f"Output: {args.output_path} ({output_type})")
        logger.info(f"Hashing Secret: {TokenizeCommand._mask_string(args.hashing_secret)}")

        # Validate secret
        if not args.hashing_secret or not args.hashing_secret.strip():
            logger.error("Hashing secret is required")
            return 1

        try:
            TokenizeCommand._process_tokens(
                args.input_path,
                args.output_path,
                args.input_type,
                output_type,
                args.hashing_secret,
            )
            logger.info("Token generation completed successfully")
            return 0
        except Exception as e:
            logger.error(f"Error during token generation: {e}", exc_info=True)
            return 1

    @staticmethod
    def _process_tokens(
        input_path: str,
        output_path: str,
        input_type: str,
        output_type: str,
        hashing_secret: str,
    ):
        """Process tokens from person attributes."""
        token_transformer_list: List[TokenTransformer] = []

        try:
            # Add only hash transformer (no encryption in tokenize mode)
            token_transformer_list.append(HashTokenTransformer(hashing_secret))
        except Exception as e:
            logger.error("Error initializing hash transformer", exc_info=e)
            raise RuntimeError("Failed to initialize transformer") from e

        try:
            with TokenizeCommand._create_reader(
                input_path, input_type
            ) as reader, TokenizeCommand._create_writer(output_path, output_type) as writer:

                # Create metadata
                metadata = Metadata()
                metadata_map = metadata.initialize()
                metadata.add_hashed_secret(Metadata.HASHING_SECRET_HASH, hashing_secret)

                # Process data
                PersonAttributesProcessor.process(reader, writer, token_transformer_list, metadata_map)

                # Write metadata
                metadata_writer = MetadataJsonWriter(output_path)
                metadata_writer.write(metadata_map)

        except Exception as e:
            logger.error("Error processing tokens", exc_info=e)
            raise

    @staticmethod
    def _create_reader(path: str, file_type: str):
        """Create a PersonAttributesReader based on file type."""
        file_type_lower = file_type.lower()
        if file_type_lower == TokenizeCommand.TYPE_CSV:
            return PersonAttributesCSVReader(path)
        elif file_type_lower == TokenizeCommand.TYPE_PARQUET:
            return PersonAttributesParquetReader(path)
        else:
            raise ValueError(f"Unsupported input type: {file_type}")

    @staticmethod
    def _create_writer(path: str, file_type: str):
        """Create a PersonAttributesWriter based on file type."""
        file_type_lower = file_type.lower()
        if file_type_lower == TokenizeCommand.TYPE_CSV:
            return PersonAttributesCSVWriter(path)
        elif file_type_lower == TokenizeCommand.TYPE_PARQUET:
            return PersonAttributesParquetWriter(path)
        else:
            raise ValueError(f"Unsupported output type: {file_type}")

    @staticmethod
    def _mask_string(input_str: str) -> str:
        """Mask a string for logging purposes."""
        return mask_string(input_str)
