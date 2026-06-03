# SPDX-License-Identifier: MIT

import zipfile
from pathlib import Path


def bundle_into_zip(zip_output_path: str, *file_paths: str) -> None:
    """Bundle files into a zip archive, using each file's basename as the entry name."""
    zip_path = Path(zip_output_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_output_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in file_paths:
            archive.write(file_path, arcname=Path(file_path).name)
