# SPDX-License-Identifier: MIT

import logging
import uuid
from typing import List

from openlinktoken_core_ai.tokens.ml1_inference_config import ML1InferenceConfig

from openlinktoken.metadata import Metadata
from openlinktoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from openlinktoken.tokentransformer.token_transformer import TokenTransformer
from openlinktoken_cli.io.csv.person_attributes_csv_reader import PersonAttributesCSVReader
from openlinktoken_cli.io.csv.person_attributes_csv_writer import PersonAttributesCSVWriter
from openlinktoken_cli.io.json.metadata_json_writer import MetadataJsonWriter
from openlinktoken_cli.io.parquet.person_attributes_parquet_reader import PersonAttributesParquetReader
from openlinktoken_cli.io.parquet.person_attributes_parquet_writer import PersonAttributesParquetWriter
from openlinktoken_cli.processor.person_attributes_processor import PersonAttributesProcessor
from openlinktoken_cli.util.exchange_config import derive_transport_encryption_key, resolve_exchange_config

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

        parser.add_argument(
            "--disable-ml1",
            action="store_true",
            dest="disable_ml1",
            help="Disable ML1 ONNX inference token generation",
        )

        parser.add_argument(
            "--ml1-model-path",
            dest="ml1_model_path",
            default=ML1InferenceConfig.DEFAULT_MODEL_PATH,
            help=f"Path to ML1 ONNX model (default: {ML1InferenceConfig.DEFAULT_MODEL_PATH})",
        )

        parser.add_argument(
            "--ml1-tokenizer-path",
            dest="ml1_tokenizer_path",
            default=ML1InferenceConfig.DEFAULT_TOKENIZER_PATH,
            help=f"Path to ML1 tokenizer JSON (default: {ML1InferenceConfig.DEFAULT_TOKENIZER_PATH})",
        )

        parser.add_argument(
            "--ml1-max-seq-length",
            "--ml1-max-sequence-length",
            dest="ml1_max_sequence_length",
            type=int,
            default=ML1InferenceConfig.DEFAULT_MAX_SEQUENCE_LENGTH,
            help="Maximum ML1 tokenizer sequence length (default: 128)",
        )

        parser.add_argument(
            "--ml1-batch-size",
            dest="ml1_batch_size",
            type=int,
            default=ML1InferenceConfig.DEFAULT_BATCH_SIZE,
            help="ML1 ONNX inference batch size (default: 64)",
        )

        parser.add_argument(
            "--ml1-num-threads",
            dest="ml1_num_threads",
            type=int,
            default=0,
            help="ORT intra/inter-op thread count for ML1 inference (0 = auto-detect, default: 0)",
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
        logger.info(f"Ring ID: {ring_id}")
        if hash_record_ids:
            logger.info("Record ID hashing enabled: RecordIds will be SHA-256 hashed in output")

        ml1_enabled = not getattr(args, "disable_ml1", False)
        ML1InferenceConfig.configure(
            enable_ml1=ml1_enabled,
            configured_model_path=getattr(args, "ml1_model_path", ML1InferenceConfig.DEFAULT_MODEL_PATH),
            configured_tokenizer_path=getattr(args, "ml1_tokenizer_path", ML1InferenceConfig.DEFAULT_TOKENIZER_PATH),
            configured_max_sequence_length=getattr(
                args, "ml1_max_sequence_length", ML1InferenceConfig.DEFAULT_MAX_SEQUENCE_LENGTH
            ),
            configured_batch_size=getattr(args, "ml1_batch_size", ML1InferenceConfig.DEFAULT_BATCH_SIZE),
            configured_num_threads=getattr(args, "ml1_num_threads", 0),
        )
        num_threads = getattr(args, "ml1_num_threads", 0)
        logger.info(
            "ML1 ONNX inference: enabled=%s, modelPath=%s, tokenizerPath=%s, maxSequenceLength=%s, batchSize=%s, numThreads=%s",
            ml1_enabled,
            getattr(args, "ml1_model_path", ML1InferenceConfig.DEFAULT_MODEL_PATH),
            getattr(args, "ml1_tokenizer_path", ML1InferenceConfig.DEFAULT_TOKENIZER_PATH),
            getattr(args, "ml1_max_sequence_length", ML1InferenceConfig.DEFAULT_MAX_SEQUENCE_LENGTH),
            getattr(args, "ml1_batch_size", ML1InferenceConfig.DEFAULT_BATCH_SIZE),
            num_threads if num_threads > 0 else "auto",
        )

        try:
            exchange = resolve_exchange_config(
                args.exchange_config,
                private_key_path=args.private_key,
                private_key_env=args.private_key_env,
            )
            encryption_key = derive_transport_encryption_key(exchange)
            logger.info(f"Exchange config: {exchange.path}")
            PackageCommand._process_tokens(
                args.input_path,
                args.output_path,
                args.input_type,
                output_type,
                exchange.hashing_secret,
                encryption_key,
                ring_id,
                hash_record_ids,
            )
            logger.info("Token generation and encryption completed successfully")
            return 0
        except Exception as e:
            logger.error(f"Error during token processing: {e}")
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
