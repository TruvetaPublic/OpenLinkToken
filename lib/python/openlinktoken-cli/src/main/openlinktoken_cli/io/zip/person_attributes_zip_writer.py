# SPDX-License-Identifier: MIT

import csv
import io
import os
import zipfile
from pathlib import Path
from typing import Dict

from openlinktoken_cli.io.person_attributes_writer import PersonAttributesWriter


class PersonAttributesZipWriter(PersonAttributesWriter):
    """Writes person attributes to a CSV file inside a ZIP archive."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        output_dir = os.path.dirname(file_path) if os.path.dirname(file_path) else "."
        os.makedirs(output_dir, exist_ok=True)

        self.zip_file = zipfile.ZipFile(file_path, mode="w", compression=zipfile.ZIP_DEFLATED)
        inner_name = f"{Path(file_path).stem}.csv"
        self._raw_stream = self.zip_file.open(inner_name, mode="w")
        self._text_stream = io.TextIOWrapper(self._raw_stream, encoding="utf-8", newline="")
        self.csv_writer = csv.writer(self._text_stream, lineterminator="\n")
        self.header_written = False

    def write_attributes(self, data: Dict[str, str]) -> None:
        if not self.header_written:
            self.csv_writer.writerow(data.keys())
            self.header_written = True
        self.csv_writer.writerow(data.values())

    def close(self) -> None:
        if hasattr(self, "_text_stream") and self._text_stream:
            self._text_stream.flush()
            self._text_stream.close()
        if hasattr(self, "zip_file") and self.zip_file:
            self.zip_file.close()
