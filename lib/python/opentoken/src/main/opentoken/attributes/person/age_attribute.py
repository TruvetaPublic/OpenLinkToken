"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import List

from opentoken.attributes.general.integer_attribute import IntegerAttribute
from opentoken.attributes.validation.age_range_validator import AgeRangeValidator


class AgeAttribute(IntegerAttribute):
    """Represents the age attribute.

    This class extends IntegerAttribute and provides functionality for working with
    age fields. It recognizes "Age" as a valid alias for this attribute type.

    The attribute performs normalization on input values by trimming whitespace
    and validates that the age is a valid integer between 0 and 120 (inherited from
    IntegerAttribute for format validation).
    """

    NAME = "Age"
    ALIASES = [NAME]

    def __init__(self):
        """Initialize the AgeAttribute with age range validation."""
        super().__init__([AgeRangeValidator()])

    def get_name(self) -> str:
        """Get the name of the attribute.

        Returns:
            str: The name "Age"
        """
        return self.NAME

    def get_aliases(self) -> List[str]:
        """Get the aliases for the attribute.

        Returns:
            List[str]: A list containing the aliases for this attribute
        """
        return self.ALIASES.copy()
