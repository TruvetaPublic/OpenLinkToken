"""
Copyright (c) Truveta. All rights reserved.
"""

from datetime import date

from openlinktoken.attributes.validation.serializable_attribute_validator import SerializableAttributeValidator


class YearRangeValidator(SerializableAttributeValidator):
    """
    A validator that asserts that a year value is within an acceptable range.

    This validator checks that years are:
    - Not before 1910
    - Not after the current year

    If the year is outside this range, the validation fails.
    """

    MIN_YEAR = 1910

    def __init__(self):
        """Initialize the validator with default year range (1910-current year)."""
        pass

    @property
    def max_year(self) -> int:
        """Get the maximum allowed year (current year)."""
        return date.today().year

    def eval(self, value: str) -> bool:
        """
        Validate that the year value is within acceptable range.

        Args:
            value: The year string to validate

        Returns:
            True if the year is within acceptable range (1910-current year),
            False otherwise
        """
        if not value or not value.strip():
            return False

        try:
            year = int(value.strip())
            return self.MIN_YEAR <= year <= self.max_year
        except ValueError:
            return False
