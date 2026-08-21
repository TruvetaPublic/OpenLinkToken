# SPDX-License-Identifier: MIT

import logging
import sys

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the Open Link Token application."""
    from openlinktoken_cli.commands import OpenLinkTokenCommand

    exit_code = OpenLinkTokenCommand.main(sys.argv[1:])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
