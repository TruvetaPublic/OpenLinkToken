# SPDX-License-Identifier: MIT

import re
from typing import List

from openlinktoken.attributes.base_attribute import BaseAttribute
from openlinktoken.attributes.utilities.attribute_utilities import AttributeUtilities
from openlinktoken.attributes.validation.not_starts_with_validator import NotStartsWithValidator
from openlinktoken.attributes.validation.regex_validator import RegexValidator


class CanadianPostalCodeAttribute(BaseAttribute):
    """
    Represents Canadian postal codes.

    This class handles validation and normalization of Canadian postal codes,
    supporting the A1A 1A1 format (letter-digit-letter space digit-letter-digit).
    """

    NAME = "CanadianPostalCode"
    ALIASES = [NAME, "CanadianZipCode"]

    # Regular expression pattern for validating Canadian postal codes
    # Supports 3-character (ZIP-3), partial (4-5 char), and full 6-character formats
    CANADIAN_POSTAL_REGEX = r"^\s*[A-Za-z]\d[A-Za-z](\s?\d([A-Za-z]\d?)?)?\s*$"

    # Full 6-character invalid postal codes
    INVALID_ZIP_CODES = {
        # 6-character Canadian postal code placeholders
        "A1A 1A1",
        "X0X 0X0",
        "Y0Y 0Y0",
        "Z0Z 0Z0",
        "A0A 0A0",
        "B1B 1B1",
        "C2C 2C2",
        "K1A 0A6",  # Canadian government address
        "H0H 0H0",  # Santa Claus postal code
    }

    # 3-character codes that are invalid when standalone (not when part of full codes)
    INVALID_ZIP3_CODES = {
        "K1A",  # Canadian government
        "M7A",  # Government of Ontario
        "H0H",  # Santa Claus
    }

    def __init__(self, min_length: int = 6):
        """
        Initialize CanadianPostalCodeAttribute.

        Args:
            min_length: Minimum length for postal codes (default: 6)
        """
        validation_rules = []
        super().__init__(validation_rules)
        self.min_length = min_length
        self.regex_validator = RegexValidator(self.CANADIAN_POSTAL_REGEX)
        self.not_starts_with_validator = NotStartsWithValidator(self.INVALID_ZIP_CODES)

    def validate(self, value: str) -> bool:
        """
        Validate the Canadian postal code value.

        Args:
            value: The postal code value to validate

        Returns:
            True if the value is a valid Canadian postal code, False otherwise
        """
        if value is None:
            return False

        # First, check the regex pattern on the ORIGINAL value
        # This ensures the format is valid before normalization
        if not self.regex_validator.eval(value):
            return False

        # Normalize the value to ensure idempotency
        # This converts to uppercase and formats consistently
        normalized_value = self.normalize(value)

        # Validate the NORMALIZED value against the full invalid codes
        # This ensures "k1a 0a6" and "K1A 0A6" are treated consistently
        for invalid_code in self.INVALID_ZIP_CODES:
            if normalized_value.upper() == invalid_code.upper():
                return False

        # Additionally check for codes starting with invalid ZIP-3 prefixes
        # But ONLY for padded partial codes (normalized length is 7 and ends with padding)
        # Full 6-character codes (without padding) are checked against the exact invalid list above
        if len(normalized_value) == 7 and " " in normalized_value:
            zip3 = normalized_value[:3].upper()
            for invalid_zip3 in self.INVALID_ZIP3_CODES:
                if zip3 == invalid_zip3.upper():
                    # Check if this is a padded partial code
                    # Padded codes end with "000" (3-char), "A0" (4-char), or "0" (5-char after last letter)
                    last_part = normalized_value[4:]  # After "K1A "
                    if (
                        last_part == "000"  # K1A → K1A 000
                        or re.match(r"\dA0$", last_part)  # K1A1 → K1A 1A0
                        or re.match(r"\d[A-Z]0$", last_part)
                    ):  # K1A1A → K1A 1A0
                        return False

        return True

    def get_name(self) -> str:
        return self.NAME

    def get_aliases(self) -> List[str]:
        return self.ALIASES.copy()

    def normalize(self, value: str) -> str:
        """
        Normalize a Canadian postal code to standard A1A 1A1 format.

        For Canadian postal codes:
        - Codes shorter than min_length are rejected (return original)
        - 3-character format (e.g., "J1X") is padded with " 000" to create full format
          (e.g., "J1X 000") if min_length <= 3
        - 4-character format (e.g., "J1X1") is padded with "A0" to create full format
          (e.g., "J1X 1A0") if min_length <= 4
        - 5-character format (e.g., "J1X1A") is padded with "0" to create full format
          (e.g., "J1X 1A0") if min_length <= 5
        - 6-character format returns uppercase format with space (e.g., "k1a0a6" becomes "K1A 0A6")
        If the input value is null or doesn't match Canadian postal pattern, the original
        trimmed value is returned.
        """
        if not value:
            return value

        trimmed = AttributeUtilities.remove_whitespace(value.strip())

        # Check if it's a 3-character Canadian postal code (ZIP-3) - pad with " 000" if min_length allows
        if re.match(r"^[A-Za-z]\d[A-Za-z]$", trimmed):
            if self.min_length <= 3:
                upper = trimmed.upper()
                return f"{upper} 000"
            # If min_length > 3, reject this by returning original
            return value.strip()

        # Check if it's a 4-character partial postal code (e.g., "A1A1") - pad with "A0" if min_length allows
        if re.match(r"^[A-Za-z]\d[A-Za-z]\d$", trimmed):
            if self.min_length <= 4:
                upper = trimmed.upper()
                return f"{upper[:3]} {upper[3]}A0"
            # If min_length > 4, reject this by returning original
            return value.strip()

        # Check if it's a 5-character partial postal code (e.g., "A1A1A") - pad with "0" if min_length allows
        if re.match(r"^[A-Za-z]\d[A-Za-z]\d[A-Za-z]$", trimmed):
            if self.min_length <= 5:
                upper = trimmed.upper()
                return f"{upper[:3]} {upper[3:]}0"
            # If min_length > 5, reject this by returning original
            return value.strip()

        # Check if it's a Canadian postal code (6 alphanumeric characters)
        if re.match(r"[A-Za-z]\d[A-Za-z]\d[A-Za-z]\d", trimmed):
            upper = trimmed.upper()
            return f"{upper[:3]} {upper[3:6]}"

        # For values that don't match Canadian postal patterns, return trimmed original
        return value.strip()
