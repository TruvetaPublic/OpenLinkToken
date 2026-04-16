# SPDX-License-Identifier: MIT

from typing import List

from openlinktoken.attributes.general.year_attribute import YearAttribute
from openlinktoken.attributes.validation.year_range_validator import YearRangeValidator


class BirthYearAttribute(YearAttribute):
    """Represents the birth year attribute.

    This class extends YearAttribute and provides functionality for working with
    birth year fields. It recognizes "BirthYear" as a valid alias for this attribute type.

    The attribute performs normalization on input values by trimming whitespace
    and validates that the birth year is a 4-digit year between 1910 and the current year.
    """

    NAME = "BirthYear"
    ALIASES = [NAME, "YearOfBirth"]

    def __init__(self):
        super().__init__(additional_validators=[YearRangeValidator()])

    def get_name(self) -> str:
        """Get the name of the attribute.

        Returns:
            str: The name "BirthYear"
        """
        return self.NAME

    def get_aliases(self) -> List[str]:
        """Get the aliases for the attribute.

        Returns:
            List[str]: A list containing the aliases for this attribute
        """
        return self.ALIASES.copy()
