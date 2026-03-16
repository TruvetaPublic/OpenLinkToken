"""
Copyright (c) Truveta. All rights reserved.
"""

import argparse
import importlib
import importlib.metadata
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)

#: The set of command names reserved by built-in OpenToken subcommands.
BUILTIN_COMMANDS: set[str] = {
    "help",
    "tokenize",
    "encrypt",
    "decrypt",
    "package",
    "generate-key-pair",
    "initiate-exchange",
    "update",
    "extension",
}


class ExtensionLoader:
    """
    Discovers and loads OpenToken CLI extensions into the argument parser.

    Two discovery tracks are supported:

    * **Python package track** (default): uses ``importlib.metadata.entry_points``
      with the ``opentoken.extensions`` group.  Works when the CLI is run from
      a normal Python environment.
    * **Frozen binary track**: when ``sys.frozen`` is ``True`` (e.g. a PyInstaller
      binary), reads ``registry.json``, prepends each extension's ``source_path``
      to ``sys.path``, and imports the module directly.
    """

    @staticmethod
    def load_extensions(
        subparsers: argparse._SubParsersAction,
        built_in_commands: Optional[set[str]] = None,
    ) -> None:
        """
        Discover all installed extensions and register each one with *subparsers*.

        Extensions are processed in deterministic order (sorted by ``command_name``).
        An extension is skipped (with a warning) when:

        * Its ``command_name`` conflicts with a built-in command.
        * Its ``command_name`` was already registered by an earlier extension.
        * The extension module cannot be imported.

        Args:
            subparsers: The shared subparsers action from the root OpenToken parser.
            built_in_commands: Set of reserved command names.  Defaults to
                ``BUILTIN_COMMANDS`` when ``None``.
        """
        if built_in_commands is None:
            built_in_commands = BUILTIN_COMMANDS

        if getattr(sys, "frozen", False):
            extensions = ExtensionLoader._load_from_registry()
        else:
            extensions = ExtensionLoader._load_from_entry_points()

        # Sort deterministically by command_name so the parser output is stable.
        extensions.sort(key=lambda ext: ext.command_name)

        registered: set[str] = set()
        for ext in extensions:
            cmd = ext.command_name
            if cmd in built_in_commands:
                logger.warning(
                    "Extension '%s' conflicts with built-in command '%s'; skipping.",
                    type(ext).__name__,
                    cmd,
                )
                continue
            if cmd in registered:
                logger.warning(
                    "Extension '%s' wants to register command '%s' which is already claimed; skipping.",
                    type(ext).__name__,
                    cmd,
                )
                continue
            try:
                ext.register_subcommand(subparsers)
                registered.add(cmd)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Extension '%s' failed to register subcommand '%s': %s",
                    type(ext).__name__,
                    cmd,
                    exc,
                )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_from_entry_points() -> list:
        """
        Discover extensions via the ``opentoken.extensions`` entry-point group.

        Each entry point is expected to point to an ``OpenTokenExtension`` subclass.
        Import errors are caught per extension and emit a warning.
        """
        from opentoken_cli.extension.extension_interface import OpenTokenExtension

        extensions = []
        try:
            eps = importlib.metadata.entry_points(group="opentoken.extensions")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not query entry points for 'opentoken.extensions': %s", exc)
            return extensions

        for ep in eps:
            try:
                cls = ep.load()
                instance = cls()
                if not isinstance(instance, OpenTokenExtension):
                    logger.warning(
                        "Entry point '%s' does not implement OpenTokenExtension; skipping.",
                        ep.name,
                    )
                    continue
                extensions.append(instance)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to load extension from entry point '%s': %s", ep.name, exc)

        return extensions

    @staticmethod
    def _load_from_registry() -> list:
        """
        Discover extensions from registry.json when running as a frozen binary.

        Each entry's ``source_path`` is prepended to ``sys.path`` so that the
        extension's source tree is importable.
        """
        from opentoken_cli.extension.extension_interface import OpenTokenExtension
        from opentoken_cli.extension.extension_registry import ExtensionRegistry

        extensions = []
        registry = ExtensionRegistry.load()

        for name, metadata in registry.items():
            source_path = metadata.get("source_path")
            module_name = metadata.get("module")
            class_name = metadata.get("class")

            if not module_name or not class_name:
                logger.warning(
                    "Extension '%s' registry entry is missing 'module' or 'class'; skipping.",
                    name,
                )
                continue

            # Prepend source_path so the extension's package is importable.
            if source_path:
                from pathlib import Path as _Path

                expanded = str(_Path(source_path).expanduser().resolve())
                if expanded not in sys.path:
                    sys.path.insert(0, expanded)

            try:
                mod = importlib.import_module(module_name)
                cls = getattr(mod, class_name)
                instance = cls()
                if not isinstance(instance, OpenTokenExtension):
                    logger.warning(
                        "Extension '%s' class '%s.%s' does not implement OpenTokenExtension; skipping.",
                        name,
                        module_name,
                        class_name,
                    )
                    continue
                extensions.append(instance)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to load extension '%s' from registry: %s", name, exc)

        return extensions
