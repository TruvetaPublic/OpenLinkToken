"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import List

from opentoken.attributes.general.string_attribute import StringAttribute


class RecordIdAttribute(StringAttribute):
    """Represents a record identifier attribute.

    This class extends StringAttribute and provides functionality for working with
    record ID fields. It recognizes "RecordId" as a valid alias for this
    attribute type.

    The attribute normalizes values by trimming whitespace (inherited from StringAttribute).
    It validates that the value is not null or empty using the default BaseAttribute
    validation rules.
    """

    NAME = "RecordId"
    ALIASES = [NAME, "Id"]

    def __init__(self):
        # Use validation rules from StringAttribute
        super().__init__()

    def get_name(self) -> str:
        """Get the name of the attribute.

        Returns:
            str: The name "RecordId"
        """
        return self.NAME

    def get_aliases(self) -> List[str]:
        """Get the aliases for the attribute.

        Returns:
            List[str]: A list containing the aliases for this attribute
        """
        return self.ALIASES.copy()
