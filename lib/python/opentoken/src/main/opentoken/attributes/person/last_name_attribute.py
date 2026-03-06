"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import List

from opentoken.attributes.base_attribute import BaseAttribute
from opentoken.attributes.utilities.attribute_utilities import AttributeUtilities
from opentoken.attributes.validation.not_in_validator import NotInValidator
from opentoken.attributes.validation.regex_validator import RegexValidator


class LastNameAttribute(BaseAttribute):
    """
    Represents the last name of a person.

    This class extends BaseAttribute and provides functionality for working with
    last name fields. It recognizes "LastName" and "Surname" as valid aliases for
    this attribute type.

    The attribute normalizes values by removing diacritics, generational suffixes,
    and non-alphabetic characters. It validates that names are either:
    - Longer than 2 characters, or
    - Exactly 2 characters containing at least one vowel (including names with two vowels), or
    - The specific last name "Ng"
    """

    NAME = "LastName"
    ALIASES = [NAME, "Surname"]

    # Regular expression pattern for validating last names.
    #
    # This pattern matches:
    #  - Any name with 3 or more characters (including spaces within)
    #  - 2-character names with at least one vowel (consonant+vowel, vowel+consonant, or two vowels)
    #  - The special case "Ng" (case-insensitive)
    #  - Allows optional leading and trailing whitespace
    #
    # Breakdown of the regex:
    #   ^\s*                                 Start of string, optional leading whitespace
    #   (?:                                  Start of non-capturing group:
    #     (?:.{3,})                          Any name with 3+ characters
    #     |                                  OR
    #     (?:[^aeiouAEIOU\s][aeiouAEIOU])    2-char: consonant + vowel (no spaces)
    #     |                                  OR
    #     (?:[aeiouAEIOU][^aeiouAEIOU\s])    2-char: vowel + consonant (no spaces)
    #     |                                  OR
    #     (?:[aeiouAEIOU]{2})                2-char: two vowels (no spaces)
    #     |                                  OR
    #     (?:[Nn][Gg])                       Special case: "Ng" (case-insensitive)
    #   )
    #   \s*$                                 Optional trailing whitespace, end of string
    LAST_NAME_REGEX = (
        r"^\s*(?:(?:.{3,})|(?:[^aeiouAEIOU\s][aeiouAEIOU])|"
        r"(?:[aeiouAEIOU][^aeiouAEIOU\s])|(?:[aeiouAEIOU]{2})|(?:[Nn][Gg]))\s*$"
    )

    def __init__(self):
        """Initialize the LastNameAttribute with validation rules."""
        validation_rules = [NotInValidator(AttributeUtilities.COMMON_PLACEHOLDER_NAMES)]
        super().__init__(validation_rules)
        self.regex_validator = RegexValidator(self.LAST_NAME_REGEX)

    def validate(self, value: str) -> bool:
        """
        Validate the last name value.

        Args:
            value: The last name value to validate

        Returns:
            True if the value is a valid last name, False otherwise
        """
        if value is None:
            return False

        # First, check placeholder values on the ORIGINAL value using built-in validators
        # This ensures "N/A", "<masked>", etc. are properly rejected
        if not super().validate(value):
            return False

        # Normalize the value for pattern matching
        # This ensures that validate(normalize(x)) == validate(normalize(normalize(x)))
        normalized_value = self.normalize(value)

        # Reject single letters after normalization
        if len(normalized_value) == 1:
            return False

        # Check that normalized value is not a placeholder
        # This ensures idempotency: values like "TEST16" normalize to "TEST" which is a placeholder
        if not super().validate(normalized_value):
            return False

        # Validate the normalized value against the regex pattern
        # Use the pre-created regex validator instance to avoid creating new instances on each call
        return self.regex_validator.eval(normalized_value)

    def get_name(self) -> str:
        """
        Get the name of the attribute.

        Returns:
            The name of the attribute ("LastName")
        """
        return self.NAME

    def get_aliases(self) -> List[str]:
        """
        Get the aliases for the attribute.

        Returns:
            List of aliases for the attribute (["LastName", "Surname"])
        """
        return self.ALIASES.copy()

    def normalize(self, value: str) -> str:
        """
        Normalize the last name value.

        This method performs the following normalization steps:
        1. Remove diacritics (accents)
        2. Remove generational suffixes (Jr, Sr, III, etc.)
        3. Remove non-alphabetic characters (spaces, dashes, etc.)

        Args:
            value: The last name value to normalize

        Returns:
            The normalized last name value
        """

        # Step 1: Remove diacritics (é → e, ñ → n, etc.)
        normalized_value = AttributeUtilities.normalize_diacritics(value)

        # Step 2: Remove generational suffixes (Jr, Sr, III, etc.)
        value_without_suffix = AttributeUtilities.GENERATIONAL_SUFFIX_PATTERN.sub("", normalized_value)

        # If the generational suffix removal doesn't result in an empty string,
        # continue with the value without suffix, otherwise use the value with suffix
        # as last name
        if value_without_suffix.strip():
            normalized_value = value_without_suffix

        # Step 4: Remove dashes, spaces and other non-alphanumeric characters
        normalized_value = AttributeUtilities.NON_ALPHABETIC_PATTERN.sub("", normalized_value)

        return normalized_value
