# SPDX-License-Identifier: MIT
"""
Utility class for masking sensitive strings in CLI commands.
"""


class StringMaskingUtil:
    """Utility methods for masking sensitive strings."""

    NULL_MASK = "<null>"
    DEFAULT_MASK = "***"

    @staticmethod
    def mask_string(input_str: str | None) -> str:
        """
        Mask a sensitive string for logging.

        - None values are masked as "<null>"
        - Strings with 3 or fewer characters are masked as "***"
        - Longer strings show first 3 characters followed by asterisks

        Args:
            input_str: The string to mask.

        Returns:
            The masked string.
        """
        if input_str is None:
            return StringMaskingUtil.NULL_MASK
        if len(input_str) <= 3:
            return StringMaskingUtil.DEFAULT_MASK
        return input_str[:3] + "*" * (len(input_str) - 3)


def mask_string(input_str: str | None) -> str:
    """Mask a sensitive string for logging."""
    return StringMaskingUtil.mask_string(input_str)
