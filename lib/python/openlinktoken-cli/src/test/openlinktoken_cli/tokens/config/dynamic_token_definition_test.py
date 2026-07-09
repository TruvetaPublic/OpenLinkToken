# SPDX-License-Identifier: MIT

from openlinktoken_cli.tokens.config.configured_attribute_resolver import ConfiguredAttributeResolver
from openlinktoken_cli.tokens.config.dynamic_token_definition import DynamicTokenDefinition
from openlinktoken_cli.tokens.config.tokenization_config import (
    AttributeMappingEntry,
    TokenizationConfig,
    TokenRuleEntry,
)


class TestDynamicTokenDefinition:
    def test_builds_token_definitions_from_config(self):
        config = TokenizationConfig(
            attributes={
                "family_nm": AttributeMappingEntry(field="FamilyName", type="LastName"),
                "given_nm": AttributeMappingEntry(field="FirstName", type="GivenName"),
            },
            token_rules={
                "T1": [
                    TokenRuleEntry(field="FamilyName", expression="T|U"),
                    TokenRuleEntry(field="FirstName", expression="T|S(0,1)|U"),
                ]
            },
        )

        resolver = ConfiguredAttributeResolver(config)
        definition = DynamicTokenDefinition(config, resolver)

        assert definition.get_version() == "custom"
        assert definition.get_token_identifiers() == {"T1"}
        assert "FamilyName" in definition.field_registry.get_field_ids()
        assert "FirstName" in definition.field_registry.get_field_ids()

        t1_definition = definition.get_token_definition("T1")
        assert len(t1_definition) == 2
        assert t1_definition[0].attribute_class is resolver.get_class_for_field("FamilyName")
        assert t1_definition[0].field_id == "FamilyName"
        assert t1_definition[0].expressions == "T|U"
        assert t1_definition[1].attribute_class is resolver.get_class_for_field("FirstName")
        assert t1_definition[1].field_id == "FirstName"
        assert t1_definition[1].expressions == "T|S(0,1)|U"
