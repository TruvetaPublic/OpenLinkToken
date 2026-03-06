"""
Copyright (c) Truveta. All rights reserved.
"""

import re
from typing import List

from opentoken.attributes.general.integer_attribute import IntegerAttribute
from opentoken.attributes.validation import RegexValidator
from opentoken.attributes.validation.serializable_attribute_validator import SerializableAttributeValidator


class YearAttribute(IntegerAttribute):
    """Represents a generic year attribute.

    This class extends IntegerAttribute and provides functionality for working with
    year fields. It recognizes "Year" as a valid alias for this attribute type.

    The attribute performs normalization on input values by trimming whitespace
    and validates that the year is a 4-digit year format.
    """

    NAME = "Year"
    ALIASES = [NAME]

    # Regular expression pattern for validating 4-digit year format with optional whitespace
    VALIDATION_PATTERN = re.compile(r"^\s*\d{4}\s*$")
    # Pattern for extracting just the 4 digits
    YEAR_PATTERN = re.compile(r"\d{4}")

    def __init__(self, additional_validators: List[SerializableAttributeValidator] = None):
        """
        Initialize the YearAttribute with optional additional validators.

        Args:
            additional_validators: Optional list of additional validators to apply
        """
        validation_rules = [RegexValidator(self.VALIDATION_PATTERN)]
        if additional_validators:
            validation_rules.extend(additional_validators)
        super().__init__(validation_rules)

    def get_name(self) -> str:
        """Get the name of the attribute.

        Returns:
            str: The name "Year"
        """
        return self.NAME

    def get_aliases(self) -> List[str]:
        """Get the aliases for the attribute.

        Returns:
            List[str]: A list containing the aliases for this attribute
        """
        return self.ALIASES.copy()

    def normalize(self, value: str) -> str:
        """Normalize the year value by trimming whitespace.

        Args:
            value: The year string to normalize

        Returns:
            str: The normalized year value as a string (leading zeros removed)

        Raises:
            ValueError: If the year is not a valid 4-digit year or empty
        """
        if not value:
            raise ValueError(f"Invalid year format: {value}")

        trimmed = value.strip()

        # Validate it's exactly 4 digits using the pattern before delegating normalization
        if not self.YEAR_PATTERN.match(trimmed):
            raise ValueError(f"Invalid year format: {value}")

        return super().normalize(trimmed)
