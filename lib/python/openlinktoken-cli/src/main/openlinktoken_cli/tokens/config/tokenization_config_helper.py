"""Shared helper utilities for config-driven tokenization workflows."""

import logging
from typing import Optional

from openlinktoken_cli.io.csv.person_attributes_csv_reader import PersonAttributesCSVReader
from openlinktoken_cli.io.parquet.person_attributes_parquet_reader import PersonAttributesParquetReader
from openlinktoken_cli.tokens.config.dynamic_attribute_factory import DynamicAttributeFactory
from openlinktoken_cli.tokens.config.dynamic_token_definition import DynamicTokenDefinition
from openlinktoken_cli.tokens.config.tokenization_config import TokenizationConfig
from openlinktoken_cli.tokens.config.tokenization_config_loader import TokenizationConfigLoader
from openlinktoken_cli.util.file_type_detector import FileTypeDetector

logger = logging.getLogger(__name__)


class TokenizationConfigHelper:
    """Utilities for loading and applying tokenization configs."""

    @staticmethod
    def load_tokenization_config(
        tokenization_config_path: Optional[str] = None,
    ) -> tuple[TokenizationConfig | None, DynamicAttributeFactory | None, DynamicTokenDefinition | None]:
        """Load optional tokenization config and build derived factory/definition objects."""
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
        """Build input-column-to-field-id mapping from tokenization config."""
        attribute_map = {}
        for csv_column in config.attributes:
            try:
                attribute_map[csv_column] = factory.get_field_for_csv_column(csv_column)
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
        """Create and optionally configure a reader for CSV or Parquet inputs."""
        attribute_map = None
        if config is not None and factory is not None:
            attribute_map = TokenizationConfigHelper.build_configured_input_attribute_map(config, factory)

        file_type_lower = file_type.lower()
        if file_type_lower == FileTypeDetector.TYPE_CSV:
            return PersonAttributesCSVReader(path, attribute_map=attribute_map)
        if file_type_lower == FileTypeDetector.TYPE_PARQUET:
            return PersonAttributesParquetReader(path, attribute_map=attribute_map)

        raise ValueError(f"Unsupported input type: {file_type}")
