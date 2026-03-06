"""
Copyright (c) Truveta. All rights reserved.
"""

from datetime import date, datetime
from typing import Optional

from opentoken.attributes.validation.serializable_attribute_validator import SerializableAttributeValidator


class DateRangeValidator(SerializableAttributeValidator):
    """
    A generic validator that asserts that a date value is within an acceptable range.

    This validator checks that dates are:
    - Not before the specified minimum date (if provided)
    - Not after the specified maximum date (if provided)
    - If use_current_as_max is True, uses today's date as the maximum

    If the date is outside the specified range, the validation fails.
    """

    # Supported date formats for parsing
    POSSIBLE_INPUT_FORMATS = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%d.%m.%Y",
        # ISO 8601 timestamp formats
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
    ]

    def __init__(
        self, min_date: Optional[date] = None, max_date: Optional[date] = None, use_current_as_max: bool = False
    ):
        """
        Initialize the validator with a date range.

        Args:
            min_date: The minimum allowed date (inclusive), or None for no minimum
            max_date: The maximum allowed date (inclusive), or None for no maximum
            use_current_as_max: If True, uses today's date as the maximum date
        """
        self._min_date = min_date
        self._use_current_as_max = use_current_as_max
        self._max_date = max_date

    @property
    def min_date(self) -> Optional[date]:
        """Get the minimum allowed date."""
        return self._min_date

    @property
    def max_date(self) -> Optional[date]:
        """Get the maximum allowed date."""
        if self._use_current_as_max:
            return date.today()
        return self._max_date

    @property
    def use_current_as_max(self) -> bool:
        """Check if using current date as maximum."""
        return self._use_current_as_max

    def eval(self, value: str) -> bool:
        """
        Validate that the date value is within acceptable range.

        Args:
            value: The date string to validate

        Returns:
            True if the date is within acceptable range, False otherwise
        """
        if not value or not value.strip():
            return False

        parsed_date = self._parse_date(value.strip())
        if parsed_date is None:
            return False

        # Check minimum date if specified
        if self._min_date is not None and parsed_date < self._min_date:
            return False

        # Check maximum date
        max_date_to_check = self.max_date
        if max_date_to_check is not None and parsed_date > max_date_to_check:
            return False

        return True

    def _parse_date(self, value: str) -> Optional[date]:
        """
        Parse the date string using various supported formats.

        Args:
            value: The date string to parse

        Returns:
            Parsed date object, or None if parsing fails
        """
        for date_format in self.POSSIBLE_INPUT_FORMATS:
            try:
                parsed_datetime = datetime.strptime(value, date_format)
                return parsed_datetime.date()
            except ValueError:
                continue
        return None
