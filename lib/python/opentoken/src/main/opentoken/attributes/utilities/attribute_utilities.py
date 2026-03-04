"""
Copyright (c) Truveta. All rights reserved.
"""

import re
import unicodedata
from typing import Set


class AttributeUtilities:
    """
    This class includes functions such as normalizing accents,
    standardizing formats, and other attribute-related transformations.
    """

    # Pattern that matches any character that is not an alphabetic character (a-z or A-Z).
    # Used for removing or identifying non-alphabetic characters in strings.
    NON_ALPHABETIC_PATTERN = re.compile(r"[^a-zA-Z]")

    # Pattern that matches one or more whitespace characters.
    # This includes spaces, tabs, line breaks, and other Unicode whitespace.
    #
    # Examples:
    # " " -> single space
    # "\t" -> tab
    # "\n" -> newline
    # "\r\n" -> carriage return + newline
    # "   " -> multiple spaces
    WHITESPACE_PATTERN = re.compile(r"\s+")

    # Pattern that matches generational suffixes at the end of a string.
    # Matches case-insensitive suffixes after a whitespace character.
    #
    # Matches the following types of generational suffixes:
    # - Jr, Jr., Junior
    # - Sr, Sr., Senior
    # - Roman numerals (I, II, III, IV, V, VI, VII, VIII, IX, X)
    # - Ordinal numbers (1st, 2nd, 3rd, 4th, etc.)
    #
    # Examples:
    # "John Smith Jr" -> matches " Jr"
    # "Jane Doe Sr." -> matches " Sr."
    # "Robert Johnson III" -> matches " III"
    # "Thomas Wilson 2nd" -> matches " 2nd"
    GENERATIONAL_SUFFIX_PATTERN = re.compile(
        r"(?i)\s+(jr\.?|junior|sr\.?|senior|I{1,3}|IV|V|VI{0,3}|IX|X|\d+(st|nd|rd|th))$"
    )

    # A set of common placeholder names used to identify non-identifying or
    # placeholder text in data fields.
    #
    # This set includes various standard terms and phrases that are commonly used
    # as placeholders in data records when actual values are unknown, not applicable,
    # unavailable, or intentionally masked.
    # These placeholders might be found in production data but don't represent
    # actual identifying information.
    #
    # These values should be treated as non-identifying data and may need special
    # handling during data processing, anonymization, or when analyzing data quality.
    COMMON_PLACEHOLDER_NAMES: Set[str] = {
        "Unknown",  # Placeholder for unknown last names
        "N/A",  # Not applicable
        "None",  # No last name provided
        "Test",  # Commonly used in testing scenarios
        "Sample",  # Sample data placeholder
        "Donor",  # Placeholder for donor records
        "Patient",  # Placeholder for patient records
        "Automation Test",  # Placeholder for automation tests
        "Automationtest",  # Another variation of automation test
        "patient not found",  # Placeholder for cases where patient data is not found
        "patientnotfound",  # Another variation of patient not found
        "<masked>",  # Placeholder for masked data
        "Anonymous",  # Placeholder for anonymous records
        "zzztrash",  # Placeholder for test or trash data
        "Missing",  # Placeholder for missing data
        "Unavailable",  # Placeholder for unavailable data
        "Not Available",  # Placeholder for data not available
        "NotAvailable",  # Placeholder for data not available (no spaces)
    }

    def __init__(self):
        """Prevent instantiation of utility class."""
        raise RuntimeError("This is a utility class and cannot be instantiated")

    @staticmethod
    def normalize_diacritics(value: str) -> str:
        """
        Removes diacritic marks from the given string.

        This method performs the following steps:
        1. Trims the input string
        2. Normalizes the string using NFD form, which separates characters from
           their diacritical marks
        3. Removes all diacritical marks using Unicode category filtering

        Args:
            value: The string from which to remove diacritical marks

        Returns:
            A new string with all diacritical marks removed

        Raises:
            AttributeError: If value is None
        """
        if value is None:
            raise AttributeError("Value cannot be None")

        trimmed_value = value.strip()

        # Normalize to NFD (decomposed form) and filter out combining characters
        normalized = unicodedata.normalize("NFD", trimmed_value)
        return "".join(c for c in normalized if unicodedata.category(c) != "Mn")

    @staticmethod
    def remove_whitespace(value: str) -> str:
        """
        Remove all whitespace characters from the string.

        Args:
            value: The string from which to remove whitespace

        Returns:
            String with all whitespace removed
        """
        if value is None:
            return None

        return AttributeUtilities.WHITESPACE_PATTERN.sub("", value)

    @staticmethod
    def remove_non_alphabetic_characters(value: str) -> str:
        """
        Remove all non-alphabetic characters from the string.

        Args:
            value: The string from which to remove non-alphabetic characters

        Returns:
            String with only alphabetic characters (a-z, A-Z)
        """
        if value is None:
            return None

        return AttributeUtilities.NON_ALPHABETIC_PATTERN.sub("", value)

    @staticmethod
    def remove_generational_suffix(value: str) -> str:
        """
        Remove generational suffixes (Jr, Sr, III, etc.) from the string.

        Args:
            value: The string from which to remove generational suffixes

        Returns:
            String with generational suffixes removed
        """
        if value is None:
            return None

        return AttributeUtilities.GENERATIONAL_SUFFIX_PATTERN.sub("", value).strip()

    @staticmethod
    def get_common_placeholder_names() -> Set[str]:
        """
        Get a copy of the common placeholder names set.

        Returns:
            A copy of the set containing common placeholder names
        """
        return AttributeUtilities.COMMON_PLACEHOLDER_NAMES.copy()
