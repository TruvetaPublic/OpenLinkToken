"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import List

from openlinktoken.attributes.base_attribute import BaseAttribute


class StringAttribute(BaseAttribute):
    """Represents a generic string attribute.

    This class extends BaseAttribute and provides functionality for working with
    string fields. It normalizes values by trimming whitespace.

    The attribute validates that the value is not null or empty using the
    default BaseAttribute validation rules.
    """

    NAME = "String"
    ALIASES = [NAME, "Text"]

    def __init__(self):
        # Use default validation rules from BaseAttribute (not null or empty)
        super().__init__()

    def get_name(self) -> str:
        """Get the name of the attribute.

        Returns:
            str: The name "String"
        """
        return self.NAME

    def get_aliases(self) -> List[str]:
        """Get the aliases for the attribute.

        Returns:
            List[str]: A list containing the aliases for this attribute
        """
        return self.ALIASES.copy()

    def normalize(self, value: str) -> str:
        """Normalize the string value by trimming whitespace.

        Args:
            value: The string value to normalize

        Returns:
            str: The trimmed string value

        Raises:
            ValueError: If value is None
        """
        if value is None:
            raise ValueError("String value cannot be null")
        return value.strip()
