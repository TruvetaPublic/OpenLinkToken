"""
Copyright (c) Truveta. All rights reserved.
"""

from openlinktoken.attributes.validation.serializable_attribute_validator import SerializableAttributeValidator


class AgeRangeValidator(SerializableAttributeValidator):
    """
    A validator that asserts that an age value is within an acceptable range (0-120).

    This validator checks that ages are:
    - Not less than 0
    - Not greater than 120

    If the age is outside this range, the validation fails.
    """

    MIN_AGE = 0
    MAX_AGE = 120

    def __init__(self):
        """Initialize the validator with default age range (0-120)."""
        pass

    def eval(self, value: str) -> bool:
        """
        Validate that the age value is within acceptable range.

        Args:
            value: The age string to validate

        Returns:
            True if the age is within acceptable range (0-120), False otherwise
        """
        if not value or not value.strip():
            return False

        try:
            age = int(value.strip())
            return self.MIN_AGE <= age <= self.MAX_AGE
        except ValueError:
            return False
