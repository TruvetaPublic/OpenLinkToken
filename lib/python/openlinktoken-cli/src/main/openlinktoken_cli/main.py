"""
Copyright (c) Truveta. All rights reserved.
"""

import logging
import sys

from openlinktoken_cli.commands import OpenLinkTokenCommand

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the OpenLinkToken application."""
    exit_code = OpenLinkTokenCommand.main(sys.argv[1:])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
