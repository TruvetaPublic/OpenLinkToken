"""
Copyright (c) Truveta. All rights reserved.
"""

from abc import ABC, abstractmethod
from typing import Dict


class PersonAttributesWriter(ABC):
    """
    A generic interface for the person attributes writer.
    """

    @abstractmethod
    def write_attributes(self, data: Dict[str, str]) -> None:
        """
        Writes the provided person attributes to an output target.

        Example person attribute map:
        {
            "RecordId": "2ea45fee-90c3-494a-a503-36022c9e1281",
            "RuleId": "T1",
            "Token": "812f4cec4ff577e90f6a0dce95361be59b3208892ffe46ce970649e35c1e923d"
        }

        Args:
            data: A map of person attributes.

        Raises:
            IOError: Errors encountered while writing to the output data source.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the writer and release any resources."""
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
