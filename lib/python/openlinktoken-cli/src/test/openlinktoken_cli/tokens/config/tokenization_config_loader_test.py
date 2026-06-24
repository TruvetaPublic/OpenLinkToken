# SPDX-License-Identifier: MIT

from pathlib import Path

import pytest

from openlinktoken_cli.tokens.config.tokenization_config_loader import TokenizationConfigLoader


class TestTokenizationConfigLoader:
    def test_load_valid_config(self, tmp_path: Path):
        config_path = tmp_path / "tokenization-config.yaml"
        config_path.write_text(
            """
attributes:
  given_nm:
    field: FirstName
    type: GivenName
  family_nm:
    field: FamilyName
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

        assert config.attributes["given_nm"].field == "FirstName"
        assert config.attributes["given_nm"].type == "GivenName"
        assert "T1" in config.token_rules
        assert config.token_rules["T1"][0].field == "FamilyName"
        assert config.token_rules["T1"][0].expression == "T|U"

    def test_load_missing_attribute_field_raises(self, tmp_path: Path):
        config_path = tmp_path / "invalid-config.yaml"
        config_path.write_text(
            """
attributes:
  given_nm:
    type: GivenName

token_rules:
  T1:
    - field: FirstName
      expression: "T|U"
""".strip(),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="missing required field 'field'"):
            TokenizationConfigLoader.load(str(config_path))

    def test_load_unknown_field_reference_raises(self, tmp_path: Path):
        config_path = tmp_path / "invalid-config.yaml"
        config_path.write_text(
            """
attributes:
  given_nm:
    field: FirstName
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
