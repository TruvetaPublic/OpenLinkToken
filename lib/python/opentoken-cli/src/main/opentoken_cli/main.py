"""
Copyright (c) Truveta. All rights reserved.
"""

import logging
import sys
from typing import List

from opentoken_cli.command_line_arguments import CommandLineArguments
from opentoken_cli.io.csv.person_attributes_csv_reader import PersonAttributesCSVReader
from opentoken_cli.io.csv.person_attributes_csv_writer import PersonAttributesCSVWriter
from opentoken_cli.io.csv.token_csv_reader import TokenCSVReader
from opentoken_cli.io.csv.token_csv_writer import TokenCSVWriter
from opentoken_cli.io.json.metadata_json_writer import MetadataJsonWriter
from opentoken_cli.io.parquet.person_attributes_parquet_reader import PersonAttributesParquetReader
from opentoken_cli.io.parquet.person_attributes_parquet_writer import PersonAttributesParquetWriter
from opentoken_cli.io.parquet.token_parquet_reader import TokenParquetReader
from opentoken_cli.io.parquet.token_parquet_writer import TokenParquetWriter
from opentoken_cli.processor.person_attributes_processor import PersonAttributesProcessor
from opentoken_cli.processor.token_decryption_processor import TokenDecryptionProcessor
from opentoken.metadata import Metadata
from opentoken.tokentransformer.decrypt_token_transformer import DecryptTokenTransformer
from opentoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from opentoken.tokentransformer.hash_token_transformer import HashTokenTransformer
from opentoken.tokentransformer.token_transformer import TokenTransformer


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the OpenToken application."""
    command_line_arguments = _load_command_line_arguments(sys.argv[1:])
    hashing_secret = command_line_arguments.hashing_secret
    encryption_key = command_line_arguments.encryption_key
    input_path = command_line_arguments.input_path
    input_type = command_line_arguments.input_type
    output_path = command_line_arguments.output_path
    output_type = command_line_arguments.output_type if command_line_arguments.output_type else input_type
    decrypt_mode = command_line_arguments.decrypt
    hash_only_mode = command_line_arguments.hash_only
    ring_id = command_line_arguments.ring_id

    logger.info(f"Decrypt Mode: {decrypt_mode}")
    logger.info(f"Hash-Only Mode: {hash_only_mode}")
    logger.info(f"Ring ID: {ring_id}")
    logger.info(f"Hashing Secret: {_mask_string(hashing_secret)}")
    logger.info(f"Encryption Key: {_mask_string(encryption_key)}")
    logger.info(f"Input Path: {input_path}")
    logger.info(f"Input Type: {input_type}")
    logger.info(f"Output Path: {output_path}")
    logger.info(f"Output Type: {output_type}")

    # Validate input and output types for both modes
    if input_type not in [CommandLineArguments.TYPE_CSV, CommandLineArguments.TYPE_PARQUET]:
        logger.error("Only csv and parquet input types are supported!")
        return
    if output_type not in [CommandLineArguments.TYPE_CSV, CommandLineArguments.TYPE_PARQUET]:
        logger.error("Only csv and parquet output types are supported!")
        return

    # Process based on mode
    if decrypt_mode:
        # Decrypt mode - process encrypted tokens
        if not encryption_key or not encryption_key.strip():
            logger.error("Encryption key must be specified for decryption")
            return

        _decrypt_tokens(input_path, output_path, input_type, output_type, encryption_key)
        logger.info("Token decryption completed successfully.")
    else:
        # Token generation mode - validate and process person attributes
        # Hashing secret is always required
        if not hashing_secret or not hashing_secret.strip():
            logger.error("Hashing secret must be specified")
            return
        
        # Encryption key is only required when not in hash-only mode
        if not hash_only_mode and (not encryption_key or not encryption_key.strip()):
            logger.error("Encryption key must be specified (or use --hash-only to skip encryption)")
            return

        _process_tokens(input_path, output_path, input_type, output_type, hashing_secret, encryption_key, hash_only_mode, ring_id)


def _create_person_attributes_reader(input_path: str, input_type: str):
    """Create a PersonAttributesReader based on input type."""
    input_type_lower = input_type.lower()
    if input_type_lower == CommandLineArguments.TYPE_CSV:
        return PersonAttributesCSVReader(input_path)
    elif input_type_lower == CommandLineArguments.TYPE_PARQUET:
        return PersonAttributesParquetReader(input_path)
    else:
        raise ValueError(f"Unsupported input type: {input_type}")


def _create_person_attributes_writer(output_path: str, output_type: str):
    """Create a PersonAttributesWriter based on output type."""
    output_type_lower = output_type.lower()
    if output_type_lower == CommandLineArguments.TYPE_CSV:
        return PersonAttributesCSVWriter(output_path)
    elif output_type_lower == CommandLineArguments.TYPE_PARQUET:
        return PersonAttributesParquetWriter(output_path)
    else:
        raise ValueError(f"Unsupported output type: {output_type}")


def _create_token_reader(input_path: str, input_type: str):
    """Create a TokenReader based on input type."""
    input_type_lower = input_type.lower()
    if input_type_lower == CommandLineArguments.TYPE_CSV:
        return TokenCSVReader(input_path)
    elif input_type_lower == CommandLineArguments.TYPE_PARQUET:
        return TokenParquetReader(input_path)
    else:
        raise ValueError(f"Unsupported input type: {input_type}")


def _create_token_writer(output_path: str, output_type: str):
    """Create a TokenWriter based on output type."""
    output_type_lower = output_type.lower()
    if output_type_lower == CommandLineArguments.TYPE_CSV:
        return TokenCSVWriter(output_path)
    elif output_type_lower == CommandLineArguments.TYPE_PARQUET:
        return TokenParquetWriter(output_path)
    else:
        raise ValueError(f"Unsupported output type: {output_type}")


def _load_command_line_arguments(args: list) -> CommandLineArguments:
    """Load and parse command line arguments."""
    logger.debug(f"Processing command line arguments: {' | '.join(args)}")
    command_line_arguments = CommandLineArguments.parse_args(args)
    logger.info("Command line arguments processed.")
    return command_line_arguments


def _mask_string(input_str: str) -> str:
    """Mask a string for logging purposes, showing only first 3 characters."""
    if input_str is None or len(input_str) <= 3:
        return input_str
    return input_str[:3] + "*" * (len(input_str) - 3)


def _process_tokens(input_path: str, output_path: str, input_type: str, output_type: str,
                    hashing_secret: str, encryption_key: str, hash_only_mode: bool, ring_id: str):
    """
    Process tokens from person attributes and write to output file.
    
    Args:
        input_path: Path to input file with person attributes.
        output_path: Path to output file for tokens.
        input_type: Type of input file (csv or parquet).
        output_type: Type of output file (csv or parquet).
        hashing_secret: Secret for hashing tokens.
        encryption_key: Key for encrypting tokens (not used in hash-only mode).
        hash_only_mode: If True, skip encryption step.
        ring_id: Ring identifier for JWE token wrapping.
    """
    token_transformer_list: List[TokenTransformer] = []
    try:
        # Always add hash transformer
        token_transformer_list.append(HashTokenTransformer(hashing_secret))
        
        # Only add encryption transformer if not in hash-only mode
        if not hash_only_mode:
            token_transformer_list.append(EncryptTokenTransformer(encryption_key))
    except Exception as e:
        logger.error("Error in initializing the transformer. Execution halted.", exc_info=e)
        return

    try:
        with _create_person_attributes_reader(input_path, input_type) as reader, \
             _create_person_attributes_writer(output_path, output_type) as writer:

            # Create initial metadata with system information
            metadata = Metadata()
            metadata_map = metadata.initialize()

            # Set hashing secret
            metadata.add_hashed_secret(Metadata.HASHING_SECRET_HASH, hashing_secret)
            
            # Set encryption secret if applicable
            if not hash_only_mode:
                metadata.add_hashed_secret(Metadata.ENCRYPTION_SECRET_HASH, encryption_key)

            # Process data and get updated metadata
            # Pass encryption key and ring ID for JWE wrapping (only if not in hash-only mode)
            PersonAttributesProcessor.process(
                reader, writer, token_transformer_list, metadata_map,
                None if hash_only_mode else encryption_key, ring_id
            )

            # Write the metadata to file
            metadata_writer = MetadataJsonWriter(output_path)
            metadata_writer.write(metadata_map)

    except Exception as e:
        logger.error("Error in processing the input file. Execution halted.", exc_info=e)


def _decrypt_tokens(input_path: str, output_path: str, input_type: str, output_type: str, encryption_key: str):
    """
    Decrypt tokens from input file and write to output file.
    
    Args:
        input_path: Path to input file with encrypted tokens.
        output_path: Path to output file for decrypted tokens.
        input_type: Type of input file (csv or parquet).
        output_type: Type of output file (csv or parquet).
        encryption_key: Encryption key for decryption.
    """
    try:
        decryptor = DecryptTokenTransformer(encryption_key)
        
        with _create_token_reader(input_path, input_type) as reader, \
             _create_token_writer(output_path, output_type) as writer:
            TokenDecryptionProcessor.process_with_key(reader, writer, decryptor, encryption_key)
                
    except Exception as e:
        logger.error(f"Error during token decryption: {e}")
        raise

if __name__ == "__main__":
    main()
