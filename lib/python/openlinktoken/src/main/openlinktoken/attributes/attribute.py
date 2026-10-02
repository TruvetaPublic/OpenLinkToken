from abc import ABC, abstractmethod
from typing import List


class Attribute(ABC):
    """Base interface for all attributes."""

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of the attribute.

        Returns:
            The name of the attribute.
        """
        ...  # pragma: no cover

    @abstractmethod
    def get_aliases(self) -> List[str]:
        """
        Get the aliases for the attribute.

        Returns:
            The aliases for the attribute.
        """
        ...  # pragma: no cover

    @abstractmethod
    def normalize(self, value: str) -> str:
        """
        Normalize the attribute value.

        Args:
            value: Raw attribute value to convert to its canonical string form.

        Returns:
            Canonical string representation of the attribute value.
        """
        ...  # pragma: no cover

    @abstractmethod
    def validate(self, value: str) -> bool:
        """
        Validate the attribute value.

        Args:
            value: Attribute value to check against this attribute's accepted format.

        Returns:
            True when the check succeeds; otherwise, False.
        """
        ...  # pragma: no cover
