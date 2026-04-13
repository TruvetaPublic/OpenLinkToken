"""
Copyright (c) Truveta. All rights reserved.
"""

import argparse

from openlinktoken_cli.extension import OpenLinkTokenExtension


class HelloWorldExtension(OpenLinkTokenExtension):
    """Reference OpenLinkToken extension that demonstrates the extension interface."""

    @property
    def command_name(self) -> str:
        """Return the top-level subcommand name owned by this extension."""
        return "hello-world"

    @property
    def description(self) -> str:
        """Return a short human-readable description of this extension."""
        return "OpenLinkToken hello-world reference extension"

    @property
    def version(self) -> str:
        """Return the SemVer version string for this extension."""
        return "1.0.0"

    def register_subcommand(self, subparsers: argparse._SubParsersAction) -> None:
        """Register the ``hello-world`` parser and its sub-subcommands."""
        parser = subparsers.add_parser(self.command_name, help=self.description)
        sub = parser.add_subparsers(dest="hello_world_subcommand")

        hello = sub.add_parser("hello", help="Print a hello greeting")
        hello.add_argument("--name", required=True, help="Name to greet")
        hello.set_defaults(func=HelloWorldExtension._hello)

        bye = sub.add_parser("bye", help="Print a goodbye greeting")
        bye.add_argument("--name", required=True, help="Name to bid farewell")
        bye.set_defaults(func=HelloWorldExtension._bye)

        parser.set_defaults(func=lambda args: (parser.print_help(), 0)[1])

    @staticmethod
    def _hello(args) -> int:
        """Print a personalised hello greeting and return exit code 0."""
        print(f"Hello, {args.name}")
        return 0

    @staticmethod
    def _bye(args) -> int:
        """Print a personalised goodbye greeting and return exit code 0."""
        print(f"Bye, {args.name}")
        return 0
