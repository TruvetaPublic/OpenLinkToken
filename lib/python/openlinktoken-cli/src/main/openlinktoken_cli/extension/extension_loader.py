# SPDX-License-Identifier: MIT

import argparse
import importlib
import importlib.metadata
import logging
import sys
from typing import Optional

from openlinktoken_cli.extension.extension_manifest import CURRENT_CORE_VERSION, is_core_compatible

logger = logging.getLogger(__name__)
_CURRENT_CORE_VERSION = CURRENT_CORE_VERSION

#: The set of command names reserved by built-in Open Link Token subcommands.
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
    Discovers and loads Open Link Token CLI extensions into the argument parser.

    Two discovery tracks are supported:

    * **Python package track** (default): uses ``importlib.metadata.entry_points``
      with the ``openlinktoken.extensions`` group.  Works when the CLI is run from
      a normal Python environment.
    * **Frozen binary track**: when ``sys.frozen`` is ``True`` (e.g. a PyInstaller
      binary), reads ``registry.json``, prepends each extension's ``source_path``
      to ``sys.path``, and imports the module directly.
    """

    CURRENT_CORE_VERSION = _CURRENT_CORE_VERSION

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
            subparsers: The shared subparsers action from the root Open Link Token parser.
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
        Discover extensions via the ``openlinktoken.extensions`` entry-point group.

        Each entry point is expected to point to an ``OpenLinkTokenExtension`` subclass.
        Import errors are caught per extension and emit a warning.
        """
        from openlinktoken_cli.extension.extension_interface import OpenLinkTokenExtension

        extensions = []
        try:
            eps = importlib.metadata.entry_points(group="openlinktoken.extensions")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not query entry points for 'openlinktoken.extensions': %s", exc)
            return extensions

        for ep in eps:
            try:
                cls = ep.load()
                instance = cls()
                if not isinstance(instance, OpenLinkTokenExtension):
                    logger.warning(
                        "Entry point '%s' does not implement OpenLinkTokenExtension; skipping.",
                        ep.name,
                    )
                    continue

                command_name = getattr(instance, "command_name", None)
                if not command_name:
                    logger.warning(
                        "Entry point '%s' extension instance is missing 'command_name'; skipping.",
                        ep.name,
                    )
                    continue

                if command_name != ep.name:
                    logger.warning(
                        "Entry point name '%s' does not match extension command_name '%s'; skipping.",
                        ep.name,
                        command_name,
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
        from openlinktoken_cli.extension.extension_interface import OpenLinkTokenExtension
        from openlinktoken_cli.extension.extension_registry import ExtensionRegistry

        extensions = []
        registry = ExtensionRegistry.load()

        for name, metadata in registry.items():
            if not isinstance(metadata, dict):
                logger.warning("Extension '%s' registry entry is not an object; skipping.", name)
                continue
            core_range = (
                metadata.get("supported_core")
                or metadata.get("supported_core_version_range")
                or metadata.get("core_range")
            )
            if core_range and not is_core_compatible(ExtensionLoader.CURRENT_CORE_VERSION, core_range):
                message = (
                    f"Extension '{name}' is incompatible with Open Link Token core "
                    f"{ExtensionLoader.CURRENT_CORE_VERSION} (requires {core_range}). "
                    "Update the extension or roll back the core bundle."
                )
                ExtensionLoader._record_state(name, disabled=True, error=message)
                logger.warning(message)
                continue
            if metadata.get("disabled"):
                error = metadata.get("error")
                if isinstance(error, str) and error.startswith("Extension '") and "incompatible with" in error:
                    ExtensionLoader._record_state(name, disabled=False, error=None)
                else:
                    logger.info("Extension '%s' is disabled: %s", name, metadata.get("error", "disabled"))
                    continue

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
                if not isinstance(instance, OpenLinkTokenExtension):
                    logger.warning(
                        "Extension '%s' class '%s.%s' does not implement OpenLinkTokenExtension; skipping.",
                        name,
                        module_name,
                        class_name,
                    )
                    continue

                command_name = getattr(instance, "command_name", None)
                if not command_name or command_name != name:
                    logger.warning(
                        "Extension registry key '%s' does not match extension command_name '%s'; skipping.",
                        name,
                        command_name,
                    )
                    continue

                extensions.append(instance)
            except Exception as exc:  # noqa: BLE001
                message = f"Failed to load extension '{name}' from registry: {exc}"
                ExtensionLoader._record_state(name, disabled=False, error=str(exc))
                logger.warning(message)

        return extensions

    @staticmethod
    def _record_state(name: str, *, disabled: bool, error: Optional[str]) -> None:
        """Persist loader state without allowing a registry failure to break startup."""
        try:
            from openlinktoken_cli.extension.extension_registry import ExtensionRegistry

            ExtensionRegistry.update_state(name, disabled=disabled, error=error)
        except Exception:  # noqa: BLE001
            logger.debug("Could not persist state for extension '%s'.", name, exc_info=True)
