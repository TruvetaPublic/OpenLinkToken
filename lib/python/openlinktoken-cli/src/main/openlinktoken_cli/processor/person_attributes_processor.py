# SPDX-License-Identifier: MIT

import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Set, Type

from openlinktoken.attributes.attribute import Attribute
from openlinktoken.attributes.general.record_id_attribute import RecordIdAttribute
from openlinktoken.tokens.base_token_definition import BaseTokenDefinition
from openlinktoken.tokens.token_definition import TokenDefinition
from openlinktoken.tokens.token_generator import TokenGenerator
from openlinktoken.tokens.token_generator_result import TokenGeneratorResult
from openlinktoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from openlinktoken.tokens.tokenizer.tokenizer import Tokenizer
from openlinktoken.tokentransformer.jwe_match_token_formatter import JweMatchTokenFormatter
from openlinktoken.tokentransformer.token_transformer import TokenTransformer
from openlinktoken_cli.io.person_attributes_reader import PersonAttributesReader
from openlinktoken_cli.io.person_attributes_writer import PersonAttributesWriter
from openlinktoken_cli.processor.token_constants import TokenConstants
from openlinktoken_cli.util.record_id_hasher import RecordIdHasher

logger = logging.getLogger(__name__)


class _PersonAttributesRowShape(Enum):
    """Supported person-attribute row key shapes at the processor boundary."""

    FIELD_ID = "field-id"
    LEGACY_ATTRIBUTE_CLASS = "legacy-attribute-class"


