# src/openlinktoken/attributes/person/social_security_number_attribute.py
# SPDX-License-Identifier: MIT

import locale
import re
from typing import List

from openlinktoken.attributes.base_attribute import BaseAttribute
from openlinktoken.attributes.utilities.attribute_utilities import AttributeUtilities
from openlinktoken.attributes.validation.not_in_validator import NotInValidator
from openlinktoken.attributes.validation.regex_validator import RegexValidator


class SocialSecurityNumberAttribute(BaseAttribute):
    """
    Represents the social security number attribute.

    This class extends BaseAttribute and provides functionality for working with
    social security number fields. It recognizes "SocialSecurityNumber" and
    "NationalIdentificationNumber" as valid aliases for this attribute type.

    The attribute performs normalization on input values, converting them to a
    standard format (xxx-xx-xxxx).
    """

    NAME = "SocialSecurityNumber"
    ALIASES = [NAME, "NationalIdentificationNumber"]
    DASH = "-"
    SSN_FORMAT = "{:09d}"

    MIN_SSN_LENGTH = 7
    SSN_LENGTH = 9

    # Get decimal separator for current locale
    try:
        DECIMAL_SEPARATOR = locale.localeconv()["decimal_point"]
    except Exception:
        DECIMAL_SEPARATOR = "."

    # Regular expression to validate Social Security Numbers
    SSN_REGEX = (
        rf"^(?:\d{{7,9}}(?:[{DECIMAL_SEPARATOR}]0*)?)$"
        rf"|(?:^(?!000|666|9\d\d)(\d{{3}})-?(?!00)(\d{{2}})-?(?!0000)(\d{{4}})$)"
    )

    DIGITS_ONLY_PATTERN = re.compile(r"\d+")

    # SSNs excluded based on real-life data patterns.
    INVALID_SSNS = {
        "111-11-1111",
        "222-22-2222",
        "333-33-3333",
        "444-44-4444",
        "555-55-5555",
        "777-77-7777",
        "888-88-8888",
        "001-01-0001",
        "001-01-0101",
        "001-01-9999",
        "001-10-0110",
        "001-11-1111",
        "001-12-2334",
        "001-23-4567",
        "007-77-7777",
        "010-10-1010",
        "011-11-1111",
        "012-34-5678",
        "022-22-2222",
        "055-55-5555",
        "077-77-7777",
        "087-65-4321",
        "088-88-8888",
        "098-76-5432",
        "099-99-9999",
        "100-10-1000",
        "111-11-1112",
        "111-11-1234",
        "111-11-9999",
        "111-22-1111",
        "111-22-2333",
        "111-22-3333",
        "121-21-2121",
        "123-12-1234",
        "123-12-3123",
        "123-45-1234",
        "123-45-6788",
        "123-45-6789",
        "123-45-6798",
        "123-45-6879",
        "123-45-6987",
        "123-45-7896",
        "199-99-9999",
        "222-33-4444",
        "299-99-9999",
        "399-99-9999",
        "454-54-5454",
        "499-99-9999",
        "599-99-9999",
        "699-99-9999",
        "799-99-9999",
        "899-99-9999",
    }

    def __init__(self):
        validation_rules = [NotInValidator(self.INVALID_SSNS), RegexValidator(self.SSN_REGEX)]
        super().__init__(validation_rules)

    def get_name(self) -> str:
        return self.NAME

    def get_aliases(self) -> List[str]:
        return self.ALIASES.copy()

    def normalize(self, original_value: str) -> str:
        """
        Normalize the social security number value. Remove any dashes and format the
        value as xxx-xx-xxxx. If not possible return the original but trimmed value.
        """
        if not original_value:
            return original_value

        # Remove any whitespace
        trimmed_value = AttributeUtilities.remove_whitespace(original_value.strip())

        # Remove any dashes for now
        normalized_value = trimmed_value.replace(self.DASH, "")

        # Remove decimal point/separator and all following numbers if present
        decimal_index = normalized_value.find(self.DECIMAL_SEPARATOR)
        if decimal_index != -1:
            normalized_value = normalized_value[:decimal_index]

        # Check if the string contains only digits
        if not self.DIGITS_ONLY_PATTERN.fullmatch(normalized_value):
            return original_value  # Return original if contains non-numeric characters

        if len(normalized_value) < self.MIN_SSN_LENGTH or len(normalized_value) > self.SSN_LENGTH:
            return original_value  # Invalid length for SSN

        normalized_value = self._pad_with_zeros(normalized_value)
        return self._format_with_dashes(normalized_value)

    def _pad_with_zeros(self, ssn: str) -> str:
        """Pad SSN with leading zeros if between 7-8 digits."""
        if self.MIN_SSN_LENGTH <= len(ssn) < self.SSN_LENGTH:
            return self.SSN_FORMAT.format(int(ssn))
        return ssn

    def _format_with_dashes(self, value: str) -> str:
        """Format 9-digit SSN with dashes (123-45-6789)."""
        if len(value) == self.SSN_LENGTH:
            area_number = value[:3]
            group_number = value[3:5]
            serial_number = value[5:]
            return self.DASH.join([area_number, group_number, serial_number])
        return value
