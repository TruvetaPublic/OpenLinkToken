"""
Copyright (c) Truveta. All rights reserved.
"""

import json
import os
from typing import Any, Dict

from opentoken.metadata import Metadata
from opentoken_cli.io.metadata_writer import MetadataWriter


class MetadataJsonWriter(MetadataWriter):
    """JSON implementation of MetadataWriter."""

    def __init__(self, output_path: str):
        """
        Initialize the metadata writer with the output path.

        Args:
            output_path: The output file path (used to derive metadata file name)
        """
        super().__init__(output_path)
        # Get the directory and base name of the output file
        output_dir = os.path.dirname(output_path)
        output_base = os.path.splitext(os.path.basename(output_path))[0]

        # Create metadata file path
        self.metadata_file_path = os.path.join(output_dir, output_base + Metadata.METADATA_FILE_EXTENSION)

    def write(self, metadata_map: Dict[str, Any]) -> None:
        """
        Write metadata to a JSON file.

        Args:
            metadata_map: The metadata to write
        """
        try:
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(self.metadata_file_path), exist_ok=True)

            # Write metadata as JSON with pretty formatting
            with open(self.metadata_file_path, "w", encoding="utf-8") as f:
                json.dump(metadata_map, f, indent=2, ensure_ascii=False)

        except Exception as e:
            raise IOError(f"Failed to write metadata to {self.metadata_file_path}: {e}")
