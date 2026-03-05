"""
Copyright (c) Truveta. All rights reserved.
"""

import argparse
import logging
import os
import sys

from opentoken.metadata import Metadata
from opentoken_cli.util.version_checker import start_version_check

logger = logging.getLogger(__name__)


class OpenTokenCommand:
    """
    Main entry point command for OpenToken CLI with subcommands.
    Provides modern, subcommand-based interface for token operations.
    """

    VERSION = Metadata.DEFAULT_VERSION

    @staticmethod
    def show_banner():
        """
        Display the OpenToken banner for interactive sessions.
        Respects NO_COLOR environment variable and TTY detection.
        """
        # Check if we're in an interactive terminal and NO_COLOR is not set
        if not OpenTokenCommand._is_interactive() or os.getenv("NO_COLOR"):
            return

        try:
            banner = OpenTokenCommand._get_colorized_banner()
            print(banner)
        except Exception as e:
            # Silently fail banner display - it's not critical
            logger.debug(f"Could not display banner: {e}")

    @staticmethod
    def _is_interactive():
        """Check if stdout is connected to an interactive terminal."""
        return sys.stdout.isatty()

    @staticmethod
    def _get_colorized_banner():
        """Get the colorized OpenToken banner."""
        cyan = "\033[36m"
        blue = "\033[34m"
        reset = "\033[0m"

        return (
            f"{cyan}  ___                 _____     _              {reset}\n"
            f"{cyan} / _ \\ _ __   ___ _ _|_   _|__ | | _____ _ __  {reset}\n"
            f"{cyan}| | | | '_ \\ / _ \\ '_ \\| |/ _ \\| |/ / _ \\ '_ \\ {reset}\n"
            f"{cyan}| |_| | |_) |  __/ | | | | (_) |   <  __/ | | |{reset}\n"
            f"{cyan} \\___/| .__/ \\___|_| |_|_|\\___/|_|\\_\\___|_| |_|{reset}\n"
            f"{cyan}      |_|                                       {reset}\n"
            f"{blue}Privacy-Preserving Record Linkage v{OpenTokenCommand.VERSION}{reset}\n"
        )

    @staticmethod
    def create_parser():
        """Create the main argument parser with subcommands."""
        parser = argparse.ArgumentParser(
            prog="opentoken",
            description="Privacy-preserving record linkage via cryptographic tokens",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        parser.add_argument(
            "--version",
            action="version",
            version=f"OpenToken {OpenTokenCommand.VERSION}",
        )

        parser.add_argument(
            "--no-update-check",
            action="store_true",
            default=False,
            dest="no_update_check",
            help="Disable the automatic update check on startup",
        )

        subparsers = parser.add_subparsers(
            title="commands",
            description="Available commands",
            dest="command",
            help="Use 'opentoken <command> --help' for command-specific help",
        )

        # Import command modules here to avoid circular imports
        from opentoken_cli.commands.decrypt_command import DecryptCommand
        from opentoken_cli.commands.encrypt_command import EncryptCommand
        from opentoken_cli.commands.help_command import HelpCommand
        from opentoken_cli.commands.package_command import PackageCommand
        from opentoken_cli.commands.tokenize_command import TokenizeCommand
        from opentoken_cli.commands.update_command import UpdateCommand

        # Register subcommands
        HelpCommand.register_subcommand(subparsers)
        TokenizeCommand.register_subcommand(subparsers)
        EncryptCommand.register_subcommand(subparsers)
        DecryptCommand.register_subcommand(subparsers)
        PackageCommand.register_subcommand(subparsers)
        UpdateCommand.register_subcommand(subparsers)

        return parser

    @staticmethod
    def main(args=None):
        """Main entry point for the command-line application."""
        parser = OpenTokenCommand.create_parser()

        # Show banner for interactive runs (not for --help or piped output)
        # Show when no args provided OR when it's not a help request
        argv = sys.argv if args is None else args
        if len(argv) == 0 or not OpenTokenCommand._is_help_request(argv):
            OpenTokenCommand.show_banner()

        try:
            parsed_args = parser.parse_args(args)
        except SystemExit as error:
            return error.code if isinstance(error.code, int) else 1

        no_update_check = getattr(parsed_args, "no_update_check", False)

        # Start the asynchronous version check before executing the command
        version_checker = start_version_check(
            OpenTokenCommand.VERSION, no_update_check=no_update_check
        )

        # If no subcommand specified, show help
        if not parsed_args.command:
            parser.print_help()
            version_checker.wait_and_notify()
            return 0

        # Execute the command
        try:
            exit_code = parsed_args.func(parsed_args)
        except Exception as e:
            logger.error(f"Command execution failed: {e}", exc_info=True)
            exit_code = 1

        # Wait for the version check and surface any update notice after command output
        version_checker.wait_and_notify()
        return exit_code

    @staticmethod
    def execute(args):
        """
        Execute the CLI without calling sys.exit().
        Useful for testing or when embedding the CLI in another application.

        Args:
            args: Command-line arguments as a list

        Returns:
            Exit code (0 for success, non-zero for errors)
        """
        return OpenTokenCommand.main(args)

    @staticmethod
    def _is_help_request(args):
        """Check if the command is a help request."""
        if not args:
            return False
        for arg in args:
            if arg in ("--help", "help"):
                return True
        return False
