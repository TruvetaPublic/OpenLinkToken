"""
Copyright (c) Truveta. All rights reserved.
"""

from abc import ABC, abstractmethod
from typing import Dict


class TokenWriter(ABC):
    """
    A generic interface for the token writer.

    Writes encrypted or decrypted tokens to an output target.
    """

    @abstractmethod
    def write_token(self, data: Dict[str, str]) -> None:
        """
        Writes the provided token to an output target.

        Example token map:
        {
            'RecordId': '2ea45fee-90c3-494a-a503-36022c9e1281',
            'RuleId': 'T1',
            'Token': '812f4cec4ff577e90f6a0dce95361be59b3208892ffe46ce970649e35c1e923d'
        }

        Args:
            data: A dictionary containing RuleId, Token, and RecordId.

        Raises:
            IOError: Errors encountered while writing to the output data source.
        """
        pass

    @abstractmethod
    def close(self):
        """Close the writer and release any resources."""
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
