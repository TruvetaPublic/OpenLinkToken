"""
Copyright (c) Truveta. All rights reserved.
"""

import re
from typing import Pattern

from openlinktoken.attributes.validation.serializable_attribute_validator import SerializableAttributeValidator


class RegexValidator(SerializableAttributeValidator):
    """
    A Validator that is designed for validating with regex expressions.
    """

    def __init__(self, pattern: str):
        """
        Initialize the regex validator with a pattern.

        Args:
            pattern: The regex pattern string to compile and use for validation

        Raises:
            re.error: If the pattern is invalid
        """
        if not pattern:
            raise ValueError("Pattern cannot be None or empty")

        self._compiled_pattern: Pattern[str] = re.compile(pattern)

    @property
    def compiled_pattern(self) -> Pattern[str]:
        """Get the compiled regex pattern."""
        return self._compiled_pattern

    def eval(self, value: str) -> bool:
        """
        Validate that the value matches the regex pattern.

        Args:
            value: The attribute value to validate

        Returns:
            True if the value matches the pattern, False otherwise
        """
        return value is not None and bool(self._compiled_pattern.match(value))
