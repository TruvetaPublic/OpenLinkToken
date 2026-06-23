"""Shared utilities for config-driven tokenization in CLI commands."""

import logging
from typing import Optional

from openlinktoken_cli.tokens.config.dynamic_attribute_factory import DynamicAttributeFactory
from openlinktoken_cli.tokens.config.dynamic_token_definition import DynamicTokenDefinition
from openlinktoken_cli.tokens.config.tokenization_config import TokenizationConfig
from openlinktoken_cli.tokens.config.tokenization_config_loader import TokenizationConfigLoader
from openlinktoken_cli.io.csv.person_attributes_csv_reader import PersonAttributesCSVReader
from openlinktoken_cli.io.parquet.person_attributes_parquet_reader import PersonAttributesParquetReader
from openlinktoken_cli.util.file_type_detector import FileTypeDetector

logger = logging.getLogger(__name__)


class TokenizationConfigHelper:
    """Utilities for loading and applying tokenization configs."""

    @staticmethod
    def load_tokenization_config(
        tokenization_config_path: Optional[str] = None,
    ) -> tuple[TokenizationConfig | None, DynamicAttributeFactory | None, DynamicTokenDefinition | None]:
        """
        Load tokenization config and create factories for config-driven token generation.

        Args:
            tokenization_config_path: Path to YAML tokenization config file.
                If None or omitted, returns (None, None, None).

        Returns:
            Tuple of (TokenizationConfig, DynamicAttributeFactory, DynamicTokenDefinition)
            or (None, None, None) if config not provided.
        """
        if not tokenization_config_path:
            return None, None, None

        config = TokenizationConfigLoader.load(tokenization_config_path)
        factory = DynamicAttributeFactory(config)
        token_definition = DynamicTokenDefinition(config, factory)
        return config, factory, token_definition

    @staticmethod
    def build_configured_input_attribute_map(
        config: TokenizationConfig,
        factory: DynamicAttributeFactory,
    ) -> dict:
        """
        Build input column-to-attribute class mapping from tokenization config.

        Maps each input column name defined in config to its corresponding attribute class.
        Logs warnings for columns with no registered dynamic class.

        Args:
            config: Tokenization config containing attribute definitions.
            factory: Dynamic attribute factory for class resolution.

        Returns:
            Dictionary mapping input column names to attribute classes.
        """
        attribute_map = {}
        for csv_column in config.attributes:
            try:
                attribute_map[csv_column] = factory.get_class_for_csv_column(csv_column)
            except KeyError:
                logger.warning(
                    "CSV column '%s' is in config but has no dynamic class registered.", csv_column
                )
        return attribute_map

    @staticmethod
    def create_reader(
        path: str,
        file_type: str,
        config: Optional[TokenizationConfig] = None,
        factory: Optional[DynamicAttributeFactory] = None,
    ):
        """
        Create a PersonAttributesReader based on file type with optional config-driven attribute mapping.

        Args:
            path: Input file path.
            file_type: File type ('csv' or 'parquet').
            config: Optional tokenization config with attribute mappings.
            factory: Optional dynamic attribute factory for config-driven reads.

        Returns:
            Configured PersonAttributesReader instance.

        Raises:
            ValueError: If file_type is not supported.
        """
        attribute_map = None
        if config is not None and factory is not None:
            attribute_map = TokenizationConfigHelper.build_configured_input_attribute_map(config, factory)

        file_type_lower = file_type.lower()
        if file_type_lower == FileTypeDetector.TYPE_CSV:
            reader = PersonAttributesCSVReader(path)
            if attribute_map is not None:
                reader.attribute_map = attribute_map.copy()
            return reader
        elif file_type_lower == FileTypeDetector.TYPE_PARQUET:
            reader = PersonAttributesParquetReader(path)
            if attribute_map is not None:
                reader.attribute_map = {
                    column_name.lower(): attribute_class
                    for column_name, attribute_class in attribute_map.items()
                }
            return reader
        else:
            raise ValueError(f"Unsupported input type: {file_type}")
