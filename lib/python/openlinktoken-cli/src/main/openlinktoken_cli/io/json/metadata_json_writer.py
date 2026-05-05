# SPDX-License-Identifier: MIT

import json
from typing import Any, Dict

from openlinktoken.metadata import Metadata
from openlinktoken_cli.io.metadata_writer import MetadataWriter
from openlinktoken_cli.util.path_utils import ensure_parent_directory


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
        output_path_value = ensure_parent_directory(output_path)
        output_dir = output_path_value.parent
        output_base = output_path_value.stem

        # Create metadata file path
        self.metadata_file_path = str(output_dir / f"{output_base}{Metadata.METADATA_FILE_EXTENSION}")

    def write(self, metadata_map: Dict[str, Any]) -> None:
        """
        Write metadata to a JSON file.

        Args:
            metadata_map: The metadata to write
        """
        try:
            ensure_parent_directory(self.metadata_file_path)

            # Write metadata as JSON with pretty formatting
            with open(self.metadata_file_path, "w", encoding="utf-8") as f:
                json.dump(metadata_map, f, indent=2, ensure_ascii=False)

        except Exception as e:
            raise IOError(f"Failed to write metadata to {self.metadata_file_path}: {e}")
