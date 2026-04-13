"""
Copyright (c) Truveta. All rights reserved.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class MetadataWriter(ABC):
    """Abstract base class for writing metadata."""

    def __init__(self, output_path: str):
        """
        Initialize the metadata writer.

        Args:
            output_path: The output file path
        """
        self.output_path = output_path

    @abstractmethod
    def write(self, metadata_map: Dict[str, Any]) -> None:
        """
        Write metadata to the output destination.

        Args:
            metadata_map: The metadata to write
        """
        pass
