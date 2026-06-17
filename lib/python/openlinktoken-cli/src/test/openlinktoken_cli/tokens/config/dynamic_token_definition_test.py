# SPDX-License-Identifier: MIT

from openlinktoken_cli.tokens.config.dynamic_attribute_factory import DynamicAttributeFactory
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
                "given_nm": AttributeMappingEntry(field="GivenName", type="GivenName"),
            },
            token_rules={
                "T1": [
                    TokenRuleEntry(field="FamilyName", expression="T|U"),
                    TokenRuleEntry(field="GivenName", expression="T|S(0,1)|U"),
                ]
            },
        )

        factory = DynamicAttributeFactory(config)
        definition = DynamicTokenDefinition(config, factory)

        assert definition.get_version() == "custom"
        assert definition.get_token_identifiers() == {"T1"}

        t1_definition = definition.get_token_definition("T1")
        assert len(t1_definition) == 2
        assert t1_definition[0].attribute_class is factory.get_class_for_field("FamilyName")
        assert t1_definition[0].expressions == "T|U"
        assert t1_definition[1].attribute_class is factory.get_class_for_field("GivenName")
        assert t1_definition[1].expressions == "T|S(0,1)|U"
