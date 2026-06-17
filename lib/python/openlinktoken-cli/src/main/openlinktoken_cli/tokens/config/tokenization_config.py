# SPDX-License-Identifier: MIT

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AttributeMappingEntry:
    """Represents a single attribute mapping entry from the config file."""

    field: str
    type: str


@dataclass
class TokenRuleEntry:
    """Represents a single entry in a token rule definition."""

    field: str
    expression: str


@dataclass
class TokenizationConfig:
    """Parsed representation of a custom tokenization configuration file."""

    attributes: Dict[str, AttributeMappingEntry] = field(default_factory=dict)
    token_rules: Dict[str, List[TokenRuleEntry]] = field(default_factory=dict)
