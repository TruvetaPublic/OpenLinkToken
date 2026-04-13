"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import List, Optional

from openlinktoken.attributes.base_attribute import BaseAttribute
from openlinktoken.attributes.validation import RegexValidator
from openlinktoken.attributes.validation.serializable_attribute_validator import SerializableAttributeValidator


class DecimalAttribute(BaseAttribute):
    """Represents a generic decimal (floating-point) attribute.

    This class extends BaseAttribute and provides functionality for working with
    decimal fields. It recognizes "Decimal" as a valid alias for this attribute type.

    The attribute performs normalization on input values by trimming whitespace
    and validates that the input is a valid decimal number.

    Supported formats include:
    - Standard decimals: 123, -45.67, +89.0
    - Decimals without leading digit: .5
    - Decimals without trailing digits: 1.
    - Scientific notation: 1.5e10, -3.14E-2
    """

    NAME = "Decimal"
    ALIASES = [NAME]

    # Regular expression pattern for validating decimal format
    # Supports: optional sign, digits with optional decimal, scientific notation
    VALIDATION_PATTERN = r"^\s*[+-]?(\d+\.\d*|\d*\.\d+|\d+)([eE][+-]?\d+)?\s*$"

    def __init__(self, additional_validators: Optional[List[SerializableAttributeValidator]] = None):
        """
        Initialize the DecimalAttribute with optional additional validators.

        Args:
            additional_validators: Optional list of additional validators to apply
        """
        validation_rules: List[SerializableAttributeValidator] = [RegexValidator(self.VALIDATION_PATTERN)]
        if additional_validators:
            validation_rules.extend(additional_validators)
        super().__init__(validation_rules)

    def get_name(self) -> str:
        """Get the name of the attribute.

        Returns:
            str: The name "Decimal"
        """
        return self.NAME

    def get_aliases(self) -> List[str]:
        """Get the aliases for the attribute.

        Returns:
            List[str]: A list containing the aliases for this attribute
        """
        return self.ALIASES.copy()

    def normalize(self, value: str) -> str:
        """Normalize the decimal value by trimming whitespace and parsing.

        Args:
            value: The decimal string to normalize

        Returns:
            str: The normalized decimal value

        Raises:
            ValueError: If the decimal is not valid or empty
        """
        if value is None:
            raise ValueError("Decimal value cannot be null")

        value_stripped = value.strip() if value else ""

        if not value_stripped:
            raise ValueError("Invalid decimal format: empty or whitespace")

        # Parse and normalize the decimal value
        try:
            decimal_value = float(value_stripped)
            return str(decimal_value)
        except ValueError:
            raise ValueError(f"Invalid decimal format: {value}")
