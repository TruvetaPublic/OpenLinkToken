"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import List

from openlinktoken.attributes.base_attribute import BaseAttribute
from openlinktoken.attributes.validation.regex_validator import RegexValidator


class SexAttribute(BaseAttribute):
    """
    Represents an assigned sex of a person.

    This class extends BaseAttribute and provides functionality for working with
    these type of fields. It recognizes "Sex" or "Gender" as valid aliases for
    this attribute type.

    The attribute performs normalization on input values, converting them to a
    standard format (Male or Female).
    """

    NAME = "Sex"
    ALIASES = [NAME, "Gender"]

    # Regular expression pattern for validating sex/gender values
    VALIDATE_REGEX = r"^\s*([Mm](ale)?|[Ff](emale)?)\s*$"

    def __init__(self):
        validation_rules = [RegexValidator(self.VALIDATE_REGEX)]
        super().__init__(validation_rules)

    def get_name(self) -> str:
        return self.NAME

    def get_aliases(self) -> List[str]:
        return self.ALIASES.copy()

    def normalize(self, value: str) -> str:
        """Normalize sex value to 'Male' or 'Female'."""
        if not value:
            return None

        first_char = value.strip()[0].lower()
        if first_char == "m":
            return "Male"
        elif first_char == "f":
            return "Female"
        else:
            return None  # Return None if can't normalize
