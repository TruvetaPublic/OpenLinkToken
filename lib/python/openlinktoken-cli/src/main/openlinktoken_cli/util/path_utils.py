"""Utility for generating automatic output file paths."""

from pathlib import Path


def get_auto_output_path(input_path: str, subcommand: str) -> str:
    """Generate an automatic output filename from the input path and subcommand.

    Args:
        input_path: The original input file path (e.g., 'data.csv').
        subcommand: The CLI subcommand name that determines the suffix
             (e.g., 'tokenize' → '_tokenized', 'encrypt' → '_encrypted',
              'decrypt' → '_decrypted', 'package' → '_packaged.zip').

    Returns:
        A new file path string with the input stem replaced by
          <stem>_<suffix>. For example, 'customers.csv' with subcommand
          'tokenize' becomes 'customers_tokenized.csv'. Files without an
        extension (e.g. 'README') become 'README_tokenized'.

    Examples:
         >>> get_auto_output_path("data.csv", "tokenize")
         'data_tokenized.csv'
         >>> get_auto_output_path("records.parquet", "package")
         'records_packaged.zip'
     """
     # For package, we want .zip
    if subcommand == "package":
        return str(Path(input_path).with_name(f"{Path(input_path).stem}_packaged.zip"))

     # Mapping of subcommands to their preferred suffixes for better readability
    suffix_map = {"tokenize": "tokenized", "encrypt": "encrypted", "decrypt": "decrypted"}

    suffix = suffix_map.get(subcommand, subcommand)
    path = Path(input_path)
    if not path.suffix:
        return str(path.with_name(f"{path.stem}_{suffix}"))

    return str(path.with_name(f"{path.stem}_{suffix}{path.suffix}"))
