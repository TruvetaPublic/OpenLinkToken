"""
Copyright (c) Truveta. All rights reserved.
"""

import logging
import sys

from opentoken_cli.commands import OpenTokenCommand


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the OpenToken application."""
    exit_code = OpenTokenCommand.main(sys.argv[1:])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
