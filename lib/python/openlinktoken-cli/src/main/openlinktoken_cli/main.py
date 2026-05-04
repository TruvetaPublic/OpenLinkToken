# SPDX-License-Identifier: MIT

import logging
import sys

from openlinktoken_cli.commands import OpenLinkTokenCommand
from openlinktoken_cli.util.cli_run_reporter import configure_default_logging

configure_default_logging()
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the Open Link Token application."""
    exit_code = OpenLinkTokenCommand.main(sys.argv[1:])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
