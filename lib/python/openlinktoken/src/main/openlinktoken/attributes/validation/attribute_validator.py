"""
Copyright (c) Truveta. All rights reserved.
"""

from abc import ABC, abstractmethod


class AttributeValidator(ABC):
    """
    A generic interface for attribute validation.
    """

    @abstractmethod
    def eval(self, value: str) -> bool:
        """
        Validate an attribute value.

        Args:
            value: The attribute value

        Returns:
            True if the attribute is valid, False otherwise
        """
        pass
