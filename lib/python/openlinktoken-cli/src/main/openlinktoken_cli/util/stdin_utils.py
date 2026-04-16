"""
Helpers for safely reading required PEM material from standard input or environment variables.
"""

from __future__ import annotations

import os
import sys


def read_required_stdin_bytes(flag_name: str, value_name: str) -> bytes:
    """Read non-empty bytes from stdin for the provided command-line flag.

    Args:
        flag_name: Command-line flag requesting stdin input.
        value_name: Human-readable name of the expected stdin content.

    Returns:
        The raw bytes read from stdin.

    Raises:
        ValueError: If stdin does not provide any non-whitespace bytes.
    """
    stdin_stream = getattr(sys.stdin, "buffer", sys.stdin)
    value = stdin_stream.read()
    if isinstance(value, str):
        value = value.encode("utf-8")

    if not value or not value.strip():
        raise ValueError(f"{flag_name} received empty {value_name} input from stdin.")

    return value


def read_required_env_bytes(flag_name: str, env_var_name: str, value_name: str) -> bytes:
    """Read non-empty text bytes from the named environment variable.

    Args:
        flag_name: Command-line flag requesting environment-variable input.
        env_var_name: Name of the environment variable to read.
        value_name: Human-readable name of the expected value.

    Returns:
        The environment-variable value encoded as UTF-8 bytes.

    Raises:
        ValueError: If the environment variable is unset or only contains whitespace.
    """
    value = os.environ.get(env_var_name)
    if value is None or not value.strip():
        raise ValueError(f"{flag_name} requires non-empty {value_name} data in environment variable {env_var_name}.")

    return value.encode("utf-8")
