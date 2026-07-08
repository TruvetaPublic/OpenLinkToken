# SPDX-License-Identifier: MIT

from unittest.mock import MagicMock, patch

import pytest

from openlinktoken_cli.tokens.config.tokenization_config import AttributeMappingEntry, TokenizationConfig
from openlinktoken_cli.tokens.config.tokenization_config_helper import TokenizationConfigHelper
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute


class TestTokenizationConfigHelper:
    def test_build_configured_input_attribute_map_warns_when_factory_misses_entry(self, caplog):
        config = TokenizationConfig(
            column_mappings={
                "FirstName": AttributeMappingEntry(column_name="given_nm", type="GivenName"),
                "FamilyName": AttributeMappingEntry(column_name="family_nm", type="LastName"),
            },
            token_rules={},
        )

        factory = MagicMock()
        factory.get_class_for_column.side_effect = [FirstNameAttribute, KeyError("missing")]

        attribute_map = TokenizationConfigHelper.build_configured_input_attribute_map(config, factory)

        assert attribute_map == {"given_nm": FirstNameAttribute}
        assert "has no dynamic class registered" in caplog.text

    def test_create_reader_csv_applies_attribute_map(self):
        config = TokenizationConfig(
            column_mappings={"FirstName": AttributeMappingEntry(column_name="given_nm", type="GivenName")},
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
            column_mappings={"FirstName": AttributeMappingEntry(column_name="given_nm", type="GivenName")},
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
