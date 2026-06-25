# SPDX-License-Identifier: MIT

from typing import Any, Dict

import yaml

from openlinktoken_cli.tokens.config.tokenization_config import (
    AttributeMappingEntry,
    TokenizationConfig,
    TokenRuleEntry,
)


class TokenizationConfigLoader:
    """Loads and validates a tokenization configuration from a YAML file."""

    @staticmethod
    def load(file_path: str) -> TokenizationConfig:
        """Read YAML from disk and return a validated tokenization config.

        Args:
            file_path: Path to the YAML configuration file.

        Returns:
            Parsed and validated TokenizationConfig instance.
        """
        with open(file_path, "r", encoding="utf-8") as file:
            raw = yaml.safe_load(file)

        if not isinstance(raw, dict):
            raise ValueError(f"Configuration file '{file_path}' is not a valid YAML mapping.")

        return TokenizationConfigLoader._parse(raw, file_path)

    @staticmethod
    def _parse(raw: Dict[str, Any], file_path: str) -> TokenizationConfig:
        """Validate top-level sections, then parse attributes and token rules.

        Args:
            raw: Raw YAML payload represented as a Python mapping.
            file_path: Source path used for validation error context.

        Returns:
            Parsed TokenizationConfig with normalized attributes and token rules.
        """
        if "attributes" not in raw or not raw["attributes"]:
            raise ValueError(f"Configuration '{file_path}' must define a non-empty 'attributes' section.")

        if "token_rules" not in raw or not raw["token_rules"]:
            raise ValueError(f"Configuration '{file_path}' must define a non-empty 'token_rules' section.")

        attributes = TokenizationConfigLoader._parse_attributes(raw["attributes"], file_path)
        token_rules = TokenizationConfigLoader._parse_token_rules(raw["token_rules"], attributes, file_path)
        return TokenizationConfig(attributes=attributes, token_rules=token_rules)

    @staticmethod
    def _parse_attributes(raw_attributes: Any, file_path: str) -> Dict[str, AttributeMappingEntry]:
        """Parse attribute mappings keyed by source column name.

        Args:
            raw_attributes: Raw attributes section from the YAML payload.
            file_path: Source path used for validation error context.

        Returns:
            Mapping of source column names to AttributeMappingEntry values.
        """
        if not isinstance(raw_attributes, dict):
            raise ValueError(f"Configuration '{file_path}': 'attributes' must be a mapping.")

        attributes = {}
        for csv_column, entry in raw_attributes.items():
            if not isinstance(entry, dict):
                raise ValueError(
                    f"Configuration '{file_path}': attribute entry for '{csv_column}' must be a mapping."
                )
            if "field" not in entry or not entry["field"]:
                raise ValueError(
                    f"Configuration '{file_path}': attribute '{csv_column}' is missing required field 'field'."
                )
            if "type" not in entry or not entry["type"]:
                raise ValueError(
                    f"Configuration '{file_path}': attribute '{csv_column}' is missing required field 'type'."
                )
            attributes[csv_column] = AttributeMappingEntry(field=entry["field"], type=entry["type"])

        return attributes

    @staticmethod
    def _parse_token_rules(
        raw_token_rules: Any,
        attributes: Dict[str, AttributeMappingEntry],
        file_path: str,
    ) -> Dict[str, list]:
        """Parse token rules and ensure each referenced field exists in attributes.

        Args:
            raw_token_rules: Raw token_rules section from the YAML payload.
            attributes: Parsed attributes used to validate referenced field ids.
            file_path: Source path used for validation error context.

        Returns:
            Mapping of token ids to ordered TokenRuleEntry lists.
        """
        if not isinstance(raw_token_rules, dict):
            raise ValueError(f"Configuration '{file_path}': 'token_rules' must be a mapping.")

        # Token rules reference logical field ids, not CSV column names.
        valid_field_ids = {entry.field for entry in attributes.values()}
        token_rules = {}
        for token_id, entries in raw_token_rules.items():
            if not isinstance(entries, list) or not entries:
                raise ValueError(
                    f"Configuration '{file_path}': token rule '{token_id}' must be a non-empty list."
                )
            rule_entries = []
            for index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    raise ValueError(
                        f"Configuration '{file_path}': token rule '{token_id}' entry {index} must be a mapping."
                    )
                if "field" not in entry or not entry["field"]:
                    raise ValueError(
                        f"Configuration '{file_path}': token rule '{token_id}' entry {index} is missing 'field'."
                    )
                if "expression" not in entry or not entry["expression"]:
                    raise ValueError(
                        f"Configuration '{file_path}': token rule '{token_id}' entry {index} is missing 'expression'."
                    )
                field_id = entry["field"]
                if field_id not in valid_field_ids:
                    raise ValueError(
                        # Include valid ids in the error so configuration issues are actionable.
                        f"Configuration '{file_path}': token rule '{token_id}' references unknown field "
                        f"'{field_id}'. Valid field ids are: {sorted(valid_field_ids)}."
                    )
                rule_entries.append(TokenRuleEntry(field=field_id, expression=entry["expression"]))
            token_rules[token_id] = rule_entries

        return token_rules
