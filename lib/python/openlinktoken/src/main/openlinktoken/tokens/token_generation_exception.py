"""
Copyright (c) Truveta. All rights reserved.
"""


class TokenGenerationException(Exception):
    """Exception raised when token generation fails."""

    def __init__(self, message: str, cause: Exception = None):
        """
        Initialize the exception.

        Args:
            message: The error message.
            cause: The underlying cause of the exception.
        """
        super().__init__(message)
        self.cause = cause
