"""
Copyright (c) Truveta. All rights reserved.
"""

import argparse
import uuid
from typing import Optional


class CommandLineArguments:
    """Processes the application's command line arguments."""

    TYPE_CSV = "csv"
    TYPE_PARQUET = "parquet"

    def __init__(self):
        """Initialize with default values."""
        self.hashing_secret: Optional[str] = None
        self.encryption_key: Optional[str] = None
        self.input_path: str = "csv"
        self.input_type: str = ""
        self.output_path: str = ""
        self.output_type: str = ""
        self.decrypt: bool = False
        self.hash_only: bool = False
        self.ring_id: str = str(uuid.uuid4())

    @classmethod
    def parse_args(cls, args: Optional[list] = None) -> 'CommandLineArguments':
        """
        Parse command line arguments and return a CommandLineArguments instance.

        Args:
            args: List of command line arguments. If None, uses sys.argv.

        Returns:
            CommandLineArguments instance with parsed values.
        """
        parser = argparse.ArgumentParser(
            description="OpenToken command line tool",
            add_help=False
            )

        parser.add_argument(
            "-h", "--hashingsecret",
            dest="hashing_secret",
            help="Hashing Secret to hash token signatures.",
            required=False,
            default=None
        )

        parser.add_argument(
            "-e", "--encryptionkey",
            dest="encryption_key",
            help="Encryption key to encrypt tokens with.",
            required=False,
            default=None
        )

        parser.add_argument(
            "-i", "--input",
            dest="input_path",
            help="Input file path.",
            required=True
        )

        parser.add_argument(
            "-t", "--type",
            dest="input_type",
            help="Input file type.",
            required=True
        )

        parser.add_argument(
            "-o", "--output",
            dest="output_path",
            help="Output file path.",
            required=True
        )

        parser.add_argument(
            "-ot", "--output-type",
            dest="output_type",
            help="Output file type if different from input.",
            required=False,
            default=""
        )

        parser.add_argument(
            "-d", "--decrypt",
            dest="decrypt",
            help="Decrypt mode. Decrypts tokens from input file.",
            action="store_true",
            required=False,
            default=False
        )

        parser.add_argument(
            "--hash-only",
            dest="hash_only",
            help="Hash-only mode. Generates tokens with hashing only, skipping encryption.",
            action="store_true",
            required=False,
            default=False
        )

        parser.add_argument(
            "--ring-id",
            dest="ring_id",
            help="Ring identifier for key management. Defaults to a random UUID if not provided.",
            required=False,
            default=str(uuid.uuid4())
        )

        parsed_args = parser.parse_args(args)

        # Create instance and populate with parsed values
        instance = cls()
        instance.hashing_secret = parsed_args.hashing_secret
        instance.encryption_key = parsed_args.encryption_key
        instance.input_path = parsed_args.input_path
        instance.input_type = parsed_args.input_type
        instance.output_path = parsed_args.output_path
        instance.output_type = parsed_args.output_type
        instance.decrypt = parsed_args.decrypt
        instance.hash_only = parsed_args.hash_only
        instance.ring_id = parsed_args.ring_id

        return instance

    # Property accessors for compatibility with Java-style getters
    @property
    def hashingSecret(self) -> Optional[str]:
        """Get the hashing secret (Java-style getter for compatibility)."""
        return self.hashing_secret

    @property
    def encryptionKey(self) -> Optional[str]:
        """Get the encryption key (Java-style getter for compatibility)."""
        return self.encryption_key

    @property
    def inputPath(self) -> str:
        """Get the input path (Java-style getter for compatibility)."""
        return self.input_path

    @property
    def inputType(self) -> str:
        """Get the input type (Java-style getter for compatibility)."""
        return self.input_type

    @property
    def outputPath(self) -> str:
        """Get the output path (Java-style getter for compatibility)."""
        return self.output_path

    @property
    def outputType(self) -> str:
        """Get the output type (Java-style getter for compatibility)."""
        return self.output_type

    @property
    def ringId(self) -> str:
        """Get the ring ID (Java-style getter for compatibility)."""
        return self.ring_id

    def __str__(self) -> str:
        """String representation of the command line arguments."""
        return (
            f"CommandLineArguments("
            f"hashing_secret={'<set>' if self.hashing_secret else None}, "
            f"encryption_key={'<set>' if self.encryption_key else None}, "
            f"input_path='{self.input_path}', "
            f"input_type='{self.input_type}', "
            f"output_path='{self.output_path}', "
            f"output_type='{self.output_type}')"
        )

    def __repr__(self) -> str:
        """Detailed representation of the command line arguments."""
        return self.__str__()
