"""
Copyright (c) Truveta. All rights reserved.
"""

import logging
import uuid
from typing import Dict, List, Type, Any, Set

from opentoken.attributes.attribute import Attribute
from opentoken.attributes.general.record_id_attribute import RecordIdAttribute
from opentoken_cli.io.person_attributes_reader import PersonAttributesReader
from opentoken_cli.io.person_attributes_writer import PersonAttributesWriter
from opentoken_cli.processor.token_constants import TokenConstants
from opentoken.tokens.token_definition import TokenDefinition
from opentoken.tokens.token_generator import TokenGenerator
from opentoken.tokens.token_generator_result import TokenGeneratorResult
from opentoken.tokentransformer.jwe_match_token_formatter import JweMatchTokenFormatter
from opentoken.tokentransformer.token_transformer import TokenTransformer


logger = logging.getLogger(__name__)


class PersonAttributesProcessor:
    """
    Process all person attributes.

    This class is used to read person attributes from input source,
    generate tokens for each person record and write the tokens back
    to the output data source.
    """

    TOTAL_ROWS = "TotalRows"
    TOTAL_ROWS_WITH_INVALID_ATTRIBUTES = "TotalRowsWithInvalidAttributes"
    INVALID_ATTRIBUTES_BY_TYPE = "InvalidAttributesByType"
    BLANK_TOKENS_BY_RULE = "BlankTokensByRule"

    def __init__(self):
        """Private constructor to prevent instantiation."""

    @staticmethod
    def process(reader: PersonAttributesReader,
                writer: PersonAttributesWriter,
                token_transformer_list: List[TokenTransformer],
                metadata_map: Dict[str, Any] = None,
                encryption_key: str = None,
                ring_id: str = None) -> None:
        """
        Read person attributes from the input data source, generate tokens, and
        write the result back to the output data source. The tokens can be optionally
        transformed before writing and wrapped in JWE format if ring ID is provided.

        Args:
            reader: The reader initialized with the input data source.
            writer: The writer initialized with the output data source.
            token_transformer_list: A list of token transformers.
            metadata_map: Optional metadata map to update with processing statistics.
            encryption_key: Optional encryption key for JWE wrapping (None to skip JWE).
            ring_id: Optional ring ID for JWE wrapping (None to skip JWE).
        """
        # TokenGenerator code
        token_definition = TokenDefinition()
        token_generator = TokenGenerator.from_transformers(token_definition, token_transformer_list)

        row_counter = 0
        invalid_attribute_count: Dict[str, int] = PersonAttributesProcessor._initialize_invalid_attribute_count(token_definition)
        blank_tokens_by_rule_count: Dict[str, int] = PersonAttributesProcessor._initialize_blank_tokens_by_rule_count(token_definition)

        # Cache JWE formatters if encryption is enabled
        jwe_formatters: Dict[str, JweMatchTokenFormatter] = {}
        if encryption_key and ring_id:
            for token_id in token_definition.get_token_identifiers():
                try:
                    jwe_formatters[token_id] = JweMatchTokenFormatter(
                        encryption_key, ring_id, token_id, "truveta.opentoken"
                    )
                except Exception as e:
                    error_msg = f"Failed to initialize JWE formatter for token rule {token_id}"
                    logger.error(error_msg, exc_info=True)
                    raise RuntimeError(error_msg) from e

        try:
            for row in reader:
                row_counter += 1

                token_generator_result = token_generator.get_all_tokens(row)
                logger.debug(f"Tokens: {token_generator_result.tokens}")

                PersonAttributesProcessor._keep_track_of_invalid_attributes(
                    token_generator_result, row_counter, invalid_attribute_count
                )

                PersonAttributesProcessor._keep_track_of_blank_tokens(
                    token_generator_result, row_counter, blank_tokens_by_rule_count
                )

                PersonAttributesProcessor._write_tokens(
                    writer, row, row_counter, token_generator_result, encryption_key, ring_id, jwe_formatters
                )

                if row_counter % 10000 == 0:
                    logger.info(f"Processed {row_counter:,} records")

        except Exception as e:
            logger.error(f"Error processing records: {e}", exc_info=True)
            raise

        logger.info(f"Processed a total of {row_counter:,} records")

        # Log invalid attribute statistics in alphabetical order
        for attribute_name, count in sorted(invalid_attribute_count.items()):
            logger.info(f"Total invalid Attribute count for [{attribute_name}]: {count:,}")

        total_invalid_records = sum(invalid_attribute_count.values())
        logger.info(f"Total number of records with invalid attributes: {total_invalid_records:,}")

        # Log blank token statistics in alphabetical order
        for rule_id, count in sorted(blank_tokens_by_rule_count.items()):
            logger.info(f"Total blank tokens for rule [{rule_id}]: {count:,}")

        total_blank_tokens = sum(blank_tokens_by_rule_count.values())
        logger.info(f"Total blank tokens generated: {total_blank_tokens:,}")

        # Update metadata if provided
        if metadata_map is not None:
            metadata_map[PersonAttributesProcessor.TOTAL_ROWS] = row_counter
            metadata_map[PersonAttributesProcessor.TOTAL_ROWS_WITH_INVALID_ATTRIBUTES] = total_invalid_records
            # Alphabetize attribute and token rule keys for deterministic metadata output
            metadata_map[PersonAttributesProcessor.INVALID_ATTRIBUTES_BY_TYPE] = dict(sorted(invalid_attribute_count.items()))
            metadata_map[PersonAttributesProcessor.BLANK_TOKENS_BY_RULE] = dict(sorted(blank_tokens_by_rule_count.items()))

    @staticmethod
    def _write_tokens(writer: PersonAttributesWriter,
                      row: Dict[Type[Attribute], str],
                      row_counter: int,
                      token_generator_result: TokenGeneratorResult,
                      encryption_key: str = None,
                      ring_id: str = None,
                      jwe_formatters: Dict[str, JweMatchTokenFormatter] = None) -> None:
        """
        Write tokens to the output writer. Optionally wraps tokens in JWE format.

        Args:
            writer: The writer to write tokens to.
            row: The original row data.
            row_counter: The current row number.
            token_generator_result: The result from token generation.
            encryption_key: Optional encryption key for JWE wrapping (None to skip JWE).
            ring_id: Optional ring ID for JWE wrapping (None to skip JWE).
        """
        # Sort token IDs for consistent output
        token_ids = sorted(token_generator_result.tokens.keys())

        # Generate a UUID for RecordId if it's not present in the input data
        record_id = row.get(RecordIdAttribute)
        if record_id is None or record_id == '':
            record_id = str(uuid.uuid4())

        for token_id in token_ids:
            token = token_generator_result.tokens[token_id]
            
            # Apply JWE wrapping if encryption key and ring ID are provided
            if encryption_key and ring_id and token:
                jwe_formatter = (jwe_formatters or {}).get(token_id)
                if jwe_formatter:
                    try:
                        token = jwe_formatter.transform(token)
                    except Exception as e:
                        error_msg = f"Error wrapping token in JWE format for row {row_counter:,}, rule {token_id}"
                        logger.error(error_msg, exc_info=True)
                        raise RuntimeError(error_msg) from e
            
            row_result = {
                TokenConstants.RULE_ID: token_id,
                TokenConstants.TOKEN: token,
                TokenConstants.RECORD_ID: record_id
            }

            try:
                writer.write_attributes(row_result)
            except IOError:
                logger.error(f"Error writing attributes to file for row {row_counter:,}", exc_info=True)

    @staticmethod
    def _keep_track_of_invalid_attributes(token_generator_result: TokenGeneratorResult,
                                          row_counter: int,
                                          invalid_attribute_count: Dict[str, int]) -> None:
        """
        Keep track of invalid attributes for logging purposes.

        Args:
            token_generator_result: The result from token generation.
            row_counter: The current row number.
            invalid_attribute_count: Dictionary to track invalid attribute counts.
        """
        if token_generator_result.invalid_attributes:
            logger.info(
                f"Invalid Attributes for row {row_counter:,}: {token_generator_result.invalid_attributes}"
            )

            for invalid_attribute in token_generator_result.invalid_attributes:
                invalid_attribute_count[invalid_attribute] += 1

    @staticmethod
    def _keep_track_of_blank_tokens(token_generator_result: TokenGeneratorResult,
                                    row_counter: int,
                                    blank_tokens_by_rule_count: Dict[str, int]) -> None:
        """
        Keep track of blank tokens for logging purposes.

        Args:
            token_generator_result: The result from token generation.
            row_counter: The current row number.
            blank_tokens_by_rule_count: Dictionary to track blank token counts by rule.
        """
        if token_generator_result.blank_tokens_by_rule:
            logger.debug(
                f"Blank tokens for row {row_counter:,}: {token_generator_result.blank_tokens_by_rule}"
            )

            for rule_id in token_generator_result.blank_tokens_by_rule:
                blank_tokens_by_rule_count[rule_id] += 1

    @staticmethod
    def _initialize_invalid_attribute_count(token_definition: TokenDefinition) -> Dict[str, int]:
        """
        Initialize the invalid attribute count dictionary with attributes used in the token definition set to 0.
        This ensures that all attribute types used in token generation appear in the metadata 
        even in happy path scenarios.

        Args:
            token_definition: The token definition containing all token rules and their attribute expressions

        Returns:
            A dictionary with all attribute names used in token definitions initialized to 0
        """
        invalid_attribute_count: Dict[str, int] = {}
        attribute_classes: Set[Type[Attribute]] = set()
        
        # Collect all unique attribute classes from all token definitions
        for token_id in token_definition.get_token_identifiers():
            expressions = token_definition.get_token_definition(token_id)
            if expressions:
                for expr in expressions:
                    attribute_classes.add(expr.attribute_class)
        
        # Create instances and get names
        for attr_class in attribute_classes:
            try:
                attribute = attr_class()
                invalid_attribute_count[attribute.get_name()] = 0
            except Exception as e:
                logger.warning(f"Failed to instantiate attribute class: {attr_class.__name__}: {e}")
        
        return invalid_attribute_count

    @staticmethod
    def _initialize_blank_tokens_by_rule_count(token_definition: TokenDefinition) -> Dict[str, int]:
        """
        Initialize the blank tokens by rule count dictionary with all token identifiers set to 0.
        This ensures that all token rules appear in the metadata even in happy path scenarios.

        Args:
            token_definition: The token definition containing all token identifiers

        Returns:
            A dictionary with all token identifiers initialized to 0
        """
        blank_tokens_by_rule_count: Dict[str, int] = {}
        for token_id in token_definition.get_token_identifiers():
            blank_tokens_by_rule_count[token_id] = 0
        return blank_tokens_by_rule_count
