"""
Copyright (c) Truveta. All rights reserved.
"""

import argparse

from opentoken_cli.extension import OpenTokenExtension


class HelloWorldExtension(OpenTokenExtension):
    """Reference OpenToken extension that demonstrates the extension interface."""

    @property
    def command_name(self) -> str:
        """Return the top-level subcommand name owned by this extension."""
        return "hello-world"

    @property
    def description(self) -> str:
        """Return a short human-readable description of this extension."""
        return "OpenToken hello-world reference extension"

    @property
    def version(self) -> str:
        """Return the SemVer version string for this extension."""
        return "1.0.0"

    def register_subcommand(self, subparsers: argparse._SubParsersAction) -> None:
        """Register the ``hello-world`` parser and its sub-subcommands."""
        parser = subparsers.add_parser(self.command_name, help=self.description)
        sub = parser.add_subparsers(dest="hello_world_subcommand")

        greet = sub.add_parser("greet", help="Print a greeting")
        greet.add_argument("--name", required=True, help="Name to greet")
        greet.set_defaults(func=HelloWorldExtension._greet)

        parser.set_defaults(func=lambda args: (parser.print_help(), 0)[1])

    @staticmethod
    def _greet(args) -> int:
        """Print a personalised greeting and return exit code 0."""
        print(f"Hello, {args.name}! — from OpenToken hello-world extension")
        return 0
