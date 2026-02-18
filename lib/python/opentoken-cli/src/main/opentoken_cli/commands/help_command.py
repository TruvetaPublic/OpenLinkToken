"""
Copyright (c) Truveta. All rights reserved.
"""

import logging

logger = logging.getLogger(__name__)


class HelpCommand:
    """
    Help command for displaying help information about commands.
    """

    @staticmethod
    def register_subcommand(subparsers):
        """Register the help subcommand with the argument parser."""
        help_parser = subparsers.add_parser(
            "help",
            help="Display help information about the specified command",
            description="Display help information about OpenToken commands",
        )
        help_parser.add_argument(
            "subcommand",
            nargs="?",
            help="Command to show help for (tokenize, encrypt, decrypt, package)",
        )
        help_parser.set_defaults(func=HelpCommand.execute)

    @staticmethod
    def execute(args):
        """Execute the help command."""
        from opentoken_cli.commands import OpenTokenCommand
        
        parser = OpenTokenCommand.create_parser()
        
        if args.subcommand:
            # Show help for specific subcommand
            # Parse with the subcommand and --help flag
            try:
                parser.parse_args([args.subcommand, "--help"])
            except SystemExit:
                # argparse prints help and exits, which is expected
                pass
            return 0
        else:
            # Show general help
            parser.print_help()
            return 0
