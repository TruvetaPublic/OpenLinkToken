"""
Copyright (c) Truveta. All rights reserved.
"""

import logging
import uuid
from typing import List

from opentoken.metadata import Metadata
from opentoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from opentoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from opentoken.tokentransformer.token_transformer import TokenTransformer
from opentoken_cli.io.csv.person_attributes_csv_reader import PersonAttributesCSVReader
from opentoken_cli.io.csv.person_attributes_csv_writer import PersonAttributesCSVWriter
from opentoken_cli.io.json.metadata_json_writer import MetadataJsonWriter
from opentoken_cli.io.parquet.person_attributes_parquet_reader import PersonAttributesParquetReader
from opentoken_cli.io.parquet.person_attributes_parquet_writer import PersonAttributesParquetWriter
from opentoken_cli.processor.person_attributes_processor import PersonAttributesProcessor
from opentoken_cli.util import StringMaskingUtil

logger = logging.getLogger(__name__)


class PackageCommand:
    """
    Package command - combines tokenize and encrypt in one command.
    This is the default workflow: hash + encrypt.
    """

    TYPE_CSV = "csv"
    TYPE_PARQUET = "parquet"

    @staticmethod
    def register_subcommand(subparsers):
        """Register the package subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "package",
            help="Generate and encrypt tokens in one step (tokenize + encrypt)",
            description="Generate and encrypt tokens in one step",
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
        logger.info("Running package command (tokenize + encrypt)")

        # Default output type to input type if not specified
        output_type = args.output_type if args.output_type else args.input_type
        ring_id = args.ring_id if args.ring_id and args.ring_id.strip() else str(uuid.uuid4())
        hash_record_ids = getattr(args, "hash_record_ids", False)

        # Log parameters (mask secrets)
        logger.info(f"Input: {args.input_path} ({args.input_type})")
        logger.info(f"Output: {args.output_path} ({output_type})")
        logger.info(f"Hashing Secret: {StringMaskingUtil.mask_string(args.hashing_secret)}")
        logger.info(f"Encryption Key: {StringMaskingUtil.mask_string(args.encryption_key)}")
        logger.info(f"Ring ID: {ring_id}")
        if hash_record_ids:
            logger.info("Record ID hashing enabled: RecordIds will be SHA-256 hashed in output")

        # Validate secrets
        if not args.hashing_secret or not args.hashing_secret.strip():
            logger.error("Hashing secret is required")
            return 1
        if not args.encryption_key or not args.encryption_key.strip():
            logger.error("Encryption key is required")
            return 1

        try:
            PackageCommand._process_tokens(
                args.input_path,
                args.output_path,
                args.input_type,
                output_type,
                args.hashing_secret,
                args.encryption_key,
                ring_id,
                hash_record_ids,
            )
            logger.info("Token generation and encryption completed successfully")
            return 0
        except Exception as e:
            logger.error(f"Error during token processing: {e}", exc_info=True)
            return 1

    @staticmethod
    def _process_tokens(
        input_path: str,
        output_path: str,
        input_type: str,
        output_type: str,
        hashing_secret: str,
        encryption_key: str,
        ring_id: str,
        hash_record_ids: bool = False,
    ):
        """Process tokens from person attributes."""
        token_transformer_list: List[TokenTransformer] = []

        try:
            # Add both hash and encryption transformers
            token_transformer_list.append(HashTokenTransformer(hashing_secret))
            token_transformer_list.append(EncryptTokenTransformer(encryption_key))
        except Exception as e:
            logger.error("Error initializing transformers", exc_info=e)
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
                PersonAttributesProcessor.process(
                    reader,
                    writer,
                    token_transformer_list,
                    metadata_map,
                    encryption_key,
                    ring_id,
                    hash_record_ids,
                )

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
        if file_type_lower == PackageCommand.TYPE_CSV:
            return PersonAttributesCSVReader(path)
        elif file_type_lower == PackageCommand.TYPE_PARQUET:
            return PersonAttributesParquetReader(path)
        else:
            raise ValueError(f"Unsupported input type: {file_type}")

    @staticmethod
    def _create_writer(path: str, file_type: str):
        """Create a PersonAttributesWriter based on file type."""
        file_type_lower = file_type.lower()
        if file_type_lower == PackageCommand.TYPE_CSV:
            return PersonAttributesCSVWriter(path)
        elif file_type_lower == PackageCommand.TYPE_PARQUET:
            return PersonAttributesParquetWriter(path)
        else:
            raise ValueError(f"Unsupported output type: {file_type}")
