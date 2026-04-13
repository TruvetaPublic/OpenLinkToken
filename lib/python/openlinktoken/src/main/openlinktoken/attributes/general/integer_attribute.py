# SPDX-License-Identifier: MIT

from typing import List, Optional

from openlinktoken.attributes.base_attribute import BaseAttribute
from openlinktoken.attributes.validation import RegexValidator
from openlinktoken.attributes.validation.serializable_attribute_validator import SerializableAttributeValidator


class IntegerAttribute(BaseAttribute):
    """Represents a generic integer attribute.

    This class extends BaseAttribute and provides functionality for working with
    integer fields. It recognizes "Integer" as a valid alias for this attribute type.

    The attribute performs normalization on input values by trimming whitespace
    and validates that the input is a valid integer.
    """

    NAME = "Integer"
    ALIASES = [NAME]

    # Regular expression pattern for validating integer format with optional sign
    VALIDATION_PATTERN = r"^\s*[+-]?\d+\s*$"

    def __init__(self, additional_validators: Optional[List[SerializableAttributeValidator]] = None):
        """
        Initialize the IntegerAttribute with optional additional validators.

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
            str: The name "Integer"
        """
        return self.NAME

    def get_aliases(self) -> List[str]:
        """Get the aliases for the attribute.

        Returns:
            List[str]: A list containing the aliases for this attribute
        """
        return self.ALIASES.copy()

    def normalize(self, value: str) -> str:
        """Normalize the integer value by trimming whitespace and parsing.

        Args:
            value: The integer string to normalize

        Returns:
            str: The normalized integer value

        Raises:
            ValueError: If the integer is not valid or empty
        """
        if value is None:
            raise ValueError("Integer value cannot be null")
        if not value:
            raise ValueError("Invalid integer format: empty or whitespace")

        trimmed = value.strip()

        # Validate it's a valid integer
        try:
            int_value = int(trimmed)
            return str(int_value)
        except ValueError:
            raise ValueError(f"Invalid integer format: {value}")
