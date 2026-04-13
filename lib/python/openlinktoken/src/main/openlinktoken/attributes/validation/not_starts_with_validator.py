# SPDX-License-Identifier: MIT

from typing import Set

from openlinktoken.attributes.validation.serializable_attribute_validator import SerializableAttributeValidator


class NotStartsWithValidator(SerializableAttributeValidator):
    """
    A Validator that asserts that the attribute value does NOT START WITH
    any of the invalid prefixes.
    """

    def __init__(self, invalid_prefixes: Set[str]):
        """
        Initialize the validator with a set of invalid prefixes.

        Args:
            invalid_prefixes: Set of prefixes that values should not start with

        Raises:
            ValueError: If invalid_prefixes is None
        """
        if invalid_prefixes is None:
            raise ValueError("Invalid prefixes set cannot be None")

        self._invalid_prefixes = invalid_prefixes.copy()

    @property
    def invalid_prefixes(self) -> Set[str]:
        """Get the set of invalid prefixes."""
        return self._invalid_prefixes.copy()

    def eval(self, value: str) -> bool:
        """
        Validate that the attribute value does not start with any of the invalid prefixes.

        Args:
            value: The attribute value to validate

        Returns:
            True if the value doesn't start with any invalid prefix, False otherwise
        """
        if value is None:
            return False

        trimmed_value = value.strip()
        return not any(trimmed_value.startswith(prefix) for prefix in self._invalid_prefixes)
