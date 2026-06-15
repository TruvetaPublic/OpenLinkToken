"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import Any, Dict

import yaml

from opentoken.tokens.config.tokenization_config import (
    AttributeMappingEntry,
    TokenizationConfig,
    TokenRuleEntry,
)


class TokenizationConfigLoader:
    """Loads and validates a tokenization configuration from a YAML file."""

    def __init__(self):
        raise RuntimeError("TokenizationConfigLoader should not be instantiated.")

    @staticmethod
    def load(file_path: str) -> TokenizationConfig:
        """Load and validate a tokenization configuration from a YAML file.

        Args:
            file_path: Path to the YAML configuration file.

        Returns:
            A validated TokenizationConfig instance.

        Raises:
            ValueError: If the config is missing required sections or contains invalid entries.
            FileNotFoundError: If the file does not exist.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict):
            raise ValueError(f"Configuration file '{file_path}' is not a valid YAML mapping.")

        return TokenizationConfigLoader._parse(raw, file_path)

    @staticmethod
    def _parse(raw: Dict[str, Any], file_path: str) -> TokenizationConfig:
        """Parse the raw YAML dict into a TokenizationConfig.

        Args:
            raw: The raw YAML dictionary.
            file_path: The source file path (used in error messages).

        Returns:
            A validated TokenizationConfig instance.
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
        """Parse the attributes section of the config.

        Args:
            raw_attributes: The raw attributes dict from YAML.
            file_path: The source file path (used in error messages).

        Returns:
            A dict mapping CSV column names to AttributeMappingEntry instances.
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
        """Parse the token_rules section of the config.

        Args:
            raw_token_rules: The raw token_rules dict from YAML.
            attributes: The already-parsed attributes (used to validate field references).
            file_path: The source file path (used in error messages).

        Returns:
            A dict mapping token IDs to lists of TokenRuleEntry instances.
        """
        if not isinstance(raw_token_rules, dict):
            raise ValueError(f"Configuration '{file_path}': 'token_rules' must be a mapping.")

        # Build the set of valid field identifiers for cross-reference validation
        valid_field_ids = {entry.field for entry in attributes.values()}

        token_rules = {}
        for token_id, entries in raw_token_rules.items():
            if not isinstance(entries, list) or not entries:
                raise ValueError(
                    f"Configuration '{file_path}': token rule '{token_id}' must be a non-empty list."
                )
            rule_entries = []
            for i, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    raise ValueError(
                        f"Configuration '{file_path}': token rule '{token_id}' entry {i} must be a mapping."
                    )
                if "field" not in entry or not entry["field"]:
                    raise ValueError(
                        f"Configuration '{file_path}': token rule '{token_id}' entry {i} is missing 'field'."
                    )
                if "expression" not in entry or not entry["expression"]:
                    raise ValueError(
                        f"Configuration '{file_path}': token rule '{token_id}' entry {i} is missing 'expression'."
                    )
                field_id = entry["field"]
                if field_id not in valid_field_ids:
                    raise ValueError(
                        f"Configuration '{file_path}': token rule '{token_id}' references unknown field "
                        f"'{field_id}'. Valid field ids are: {sorted(valid_field_ids)}."
                    )
                rule_entries.append(TokenRuleEntry(field=field_id, expression=entry["expression"]))
            token_rules[token_id] = rule_entries

        return token_rules
