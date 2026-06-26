"""Shared helper utilities for config-driven tokenization workflows."""

import logging
from typing import Optional

from openlinktoken_cli.io.csv.person_attributes_csv_reader import PersonAttributesCSVReader
from openlinktoken_cli.io.parquet.person_attributes_parquet_reader import PersonAttributesParquetReader
from openlinktoken_cli.tokens.config.dynamic_attribute_factory import DynamicAttributeFactory
from openlinktoken_cli.tokens.config.tokenization_config import TokenizationConfig
from openlinktoken_cli.util.file_type_detector import FileTypeDetector

logger = logging.getLogger(__name__)


class TokenizationConfigHelper:
    """Utilities for mapping config-driven attributes and creating readers."""

    @staticmethod
    def build_configured_input_attribute_map(
        config: TokenizationConfig,
        factory: DynamicAttributeFactory,
    ) -> dict:
        """Build input-column-to-attribute-class mapping from tokenization config.

        Args:
            config: Parsed tokenization config containing the attribute column mappings.
            factory: Factory used to resolve each config column to its built-in attribute class.

        Returns:
            A dict mapping each input CSV column name to its corresponding attribute class.
        """
        attribute_map = {}
        for csv_column in config.attributes:
            try:
                attribute_map[csv_column] = factory.get_class_for_csv_column(csv_column)
            except KeyError:
                logger.warning("CSV column '%s' is in config but has no dynamic class registered.", csv_column)
        return attribute_map

    @staticmethod
    def create_reader(
        path: str,
        file_type: str,
        config: Optional[TokenizationConfig] = None,
        factory: Optional[DynamicAttributeFactory] = None,
    ):
        """Create and optionally configure a reader for CSV or Parquet inputs.

        Args:
            path: Path to the input file.
            file_type: Format of the input file; must be 'csv' or 'parquet' (case-insensitive).
            config: Optional tokenization config used to build the attribute map.
            factory: Optional factory required when config is provided.

        Returns:
            A PersonAttributesCSVReader or PersonAttributesParquetReader initialised with
            the resolved attribute map when a config is supplied, or with no map otherwise.

        Raises:
            ValueError: If file_type is not 'csv' or 'parquet'.
        """
        attribute_map = None
        if config is not None and factory is not None:
            attribute_map = TokenizationConfigHelper.build_configured_input_attribute_map(config, factory)

        file_type_lower = file_type.lower()
        if file_type_lower == FileTypeDetector.TYPE_CSV:
            return PersonAttributesCSVReader(path, attribute_map=attribute_map)
        if file_type_lower == FileTypeDetector.TYPE_PARQUET:
            return PersonAttributesParquetReader(path, attribute_map=attribute_map)

        raise ValueError(f"Unsupported input type: {file_type}")
