"""
Copyright (c) Truveta. All rights reserved.
"""

from abc import ABC, abstractmethod
from typing import Dict, Iterator


class TokenReader(ABC, Iterator[Dict[str, str]]):
    """
    A generic interface for a streaming token reader.

    Reads encrypted or decrypted tokens from an input source.
    """

    @abstractmethod
    def __iter__(self) -> Iterator[Dict[str, str]]:
        """Return the iterator object."""
        pass

    @abstractmethod
    def __next__(self) -> Dict[str, str]:
        """
        Retrieve the next token row from an input source.

        Example token map:
        {
            'RecordId': '2ea45fee-90c3-494a-a503-36022c9e1281',
            'RuleId': 'T1',
            'Token': '812f4cec4ff577e90f6a0dce95361be59b3208892ffe46ce970649e35c1e923d'
        }

        Returns:
            A token dictionary containing RuleId, Token, and RecordId.
        """
        pass

    @abstractmethod
    def close(self):
        """Close the reader and release any resources."""
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
