# SPDX-License-Identifier: MIT

import argparse
import logging
import os
import sys

from openlinktoken.metadata import Metadata
from openlinktoken_cli.util.cli_error_reporter import archive_unexpected_error, format_unexpected_error_message
from openlinktoken_cli.util.cli_run_reporter import configure_default_logging
from openlinktoken_cli.util.version_checker import start_version_check

logger = logging.getLogger(__name__)


class OpenLinkTokenCommand:
    """
    Main entry point command for Open Link Token CLI with subcommands.
    Provides modern, subcommand-based interface for token operations.
    """

    VERSION = Metadata.DEFAULT_VERSION

    @staticmethod
    def show_banner():
        """
        Display the Open Link Token banner for interactive sessions.
        Respects NO_COLOR environment variable and TTY detection.
        """
        # Check if we're in an interactive terminal and NO_COLOR is not set
        if not OpenLinkTokenCommand._is_interactive() or os.getenv("NO_COLOR"):
            return

        try:
            banner = OpenLinkTokenCommand._get_colorized_banner()
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
        """Get the colorized Open Link Token banner."""
        cyan = "\033[36m"
        blue = "\033[34m"
        reset = "\033[0m"

        return (
            f"{cyan}  ___                   _    _      _     _____    _            {reset}\n"
            f"{cyan} / _ \\ _ __  ___ _ _   | |  (_)_ _ | |__ |_   _|__| |_____ _ _  {reset}\n"
            f"{cyan}| (_) | '_ \\/ -_) ' \\  | |__| | ' \\| / /   | |/ _ \\ / / -_) ' \\ {reset}\n"
            f"{cyan} \\___/| .__/\\___|_||_| |____|_|_||_|_\\_\\   |_|\\___/_\\_\\___|_||_|{reset}\n"
            f"{cyan}      |_|{reset}\n"
            f"{blue}Privacy-Preserving Record Linkage v{OpenLinkTokenCommand.VERSION}{reset}\n"
        )

    @staticmethod
    def create_parser():
        """Create the main argument parser with subcommands."""
        parser = argparse.ArgumentParser(
            prog="olt",
            description="Privacy-preserving record linkage via cryptographic tokens",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        parser.add_argument(
            "--version",
            action="version",
            version=f"Open Link Token {OpenLinkTokenCommand.VERSION}",
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
            help="Use 'openlinktoken <command> --help' for command-specific help",
        )

        # Import command modules here to avoid circular imports
        from openlinktoken_cli.commands.decrypt_command import DecryptCommand
        from openlinktoken_cli.commands.encrypt_command import EncryptCommand
        from openlinktoken_cli.commands.extension_command import ExtensionCommand
        from openlinktoken_cli.commands.generate_key_pair_command import GenerateKeyPairCommand
        from openlinktoken_cli.commands.help_command import HelpCommand
        from openlinktoken_cli.commands.initiate_exchange_command import InitiateExchangeCommand
        from openlinktoken_cli.commands.package_command import PackageCommand
        from openlinktoken_cli.commands.tokenize_command import TokenizeCommand
        from openlinktoken_cli.commands.update_command import UpdateCommand
        from openlinktoken_cli.extension.extension_loader import BUILTIN_COMMANDS, ExtensionLoader

        # Register subcommands in alphabetical order by command name
        DecryptCommand.register_subcommand(subparsers)
        EncryptCommand.register_subcommand(subparsers)
        ExtensionCommand.register_subcommand(subparsers)
        GenerateKeyPairCommand.register_subcommand(subparsers)
        HelpCommand.register_subcommand(subparsers)
        InitiateExchangeCommand.register_subcommand(subparsers)
        PackageCommand.register_subcommand(subparsers)
        TokenizeCommand.register_subcommand(subparsers)
        UpdateCommand.register_subcommand(subparsers)

        # Load installed extensions (entry points or registry).
        # BUILTIN_COMMANDS is the authoritative set of reserved command names.
        ExtensionLoader.load_extensions(subparsers, BUILTIN_COMMANDS)

        # Sort all subcommands (built-ins and extensions) alphabetically.
        # Uses private argparse internals that may not exist in all Python versions;
        # sorting is skipped gracefully if those attributes are absent.
        if hasattr(subparsers, "_name_parser_map") and hasattr(subparsers, "_choices_actions"):
            sorted_items = sorted(subparsers._name_parser_map.items())
            subparsers._name_parser_map.clear()
            subparsers._name_parser_map.update(sorted_items)
            subparsers._choices_actions.sort(key=lambda a: a.dest)
        else:
            logger.debug(
                "Subcommand alphabetical sorting skipped: argparse internals "
                "(_name_parser_map / _choices_actions) not available on this Python version."
            )

        return parser

    @staticmethod
    def main(args=None):
        """Main entry point for the command-line application."""
        configure_default_logging()
        parser = OpenLinkTokenCommand.create_parser()

        # Show banner for interactive runs.
        OpenLinkTokenCommand.show_banner()

        try:
            parsed_args = parser.parse_args(args)
        except SystemExit as error:
            return error.code if isinstance(error.code, int) else 1

        no_update_check = getattr(parsed_args, "no_update_check", False)
        should_start_version_check = OpenLinkTokenCommand._should_start_version_check(parsed_args)

        version_checker = None
        if should_start_version_check:
            # Start the asynchronous version check before executing the command
            version_checker = start_version_check(OpenLinkTokenCommand.VERSION, no_update_check=no_update_check)

        # If no subcommand specified, show help
        if not parsed_args.command:
            parser.print_help()
            if version_checker is not None:
                version_checker.wait_and_notify()
            return 0

        # Execute the command
        try:
            exit_code = parsed_args.func(parsed_args)
        except Exception as error:
            report = archive_unexpected_error(error)
            print(format_unexpected_error_message(report), file=sys.stderr)
            logger.debug("Command execution failed", exc_info=error)
            exit_code = 1

        # Wait for the version check and surface any update notice after command output
        if version_checker is not None:
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
        return OpenLinkTokenCommand.main(args)

    @staticmethod
    def _is_help_request(args):
        """Check if the command is a help request."""
        if not args:
            return False
        for arg in args:
            if arg in ("--help", "help"):
                return True
        return False

    @staticmethod
    def _should_start_version_check(parsed_args: argparse.Namespace) -> bool:
        """Return whether startup version checks should run for the parsed command."""
        return getattr(parsed_args, "command", None) != "update"
