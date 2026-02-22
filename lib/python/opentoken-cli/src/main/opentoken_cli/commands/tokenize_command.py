"""
Copyright (c) Truveta. All rights reserved.
"""

import logging
from typing import List

from opentoken.metadata import Metadata
from opentoken.tokens.tokenizer.passthrough_tokenizer import PassthroughTokenizer
from opentoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from opentoken.tokentransformer.token_transformer import TokenTransformer
from opentoken_cli.io.csv.person_attributes_csv_reader import PersonAttributesCSVReader
from opentoken_cli.io.csv.person_attributes_csv_writer import PersonAttributesCSVWriter
from opentoken_cli.io.json.metadata_json_writer import MetadataJsonWriter
from opentoken_cli.io.parquet.person_attributes_parquet_reader import (
    PersonAttributesParquetReader,
)
from opentoken_cli.io.parquet.person_attributes_parquet_writer import (
    PersonAttributesParquetWriter,
)
from opentoken_cli.processor.person_attributes_processor import (
    PersonAttributesProcessor,
)
from opentoken_cli.util import StringMaskingUtil

logger = logging.getLogger(__name__)


class TokenizeCommand:
    """
    Tokenize command - generates tokens from person attributes.

    Normal mode (default): applies SHA-256 then HMAC-SHA256 hashing on the token
    signature, producing opaque base64 tokens. ``--hashingsecret`` is required.

    Demo mode (``--demo-mode``): skips all hashing so tokens are the raw
    pipe-separated attribute signature strings. No secret is needed, making it easy
    to explore the output without managing secrets. Demo-mode output is
    **not** suitable for production or cross-organisation exchange.
    """

    TYPE_CSV = "csv"
    TYPE_PARQUET = "parquet"

    @staticmethod
    def register_subcommand(subparsers):
        """Register the tokenize subcommand with the argument parser."""
        parser = subparsers.add_parser(
            "tokenize",
            help="Generate tokens from person attributes (normal mode: HMAC-SHA256; demo mode: plain signatures)",
            description=(
                "Generate tokens from person attributes.\n\n"
                "Normal mode: tokens are HMAC-SHA256 hashed (--hashingsecret required).\n"
                "Demo mode (--demo-mode): tokens are plain attribute signature strings; no secret needed."
            ),
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
            "--demo-mode",
            action="store_true",
            default=False,
            dest="demo_mode",
            help=(
                "Enable demo mode: output plain attribute signature strings without any hashing. "
                "--hashingsecret is not required in this mode. "
                "Demo output is NOT suitable for production or cross-organisation exchange."
            ),
        )

        # Optional in demo mode; required at runtime in normal mode
        parser.add_argument(
            "-h",
            "--hashingsecret",
            required=False,
            dest="hashing_secret",
            help="Hashing secret for HMAC-SHA256 token generation (required in normal mode, ignored in demo mode)",
        )

        parser.set_defaults(func=TokenizeCommand.execute)

    @staticmethod
    def execute(args):
        """Execute the tokenize command."""
        demo_mode = getattr(args, "demo_mode", False)

        if demo_mode:
            logger.warning(
                "Running in DEMO MODE - tokens are plain attribute signature strings, not HMAC-hashed. "
                "Do not use demo-mode output in production or share it externally."
            )
        else:
            logger.info("Running tokenize command (normal mode)")

        # Default output type to input type if not specified
        output_type = args.output_type if args.output_type else args.input_type

        logger.info(f"Input: {args.input_path} ({args.input_type})")
        logger.info(f"Output: {args.output_path} ({output_type})")
        if not demo_mode:
            logger.info(
                f"Hashing Secret: {StringMaskingUtil.mask_string(args.hashing_secret)}"
            )

        # --hashingsecret is required in normal mode only
        if not demo_mode:
            if not args.hashing_secret or not args.hashing_secret.strip():
                logger.error(
                    "--hashingsecret is required in normal mode. Use --demo-mode to skip hashing."
                )
                return 1

        try:
            if demo_mode:
                TokenizeCommand._process_tokens_demo(
                    args.input_path,
                    args.output_path,
                    args.input_type,
                    output_type,
                )
            else:
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
        """Process tokens in normal mode using SHA-256 + HMAC-SHA256."""
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
            ) as reader, TokenizeCommand._create_writer(
                output_path, output_type
            ) as writer:

                metadata = Metadata()
                metadata_map = metadata.initialize()
                # Only record the hashing-secret hash in normal mode
                metadata.add_hashed_secret(Metadata.HASHING_SECRET_HASH, hashing_secret)

                PersonAttributesProcessor.process(
                    reader, writer, token_transformer_list, metadata_map
                )

                MetadataJsonWriter(output_path).write(metadata_map)

        except Exception as e:
            logger.error("Error processing tokens", exc_info=e)
            raise

    @staticmethod
    def _process_tokens_demo(
        input_path: str,
        output_path: str,
        input_type: str,
        output_type: str,
    ):
        """Process tokens in demo mode using PassthroughTokenizer (no hashing)."""
        try:
            with TokenizeCommand._create_reader(
                input_path, input_type
            ) as reader, TokenizeCommand._create_writer(
                output_path, output_type
            ) as writer:

                metadata = Metadata()
                metadata_map = metadata.initialize()
                # Deliberately omit add_hashed_secret — no secret used in demo mode

                PersonAttributesProcessor.process_with_tokenizer(
                    reader, writer, PassthroughTokenizer([]), metadata_map
                )

                MetadataJsonWriter(output_path).write(metadata_map)

        except Exception as e:
            logger.error("Error processing tokens in demo mode", exc_info=e)
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
