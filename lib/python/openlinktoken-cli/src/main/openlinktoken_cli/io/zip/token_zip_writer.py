# SPDX-License-Identifier: MIT

import csv
import io
import os
import zipfile
from pathlib import Path
from typing import Dict

from openlinktoken_cli.io.token_writer import TokenWriter
from openlinktoken_cli.processor.token_constants import TokenConstants


class TokenZipWriter(TokenWriter):
    """Writes tokens to a CSV file inside a ZIP archive."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        output_dir = os.path.dirname(file_path) if os.path.dirname(file_path) else "."
        os.makedirs(output_dir, exist_ok=True)

        self.zip_file = zipfile.ZipFile(file_path, mode="w", compression=zipfile.ZIP_DEFLATED)
        inner_name = f"{Path(file_path).stem}.csv"
        self._raw_stream = self.zip_file.open(inner_name, mode="w")
        self._text_stream = io.TextIOWrapper(self._raw_stream, encoding="utf-8", newline="")
        self.csv_writer = csv.DictWriter(
            self._text_stream,
            fieldnames=[TokenConstants.RULE_ID, TokenConstants.TOKEN, TokenConstants.RECORD_ID],
            lineterminator="\n",
        )
        self.csv_writer.writeheader()

    def write_token(self, data: Dict[str, str]) -> None:
        self.csv_writer.writerow(
            {
                TokenConstants.RULE_ID: data.get(TokenConstants.RULE_ID, ""),
                TokenConstants.TOKEN: data.get(TokenConstants.TOKEN, ""),
                TokenConstants.RECORD_ID: data.get(TokenConstants.RECORD_ID, ""),
            }
        )
        self._text_stream.flush()

    def close(self):
        if hasattr(self, "_text_stream") and self._text_stream:
            self._text_stream.flush()
            self._text_stream.close()
        if hasattr(self, "zip_file") and self.zip_file:
            self.zip_file.close()
