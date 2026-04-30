# SPDX-License-Identifier: MIT

import os
import sys
from pathlib import Path

_OPENLINKTOKEN_HOME_DIR = ".openlinktoken"
_LOGS_DIR_NAME = "logs"


def get_openlinktoken_home() -> Path:
    """Return the platform-appropriate Open Link Token home directory."""
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA", "").strip()
        if appdata:
            return Path(appdata) / _OPENLINKTOKEN_HOME_DIR
    return Path.home() / _OPENLINKTOKEN_HOME_DIR


def get_logs_dir() -> Path:
    """Return the directory used for archived CLI error logs."""
    return get_openlinktoken_home() / _LOGS_DIR_NAME
