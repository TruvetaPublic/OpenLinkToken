# SPDX-License-Identifier: MIT

import logging
import sys

from openlinktoken_cli.commands import OpenLinkTokenCommand

_RESET = "\033[0m"
_LEVEL_COLORS = {
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[1;31m",
}


class _ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        color = _LEVEL_COLORS.get(record.levelno)
        return f"{color}{msg}{_RESET}" if color else msg


_handler = logging.StreamHandler()
_handler.setFormatter(_ColorFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_handler])
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the Open Link Token application."""
    exit_code = OpenLinkTokenCommand.main(sys.argv[1:])
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
