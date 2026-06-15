"""
Copyright (c) Truveta. All rights reserved.
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AttributeMappingEntry:
    """Represents a single attribute mapping entry from the config file.

    Maps a CSV column to a logical field identifier and attribute type.
    """

    field: str
    type: str


@dataclass
class TokenRuleEntry:
    """Represents a single entry in a token rule definition.

    Pairs a logical field identifier with a transformation expression pipeline.
    """

    field: str
    expression: str


@dataclass
class TokenizationConfig:
    """The parsed representation of a custom tokenization configuration file.

    Contains the attribute mappings (CSV column → field + type) and the
    token rule definitions (token id → ordered list of field + expression entries).
    """

    attributes: Dict[str, AttributeMappingEntry] = field(default_factory=dict)
    token_rules: Dict[str, List[TokenRuleEntry]] = field(default_factory=dict)
