# SPDX-License-Identifier: MIT

import logging
import re
from typing import Any, Dict, Optional

import yaml

from openlinktoken_cli.tokens.config.configured_attribute_resolver import ConfiguredAttributeResolver
from openlinktoken_cli.tokens.config.dynamic_token_definition import DynamicTokenDefinition
from openlinktoken_cli.tokens.config.tokenization_config import (
    AttributeMappingEntry,
    TokenizationConfig,
    TokenRuleEntry,
)

logger = logging.getLogger(__name__)


class TokenizationConfigLoader:
    """Loads and validates a tokenization configuration from a YAML file."""

    KEY_COLUMN_MAPPINGS = "column_mappings"
    KEY_TOKEN_RULES = "token_rules"
    KEY_COLUMN_NAME = "column_name"
    KEY_TYPE = "type"
    KEY_FIELD = "field"
    KEY_EXPRESSION = "expression"
    RECORD_ID_TYPE = "RecordId"

    @staticmethod
    def load_runtime_components(
        tokenization_config_path: Optional[str] = None,
    ) -> tuple[TokenizationConfig | None, ConfiguredAttributeResolver | None, DynamicTokenDefinition | None]:
        """Load config and build runtime components used by tokenization commands.

        Args:
            tokenization_config_path: Optional path to a YAML tokenization config.
                When omitted or None, returns a tuple of Nones.

        Returns:
            Tuple of (TokenizationConfig, ConfiguredAttributeResolver, DynamicTokenDefinition)
            or (None, None, None) when no config path is provided.
        """
        if not tokenization_config_path:
            return None, None, None

        config = TokenizationConfigLoader.load(tokenization_config_path)
        resolver = ConfiguredAttributeResolver(config)
        token_definition = DynamicTokenDefinition(config, resolver)
        return config, resolver, token_definition

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
        if (
            TokenizationConfigLoader.KEY_COLUMN_MAPPINGS not in raw
            or not raw[TokenizationConfigLoader.KEY_COLUMN_MAPPINGS]
        ):
            raise ValueError(f"Configuration '{file_path}' must define a non-empty 'column_mappings' section.")

        if TokenizationConfigLoader.KEY_TOKEN_RULES not in raw or not raw[TokenizationConfigLoader.KEY_TOKEN_RULES]:
            raise ValueError(f"Configuration '{file_path}' must define a non-empty 'token_rules' section.")

        column_mappings = TokenizationConfigLoader._parse_column_mappings(
            raw[TokenizationConfigLoader.KEY_COLUMN_MAPPINGS], file_path
        )
        token_rules = TokenizationConfigLoader._parse_token_rules(
            raw[TokenizationConfigLoader.KEY_TOKEN_RULES], column_mappings, file_path
        )

        if not any(entry.type == TokenizationConfigLoader.RECORD_ID_TYPE for entry in column_mappings.values()):
            logger.warning(
                "Configuration '%s' does not map any field to type 'RecordId'. "
                "Source record IDs will not be preserved — output will use randomly generated UUIDs instead.",
                file_path,
            )

        return TokenizationConfig(column_mappings=column_mappings, token_rules=token_rules)

    @staticmethod
    def _parse_column_mappings(raw_column_mappings: Any, file_path: str) -> Dict[str, AttributeMappingEntry]:
        """Parse column mappings keyed by logical field id.

        Args:
            raw_column_mappings: Raw column_mappings section from the YAML payload.
            file_path: Source path used for validation error context.

        Returns:
            Mapping of logical field ids to AttributeMappingEntry values.
        """
        if not isinstance(raw_column_mappings, dict):
            raise ValueError(f"Configuration '{file_path}': 'column_mappings' must be a mapping.")

        column_mappings = {}
        for field_id, entry in raw_column_mappings.items():
            if not isinstance(entry, dict):
                raise ValueError(f"Configuration '{file_path}': attribute entry for '{field_id}' must be a mapping.")
            if (
                TokenizationConfigLoader.KEY_COLUMN_NAME not in entry
                or not entry[TokenizationConfigLoader.KEY_COLUMN_NAME]
            ):
                raise ValueError(
                    f"Configuration '{file_path}': column_mappings entry '{field_id}' "
                    f"is missing required field 'column_name'."
                )
            if TokenizationConfigLoader.KEY_TYPE not in entry or not entry[TokenizationConfigLoader.KEY_TYPE]:
                raise ValueError(
                    f"Configuration '{file_path}': attribute '{field_id}' is missing required field 'type'."
                )
            column_mappings[field_id] = AttributeMappingEntry(
                column_name=entry[TokenizationConfigLoader.KEY_COLUMN_NAME],
                type=entry[TokenizationConfigLoader.KEY_TYPE],
            )

        return column_mappings

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

        # Token rules reference logical field ids defined in column_mappings.
        valid_field_ids = set(attributes.keys())
        token_rules = {}
        for token_id, entries in raw_token_rules.items():
            if not isinstance(entries, list) or not entries:
                raise ValueError(f"Configuration '{file_path}': token rule '{token_id}' must be a non-empty list.")
            rule_entries = []
            for index, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    raise ValueError(
                        f"Configuration '{file_path}': token rule '{token_id}' entry {index} must be a mapping."
                    )
                if TokenizationConfigLoader.KEY_FIELD not in entry or not entry[TokenizationConfigLoader.KEY_FIELD]:
                    raise ValueError(
                        f"Configuration '{file_path}': token rule '{token_id}' entry {index} is missing 'field'."
                    )
                if (
                    TokenizationConfigLoader.KEY_EXPRESSION not in entry
                    or not entry[TokenizationConfigLoader.KEY_EXPRESSION]
                ):
                    raise ValueError(
                        f"Configuration '{file_path}': token rule '{token_id}' entry {index} is missing 'expression'."
                    )
                field_id = entry[TokenizationConfigLoader.KEY_FIELD]
                if field_id not in valid_field_ids:
                    raise ValueError(
                        # Include valid ids in the error so configuration issues are actionable.
                        f"Configuration '{file_path}': token rule '{token_id}' references unknown field "
                        f"'{field_id}'. Valid field ids are: {sorted(valid_field_ids)}."
                    )
                TokenizationConfigLoader._validate_expression(
                    entry[TokenizationConfigLoader.KEY_EXPRESSION], token_id, index, file_path
                )
                rule_entries.append(
                    TokenRuleEntry(
                        field=field_id,
                        expression=entry[TokenizationConfigLoader.KEY_EXPRESSION],
                    )
                )
            token_rules[token_id] = rule_entries

        return token_rules

    @staticmethod
    def _validate_expression(expression: str, token_id: str, index: int, file_path: str) -> None:
        """Raise ValueError if expression contains an unrecognised operator."""
        _KNOWN_OPERATORS = {"T", "U", "S", "D", "M", "R"}
        _OPERATOR_PATTERN = re.compile(r"\s*(?P<op>[A-Za-z]+)(?:\([^)]*\))?", re.IGNORECASE)
        for part in expression.split("|"):
            part = part.strip()
            if not part:
                continue
            match = _OPERATOR_PATTERN.fullmatch(part)
            if not match or match.group("op").upper() not in _KNOWN_OPERATORS:
                raise ValueError(
                    f"Configuration '{file_path}': token rule '{token_id}' entry {index} "
                    f"contains unknown expression operator '{part}'. "
                    f"Accepted operators are: {sorted(_KNOWN_OPERATORS)}."
                )
