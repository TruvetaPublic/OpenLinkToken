"""
Copyright (c) Truveta. All rights reserved.
"""

import argparse
from abc import ABC, abstractmethod


class OpenTokenExtension(ABC):
    """
    Interface for OpenToken CLI extensions.

    An extension registers exactly one top-level subcommand name.
    It receives the subparsers object during CLI startup and is responsible
    for adding its own sub-subcommands underneath its top-level command.
    """

    @property
    @abstractmethod
    def command_name(self) -> str:
        """
        The top-level subcommand name this extension owns.

        Must be unique across all installed extensions and must not
        conflict with built-in OpenToken commands.

        Example: "extcmd"  → enables `opentoken extcmd ...`
        """

    @property
    @abstractmethod
    def description(self) -> str:
        """Short human-readable description shown in `opentoken --help`."""

    @property
    @abstractmethod
    def version(self) -> str:
        """SemVer string for this extension (e.g. "1.0.0")."""

    @abstractmethod
    def register_subcommand(self, subparsers: argparse._SubParsersAction) -> None:
        """
        Register the extension's argparse sub-parser(s).

        The implementation must call `subparsers.add_parser(self.command_name, ...)`
        and optionally add further sub-subcommands beneath it.
        The extension is responsible for setting `set_defaults(func=...)` on all
        leaf parsers so that OpenTokenCommand can dispatch to them via `parsed_args.func`.

        Args:
            subparsers: The shared subparsers action from the root OpenToken parser.
        """
