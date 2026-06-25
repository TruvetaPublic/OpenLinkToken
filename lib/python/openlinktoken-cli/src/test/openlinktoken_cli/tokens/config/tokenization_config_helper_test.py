# SPDX-License-Identifier: MIT

import tempfile
from unittest.mock import MagicMock, patch

import pytest

from openlinktoken_cli.tokens.config.dynamic_attribute_factory import DynamicAttributeFactory
from openlinktoken_cli.tokens.config.dynamic_token_definition import DynamicTokenDefinition
from openlinktoken_cli.tokens.config.tokenization_config import AttributeMappingEntry, TokenizationConfig
from openlinktoken_cli.tokens.config.tokenization_config_helper import TokenizationConfigHelper
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute


class TestTokenizationConfigHelper:
    def test_load_tokenization_config_without_path_returns_none_tuple(self):
        config, factory, token_definition = TokenizationConfigHelper.load_tokenization_config(None)

        assert config is None
        assert factory is None
        assert token_definition is None

    def test_load_tokenization_config_with_path_builds_config_factory_and_definition(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as file:
            file.write(
                """
attributes:
  given_nm:
    field: FirstName
    type: GivenName
token_rules:
  T1:
    - field: FirstName
      expression: T|U
""".strip()
            )
            config_path = file.name

        config, factory, token_definition = TokenizationConfigHelper.load_tokenization_config(config_path)

        assert isinstance(config, TokenizationConfig)
        assert isinstance(factory, DynamicAttributeFactory)
        assert isinstance(token_definition, DynamicTokenDefinition)

    def test_build_configured_input_attribute_map_warns_when_factory_misses_entry(self, caplog):
        config = TokenizationConfig(
            attributes={
                "given_nm": AttributeMappingEntry(field="FirstName", type="GivenName"),
                "family_nm": AttributeMappingEntry(field="FamilyName", type="LastName"),
            },
            token_rules={},
        )

        factory = MagicMock()
        factory.get_class_for_csv_column.side_effect = [FirstNameAttribute, KeyError("missing")]

        attribute_map = TokenizationConfigHelper.build_configured_input_attribute_map(config, factory)

        assert attribute_map == {"given_nm": FirstNameAttribute}
        assert "has no dynamic class registered" in caplog.text

    def test_create_reader_csv_applies_attribute_map(self):
        config = TokenizationConfig(
            attributes={"given_nm": AttributeMappingEntry(field="FirstName", type="GivenName")},
            token_rules={},
        )
        factory = MagicMock()

        with patch(
            "openlinktoken_cli.tokens.config.tokenization_config_helper.TokenizationConfigHelper"
            ".build_configured_input_attribute_map",
            return_value={"given_nm": FirstNameAttribute},
        ), patch(
            "openlinktoken_cli.tokens.config.tokenization_config_helper.PersonAttributesCSVReader"
        ) as mock_reader_cls:
            reader = MagicMock()
            mock_reader_cls.return_value = reader

            created_reader = TokenizationConfigHelper.create_reader("input.csv", "csv", config, factory)

        assert created_reader is reader
        mock_reader_cls.assert_called_once_with("input.csv", attribute_map={"given_nm": FirstNameAttribute})

    def test_create_reader_parquet_applies_attribute_map(self):
        config = TokenizationConfig(
            attributes={"given_nm": AttributeMappingEntry(field="FirstName", type="GivenName")},
            token_rules={},
        )
        factory = MagicMock()

        with patch(
            "openlinktoken_cli.tokens.config.tokenization_config_helper.TokenizationConfigHelper"
            ".build_configured_input_attribute_map",
            return_value={"given_nm": FirstNameAttribute},
        ), patch(
            "openlinktoken_cli.tokens.config.tokenization_config_helper.PersonAttributesParquetReader"
        ) as mock_reader_cls:
            reader = MagicMock()
            mock_reader_cls.return_value = reader

            created_reader = TokenizationConfigHelper.create_reader("input.parquet", "parquet", config, factory)

        assert created_reader is reader
        mock_reader_cls.assert_called_once_with("input.parquet", attribute_map={"given_nm": FirstNameAttribute})

    def test_create_reader_raises_for_unsupported_type(self):
        with pytest.raises(ValueError, match="Unsupported input type"):
            TokenizationConfigHelper.create_reader("input.unknown", "json")
