# SPDX-License-Identifier: MIT

from pathlib import Path

import pytest

from openlinktoken_cli.tokens.config.configured_attribute_resolver import ConfiguredAttributeResolver
from openlinktoken_cli.tokens.config.dynamic_token_definition import DynamicTokenDefinition
from openlinktoken_cli.tokens.config.tokenization_config_loader import TokenizationConfigLoader


class TestTokenizationConfigLoader:
    def test_load_runtime_components_without_path_returns_none_tuple(self):
        config, resolver, token_definition = TokenizationConfigLoader.load_runtime_components(None)

        assert config is None
        assert resolver is None
        assert token_definition is None

    def test_load_runtime_components_with_path_builds_runtime_objects(self, tmp_path: Path):
        config_path = tmp_path / "tokenization-config.yaml"
        config_path.write_text(
            """
column_mappings:
  FirstName:
    column_name: "given_nm"
    type: GivenName
token_rules:
  T1:
    - field: FirstName
      expression: T|U
""".strip(),
            encoding="utf-8",
        )

        config, resolver, token_definition = TokenizationConfigLoader.load_runtime_components(str(config_path))

        assert config is not None
        assert isinstance(resolver, ConfiguredAttributeResolver)
        assert isinstance(token_definition, DynamicTokenDefinition)

    def test_load_valid_config(self, tmp_path: Path):
        config_path = tmp_path / "tokenization-config.yaml"
        config_path.write_text(
            """
column_mappings:
  FirstName:
    column_name: "given_nm"
    type: GivenName
  FamilyName:
    column_name: "family nm"
    type: LastName

token_rules:
  T1:
    - field: FamilyName
      expression: "T|U"
    - field: FirstName
      expression: "T|S(0,1)|U"
""".strip(),
            encoding="utf-8",
        )

        config = TokenizationConfigLoader.load(str(config_path))

        assert config.column_mappings["FirstName"].column_name == "given_nm"
        assert config.column_mappings["FirstName"].type == "GivenName"
        assert "T1" in config.token_rules
        assert config.token_rules["T1"][0].field == "FamilyName"
        assert config.token_rules["T1"][0].expression == "T|U"

    def test_load_missing_attribute_field_raises(self, tmp_path: Path):
        config_path = tmp_path / "invalid-config.yaml"
        config_path.write_text(
            """
column_mappings:
  FirstName:
    type: GivenName

token_rules:
  T1:
    - field: FirstName
      expression: "T|U"
""".strip(),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="missing required field 'column_name'"):
            TokenizationConfigLoader.load(str(config_path))

    def test_load_unknown_field_reference_raises(self, tmp_path: Path):
        config_path = tmp_path / "invalid-config.yaml"
        config_path.write_text(
            """
column_mappings:
  FirstName:
    column_name: "given_nm"
    type: GivenName

token_rules:
  T1:
    - field: UnknownField
      expression: "T|U"
""".strip(),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="references unknown field"):
            TokenizationConfigLoader.load(str(config_path))

    def test_load_raises_on_unknown_expression_operator(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            """
column_mappings:
  FirstName:
    column_name: "given_nm"
    type: GivenName

token_rules:
  T1:
    - field: FirstName
      expression: "T|Y"
""".strip(),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="unknown expression operator"):
            TokenizationConfigLoader.load(str(config_path))
