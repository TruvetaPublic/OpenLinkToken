# SPDX-License-Identifier: MIT

from pathlib import Path


def ensure_parent_directory(file_path: str) -> Path:
    """Create the parent directory for a file path when needed."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
