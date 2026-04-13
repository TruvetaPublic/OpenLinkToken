# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from typing import List

from openlinktoken.attributes.serializable_attribute import SerializableAttribute


class CombinedAttribute(SerializableAttribute, ABC):
    """
    Abstract base class for attributes that combine multiple attribute implementations.

    This class allows for combining multiple attribute implementations where each
    implementation handles a specific subset of validation and normalization logic.
    The combined attribute will iterate through all implementations until it finds
    one that reports the string as valid for validation, and uses the first
    implementation that can normalize the value for normalization.

    Subclasses must implement get_attribute_implementations() to provide
    the list of attribute implementations to combine.
    """

    @abstractmethod
    def get_attribute_implementations(self) -> List[SerializableAttribute]:
        """
        Get the list of attribute implementations to combine.

        Returns:
            List[SerializableAttribute]: The list of attribute implementations
        """
        pass

    def validate(self, value: str) -> bool:
        """
        Validate the attribute value by checking if any of the combined
        implementations consider the value valid.

        Args:
            value: The attribute value to validate

        Returns:
            True if any implementation validates the value successfully, False otherwise
        """
        if value is None:
            return False

        return any(impl.validate(value) for impl in self.get_attribute_implementations())

    def normalize(self, value: str) -> str:
        """
        Normalize the attribute value using the first implementation that
        successfully validates the value.

        Args:
            value: The attribute value to normalize

        Returns:
            The normalized value from the first validating implementation,
            or the original trimmed value if no implementation validates it
        """
        if value is None:
            return None

        for impl in self.get_attribute_implementations():
            if impl.validate(value):
                return impl.normalize(value)

        # If no implementation validates the value, return trimmed original
        return value.strip()