@dataclass(frozen=True)
class PersonAttributesProcessingSummary:
    """Summary counters for a token generation run."""

    total_rows: int
    total_rows_with_invalid_attributes: int
    invalid_attributes_by_type: Dict[str, int]
    blank_tokens_by_rule: Dict[str, int]


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
    _LEGACY_ROW_WARNING = "Deprecated legacy reader row shape detected; migrate custom readers to field-ID string keys."

    def __init__(self):
        """
        Prevent instantiation of this static utility class.

        Args:
            None.

        Returns:
            None.
        """

    @staticmethod
    def process(
        reader: PersonAttributesReader,
        writer: PersonAttributesWriter,
        token_transformer_list: List[TokenTransformer],
        metadata_map: Dict[str, Any] = None,
        encryption_key: str = None,
        ring_id: str = None,
        hash_record_ids: bool = False,
        token_definition: BaseTokenDefinition = None,
        progress_callback=None,
    ) -> PersonAttributesProcessingSummary:
        """
        Read person attributes from the input data source, generate tokens, and
        write the result back to the output data source. The tokens can be optionally
        transformed before writing and wrapped in JWE format if ring ID is provided.
        Record IDs are SHA-256 hashed in the output when hash_record_ids is True.

        Args:
            reader: The reader initialized with the input data source.
            writer: The writer initialized with the output data source.
            token_transformer_list: A list of token transformers.
            metadata_map: Optional metadata map to update with processing statistics.
            encryption_key: Optional encryption key for JWE wrapping (None to skip JWE).
            ring_id: Optional ring ID for JWE wrapping (None to skip JWE).
            hash_record_ids: When True, each record ID is SHA-256 hashed before writing
                             to the output. This is a one-way operation with no traceability.
            token_definition: Optional token definition to use for token generation.
            progress_callback: Optional callback invoked with the number of processed rows.

        Returns:
            A summary of the token generation results.
        """
        token_definition = token_definition or TokenDefinition()
        return PersonAttributesProcessor._process_with_tokenizer(
            reader,
            writer,
            SHA256Tokenizer(token_transformer_list),
            token_definition,
            metadata_map,
            encryption_key,
            ring_id,
            hash_record_ids,
            progress_callback,
        )

    @staticmethod
    def process_with_tokenizer(
        reader: PersonAttributesReader,
        writer: PersonAttributesWriter,
        tokenizer: Tokenizer,
        metadata_map: Dict[str, Any] = None,
        token_definition: BaseTokenDefinition = None,
        progress_callback=None,
    ) -> PersonAttributesProcessingSummary:
        """
        Read person attributes from the input data source, generate tokens using
        the provided tokenizer, and write the result to the output data source.

        Use this overload when full control over the tokenization strategy is needed,
        for example passing a PassthroughTokenizer for demo mode.

        Args:
            reader: The reader initialized with the input data source.
            writer: The writer initialized with the output data source.
            tokenizer: The tokenizer to use (e.g. SHA256Tokenizer or PassthroughTokenizer).
            metadata_map: Optional metadata map to update with processing statistics.
            token_definition: Optional token definition to use for token generation.
            progress_callback: Optional callback invoked with the number of processed rows.

        Returns:
            A summary of the token generation results.
        """
        token_definition = token_definition or TokenDefinition()
        return PersonAttributesProcessor._process_with_tokenizer(
            reader,
            writer,
            tokenizer,
            token_definition,
            metadata_map,
            progress_callback=progress_callback,
        )

    @staticmethod
    def _process_with_tokenizer(
        reader: PersonAttributesReader,
        writer: PersonAttributesWriter,
        tokenizer: Tokenizer,
        token_definition: BaseTokenDefinition,
        metadata_map: Dict[str, Any] = None,
        encryption_key: str = None,
        ring_id: str = None,
        hash_record_ids: bool = False,
        progress_callback=None,
    ) -> PersonAttributesProcessingSummary:
        """
        Core row-processing logic shared by all process() overloads.

        Args:
            reader: The reader initialized with the input data source.
            writer: The writer initialized with the output data source.
            tokenizer: The tokenizer instance to use.
            token_definition: The token definition instance.
            metadata_map: Optional metadata map to update with processing statistics.
            encryption_key: Optional encryption key for JWE wrapping.
            ring_id: Optional ring ID for JWE wrapping.
            hash_record_ids: When True, each record ID is SHA-256 hashed before writing.
            progress_callback: Optional callback invoked with the number of processed rows.

        Returns:
            A summary of the token generation results.
        """
        field_registry = getattr(token_definition, "field_registry", None)
        token_generator = TokenGenerator(token_definition, tokenizer, field_registry=field_registry)

        row_counter = 0
        last_reported_count = 0
        reader_row_shape: _PersonAttributesRowShape | None = None
        legacy_row_warning_emitted = False
        invalid_attribute_count: Dict[str, int] = PersonAttributesProcessor._initialize_invalid_attribute_count(
            token_definition
        )
        blank_tokens_by_rule_count: Dict[str, int] = PersonAttributesProcessor._initialize_blank_tokens_by_rule_count(
            token_definition
        )

        # Cache JWE formatters if encryption is enabled
        jwe_formatters: Dict[str, JweMatchTokenFormatter] = {}
        if encryption_key and ring_id:
            for token_id in token_definition.get_token_identifiers():
                try:
                    jwe_formatters[token_id] = JweMatchTokenFormatter(
                        encryption_key, ring_id, token_id, "org.openlinktoken"
                    )
                except Exception as e:
                    error_msg = f"Failed to initialize JWE formatter for token rule {token_id}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg) from e

        try:
            for row in reader:
                row_counter += 1

                classified_row_shape = PersonAttributesProcessor._classify_row_shape(row)
                if classified_row_shape is not None:
                    reader_row_shape = PersonAttributesProcessor._require_consistent_row_shape(
                        reader_row_shape, classified_row_shape, row_counter
                    )
                row_shape = reader_row_shape or classified_row_shape or _PersonAttributesRowShape.FIELD_ID

                if row_shape is _PersonAttributesRowShape.LEGACY_ATTRIBUTE_CLASS:
                    if not legacy_row_warning_emitted:
                        logger.warning(PersonAttributesProcessor._LEGACY_ROW_WARNING)
                        legacy_row_warning_emitted = True
                    token_generator_result = token_generator.get_all_tokens(row)
                else:
                    token_generator_result = token_generator.get_all_tokens_via_field_id(row)
                logger.debug(f"Tokens: {token_generator_result.tokens}")

                PersonAttributesProcessor._keep_track_of_invalid_attributes(
                    token_generator_result, row_counter, invalid_attribute_count
                )

                PersonAttributesProcessor._keep_track_of_blank_tokens(
                    token_generator_result, row_counter, blank_tokens_by_rule_count
                )

                PersonAttributesProcessor._write_tokens(
                    writer,
                    row,
                    row_counter,
                    token_generator_result,
                    encryption_key,
                    ring_id,
                    jwe_formatters,
                    hash_record_ids,
                )

                if row_counter % 10000 == 0:
                    logger.info(f"Processed {row_counter:,} records")
                    last_reported_count = row_counter
                    if progress_callback is not None:
                        progress_callback(row_counter)

        except Exception as e:
            logger.error("Error processing records: %s", e)
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
        if progress_callback is not None and row_counter != last_reported_count:
            progress_callback(row_counter)

        # Update metadata if provided
        if metadata_map is not None:
            metadata_map[PersonAttributesProcessor.TOTAL_ROWS] = row_counter
            metadata_map[PersonAttributesProcessor.TOTAL_ROWS_WITH_INVALID_ATTRIBUTES] = total_invalid_records
            # Alphabetize attribute and token rule keys for deterministic metadata output
            metadata_map[PersonAttributesProcessor.INVALID_ATTRIBUTES_BY_TYPE] = dict(
                sorted(invalid_attribute_count.items())
            )
            metadata_map[PersonAttributesProcessor.BLANK_TOKENS_BY_RULE] = dict(
                sorted(blank_tokens_by_rule_count.items())
            )

        return PersonAttributesProcessingSummary(
            total_rows=row_counter,
            total_rows_with_invalid_attributes=total_invalid_records,
            invalid_attributes_by_type=dict(sorted(invalid_attribute_count.items())),
            blank_tokens_by_rule=dict(sorted(blank_tokens_by_rule_count.items())),
        )

    @staticmethod
    def _write_tokens(
        writer: PersonAttributesWriter,
        row: Dict[object, str],
        row_counter: int,
        token_generator_result: TokenGeneratorResult,
        encryption_key: str = None,
        ring_id: str = None,
        jwe_formatters: Dict[str, JweMatchTokenFormatter] = None,
        hash_record_ids: bool = False,
    ) -> None:
        """
        Write tokens to the output writer. Optionally wraps tokens in JWE format
        and hashes record IDs when hash_record_ids is True.

        Args:
            writer: The writer to write tokens to.
            row: The original row data.
            row_counter: The current row number.
            token_generator_result: The result from token generation.
            encryption_key: Optional encryption key for JWE wrapping (None to skip JWE).
            ring_id: Optional ring ID for JWE wrapping (None to skip JWE).
            jwe_formatters: Optional cached JWE formatters.
            hash_record_ids: When True, each record ID is SHA-256 hashed before writing.

        Returns:
            None.
        """
        # Sort token IDs for consistent output
        token_ids = sorted(token_generator_result.tokens.keys())

        # Generate a UUID for RecordId if it's not present in the input data.
        record_id = PersonAttributesProcessor._get_record_id(row)

        # Hash the record ID when requested (no mapping file — intentionally no traceability)
        if hash_record_ids:
            record_id = RecordIdHasher.hash(record_id)

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
                        logger.error(error_msg)
                        raise RuntimeError(error_msg) from e

            row_result = {
                TokenConstants.RULE_ID: token_id,
                TokenConstants.TOKEN: token,
                TokenConstants.RECORD_ID: record_id,
            }

            try:
                writer.write_attributes(row_result)
            except IOError:
                logger.error("Error writing attributes to file for row %s", f"{row_counter:,}")

    @staticmethod
    def _classify_row_shape(row: Dict[object, str]) -> _PersonAttributesRowShape | None:
        """
        Classify a row by its key shape and reject unsupported combinations.

        Args:
            row: The person attribute row to classify.

        Returns:
            The row shape, or None when the row has no keys.
        """
        has_string_keys = False
        has_legacy_attribute_class_keys = False

        for key in row:
            if isinstance(key, str):
                has_string_keys = True
                continue

            if isinstance(key, type) and issubclass(key, Attribute):
                has_legacy_attribute_class_keys = True
                continue

            raise TypeError(f"Person attribute row has unsupported key type: {type(key).__name__}")

        if has_string_keys and has_legacy_attribute_class_keys:
            raise TypeError("Person attribute row cannot mix field-ID string keys with legacy Attribute-class keys")

        if has_legacy_attribute_class_keys:
            return _PersonAttributesRowShape.LEGACY_ATTRIBUTE_CLASS

        return _PersonAttributesRowShape.FIELD_ID if has_string_keys else None

    @staticmethod
    def _require_consistent_row_shape(
        reader_row_shape: _PersonAttributesRowShape | None,
        row_shape: _PersonAttributesRowShape,
        row_counter: int,
    ) -> _PersonAttributesRowShape:
        """
        Ensure a reader does not switch row shapes mid-stream.

        Args:
            reader_row_shape: The row shape previously observed by the reader.
            row_shape: The row shape observed for the current row.
            row_counter: The current row number.

        Returns:
            The consistent row shape.
        """
        if reader_row_shape is None:
            return row_shape

        if reader_row_shape is not row_shape:
            raise ValueError(
                f"Reader row shape changed from {reader_row_shape.value} to {row_shape.value} at row {row_counter:,}"
            )

        return reader_row_shape

    @staticmethod
    def _get_record_id(row: Dict[object, str]) -> str:
        """
        Return the record ID, preserving legacy class-keyed values when present.

        Args:
            row: The person attribute row containing a possible record ID.

        Returns:
            The record ID, generating a UUID when none is present.
        """
        record_id = row.get("RecordId")
        if record_id is None or record_id == "":
            record_id = row.get(RecordIdAttribute)
        if record_id is None or record_id == "":
            for key, value in row.items():
                if isinstance(key, type) and issubclass(key, RecordIdAttribute) and value is not None and value != "":
                    record_id = value
                    break
        if record_id is None or record_id == "":
            return str(uuid.uuid4())
        return record_id

    @staticmethod
    def _keep_track_of_invalid_attributes(
        token_generator_result: TokenGeneratorResult,
        row_counter: int,
        invalid_attribute_count: Dict[str, int],
    ) -> None:
        """
        Keep track of invalid attributes for logging purposes.

        Args:
            token_generator_result: The result from token generation.
            row_counter: The current row number.
            invalid_attribute_count: Dictionary to track invalid attribute counts.

        Returns:
            None.
        """
        if token_generator_result.invalid_attributes:
            logger.info(f"Invalid Attributes for row {row_counter:,}: {token_generator_result.invalid_attributes}")

            for invalid_attribute in token_generator_result.invalid_attributes:
                invalid_attribute_count.setdefault(invalid_attribute, 0)
                invalid_attribute_count[invalid_attribute] += 1

    @staticmethod
    def _keep_track_of_blank_tokens(
        token_generator_result: TokenGeneratorResult,
        row_counter: int,
        blank_tokens_by_rule_count: Dict[str, int],
    ) -> None:
        """
        Keep track of blank tokens for logging purposes.

        Args:
            token_generator_result: The result from token generation.
            row_counter: The current row number.
            blank_tokens_by_rule_count: Dictionary to track blank token counts by rule.

        Returns:
            None.
        """
        if token_generator_result.blank_tokens_by_rule:
            logger.debug(f"Blank tokens for row {row_counter:,}: {token_generator_result.blank_tokens_by_rule}")

            for rule_id in token_generator_result.blank_tokens_by_rule:
                blank_tokens_by_rule_count[rule_id] += 1

    @staticmethod
    def _initialize_invalid_attribute_count(
        token_definition: TokenDefinition,
    ) -> Dict[str, int]:
        """
        Initialize the invalid attribute count dictionary with attributes used in the token definition set to 0.
        This ensures that all attribute types used in token generation appear in the metadata
        even in happy path scenarios.

        Args:
            token_definition: The token definition containing all token rules and their attribute expressions.

        Returns:
            A dictionary with all attribute names used in token definitions initialized to 0.
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
    def _initialize_blank_tokens_by_rule_count(
        token_definition: TokenDefinition,
    ) -> Dict[str, int]:
        """
        Initialize the blank tokens by rule count dictionary with all token identifiers set to 0.
        This ensures that all token rules appear in the metadata even in happy path scenarios.

        Args:
            token_definition: The token definition containing all token identifiers.

        Returns:
            A dictionary with all token identifiers initialized to 0.
        """
        blank_tokens_by_rule_count: Dict[str, int] = {}
        for token_id in token_definition.get_token_identifiers():
            blank_tokens_by_rule_count[token_id] = 0
        return blank_tokens_by_rule_count
