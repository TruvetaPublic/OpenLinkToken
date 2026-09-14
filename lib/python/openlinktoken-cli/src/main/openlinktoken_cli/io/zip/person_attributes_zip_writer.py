# SPDX-License-Identifier: MIT

import csv
import io
import json
import logging
import zipfile
from pathlib import Path
from typing import Any, Dict

from openlinktoken_cli.io.path_utils import ensure_parent_directory
from openlinktoken_cli.io.person_attributes_writer import PersonAttributesWriter

logger = logging.getLogger(__name__)


class PersonAttributesZipWriter(PersonAttributesWriter):
    """
    Writes person attribute token records to a ZIP archive.

    The archive contains two entries:
    - ``{stem}.csv``           — the token output rows
    - ``{stem}.metadata.json`` — the run metadata

    Usage pattern::

        with PersonAttributesZipWriter("output.zip") as writer:
            for row in rows:
                writer.write_attributes(row)
            writer.build_zip(metadata_map)

    ``build_zip`` must be called before the context manager exits so that both
    the CSV and the metadata are bundled together. Calling ``close()`` without
    first calling ``build_zip`` discards all buffered data — no file is written.
    """

    def __init__(self, zip_path: str):
        """
        Initialize the writer for the given ZIP output path.

        Args:
            zip_path: Absolute or relative path for the output ``.zip`` file.
        """
        self._zip_path = zip_path
        self._stem = Path(zip_path).stem
        self._buffer = io.StringIO()
        self._csv_writer = csv.writer(self._buffer, lineterminator="\n")
        self._header_written = False
        self._built = False

    @property
    def zip_path(self) -> str:
        """The path of the ZIP file that will be written."""
        return self._zip_path

    def write_attributes(self, data: Dict[str, str]) -> None:
        """
        Buffer one token output row.

        The first call writes the CSV header derived from the dict keys;
        subsequent calls write data rows only.

        Args:
            data: Ordered mapping of column name to value.

        Raises:
            RuntimeError: If called after ``build_zip()`` has already been called.
            IOError: If writing to the in-memory buffer fails.
        """
        if self._built:
            raise RuntimeError("Cannot write after build_zip() has been called")
        try:
            if not self._header_written:
                self._csv_writer.writerow(data.keys())
                self._header_written = True
            self._csv_writer.writerow(data.values())
        except IOError as e:
            logger.error("Error buffering CSV row: %s", e)
            raise

    def build_zip(self, metadata_map: Dict[str, Any]) -> str:
        """
        Write the ZIP archive containing the token CSV and metadata JSON.

        Must be called once after all rows have been written and before
        ``close()`` is invoked (i.e., while still inside the context-manager
        block).

        Args:
            metadata_map: Metadata dict to serialize as JSON inside the ZIP.

        Returns:
            The path of the written ZIP file.

        Raises:
            IOError: If the ZIP archive cannot be created or written.
        """
        ensure_parent_directory(self._zip_path)
        csv_filename = f"{self._stem}.csv"
        metadata_filename = f"{self._stem}.metadata.json"
        try:
            with zipfile.ZipFile(self._zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(csv_filename, self._buffer.getvalue())
                zf.writestr(metadata_filename, json.dumps(metadata_map, indent=2, ensure_ascii=False))
            self._built = True
            logger.info("ZIP archive written: %s (%s, %s)", self._zip_path, csv_filename, metadata_filename)
            return self._zip_path
        except Exception as e:
            raise IOError(f"Failed to write ZIP archive to {self._zip_path}: {e}") from e

    def close(self) -> None:
        """Close and discard the in-memory CSV buffer."""
        self._buffer.close()
