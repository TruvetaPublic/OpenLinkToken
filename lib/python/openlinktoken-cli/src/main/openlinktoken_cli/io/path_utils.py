# SPDX-License-Identifier: MIT

from pathlib import Path


def ensure_parent_directory(file_path: str) -> None:
    """Ensure the parent directory for a file path exists."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
