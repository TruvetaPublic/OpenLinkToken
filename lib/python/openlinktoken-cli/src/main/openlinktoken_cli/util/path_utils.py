from pathlib import Path
from typing import Optional


def generate_auto_output_path(input_path: str, subcommand: str, extension_override: Optional[str] = None) -> str:
    """
    Generates an automatic output filename based on the input path and subcommand.

    Args:
        input_path: The original file path.
        subcommand: The name of the CLI subcommand (e.g., 'tokenize').
        extension_override: An optional explicit extension to use (e.g., 'zip' for package).

    Returns:
        A string representing the new output path.
    """
    path = Path(input_path)
    stem = path.stem

    if extension_override:
        extension = f".{extension_override.lstrip('.')}"
    else:
        # Default suffix for tokenize/decrypt etc is '_tokenized' or similar?
        # The requirement says "auto-generate output filename from the input"
        # Example in issue: "demo.csv" + subcommand "tokenized" => "demo_tokenized.csv"
        # Let's use a logic that respects context.
        if subcommand == "package":
            return str(path.with_name(f"{path.stem}_packaged.zip"))

        extension = path.suffix if path.suffix else ""
        if not extension and subcommand in ["tokenize", "encrypt", "decrypt"]:
            # Default to something safe if no extension?
            # But usually input has an extension.
            pass

    if not extension:
        # Fallback for files without suffix
        return str(path.with_name(f"{stem}_{subcommand}"))

    return str(path.with_name(f"{stem}_{subcommand}{extension}"))


def get_auto_output_path(input_path: str, subcommand: str) -> str:
    """Helper that simplifies the logic specifically for our CLI needs."""
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
