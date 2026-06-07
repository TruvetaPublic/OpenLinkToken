# SPDX-License-Identifier: MIT

from pathlib import Path


def ensure_parent_directory(file_path: str) -> Path:
    """Create the parent directory for a file path when needed."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def auto_generate_output_path(input_path: str, suffix: str, ext: str | None = None) -> str:
    """Generate an output file path from an input path by appending a suffix.

    The output is placed in the same directory as the input file.

    Args:
        input_path: Path to the input file.
        suffix: Suffix to append to the input stem (e.g. ``"_tokenized"``).
        ext: File extension for the output, including the leading dot
            (e.g. ``".zip"``).  When ``None`` the input extension is reused.

    Returns:
        The generated output path string.

    Examples:
        >>> auto_generate_output_path("data.csv", "_tokenized")
        'data_tokenized.csv'
        >>> auto_generate_output_path("data.parquet", "_packaged", ext=".zip")
        'data_packaged.zip'
    """
    path = Path(input_path)
    out_ext = ext if ext is not None else path.suffix
    return str(path.parent / f"{path.stem}{suffix}{out_ext}")
