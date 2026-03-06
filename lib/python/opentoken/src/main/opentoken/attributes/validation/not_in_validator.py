"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import Set

from opentoken.attributes.validation.serializable_attribute_validator import SerializableAttributeValidator


class NotInValidator(SerializableAttributeValidator):
    """
    A Validator that asserts that the attribute value is NOT IN the list of invalid values.
    """

    def __init__(self, invalid_values: Set[str]):
        """
        Initialize the validator with a set of invalid values.

        Args:
            invalid_values: Set of values that should be considered invalid

        Raises:
            ValueError: If invalid_values is None
        """
        if invalid_values is None:
            raise ValueError("Invalid values set cannot be None")

        # Convert to lowercase for case-insensitive comparison
        self._invalid_values = {value.lower() for value in invalid_values}

    @property
    def invalid_values(self) -> Set[str]:
        """Get the set of invalid values (in lowercase)."""
        return self._invalid_values.copy()

    def eval(self, value: str) -> bool:
        """
        Validate that the attribute value is not in the list of invalid values
        (case-insensitive comparison).

        Args:
            value: The attribute value to validate

        Returns:
            True if the value is not in the invalid values list, False otherwise
        """
        if value is None:
            return False

        return value.lower() not in self._invalid_values
