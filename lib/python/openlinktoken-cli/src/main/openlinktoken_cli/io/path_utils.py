# SPDX-License-Identifier: MIT

from pathlib import Path


def ensure_parent_directory(file_path: str) -> Path:
    """
    Create the parent directory for a file path when needed.

    Args:
        file_path: Filesystem path to the file handled by the operation.

    Returns:
        Created the parent directory for a file path when needed.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
