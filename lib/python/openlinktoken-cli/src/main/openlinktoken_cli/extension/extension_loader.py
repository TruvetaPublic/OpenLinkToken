# SPDX-License-Identifier: MIT

import argparse
import importlib
import importlib.metadata
import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from openlinktoken_cli.extension.extension_manifest import CURRENT_CORE_VERSION, is_core_compatible

logger = logging.getLogger(__name__)
_CURRENT_CORE_VERSION = CURRENT_CORE_VERSION
WORKER_ARGUMENT = "--_olt-extension-worker"
METADATA_ARGUMENT = "--_olt-extension-metadata"
METADATA_MARKER = "OLT_EXTENSION_METADATA:"
_VALID_COMMAND_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_METADATA_WORKER_TIMEOUT_SECONDS = 60

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
    * **Frozen parent track**: reads ``registry.json`` and registers
      metadata-only parsers. A selected command runs in a separate process.
    * **Frozen worker track**: imports only the requested extension with its
      private source and dependency paths.
    """

    CURRENT_CORE_VERSION = _CURRENT_CORE_VERSION

    @staticmethod
    def load_extensions(
        subparsers: argparse._SubParsersAction,
        built_in_commands: Optional[set[str]] = None,
        *,
        worker_extension_name: Optional[str] = None,
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
            worker_extension_name: Registry key to load in a standalone extension worker.
        """
        if built_in_commands is None:
            built_in_commands = BUILTIN_COMMANDS

        if getattr(sys, "frozen", False) and worker_extension_name is None:
            ExtensionLoader._register_standalone_stubs(subparsers, built_in_commands)
            return
        if getattr(sys, "frozen", False):
            try:
                extensions = [ExtensionLoader.load_worker_extension(worker_extension_name)]
            except Exception as exc:
                raise ExtensionLoadError(f"Could not load extension '{worker_extension_name}': {exc}") from exc
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

        Returns:
            Loaded from entry points as a sequence.
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
    def load_worker_extension(name: Optional[str]) -> object:
        """
        Import exactly one registry extension inside its isolated worker process.

        Args:
            name: Registry key identifying the extension to load.

        Returns:
            The validated extension instance.

        Raises:
            ExtensionLoadError: If the registry entry or extension implementation is invalid.
        """
        if not isinstance(name, str) or not name:
            raise ExtensionLoadError("A worker extension name is required.")
        from openlinktoken_cli.extension.extension_interface import OpenLinkTokenExtension
        from openlinktoken_cli.extension.extension_registry import ExtensionRegistry

        registry = ExtensionRegistry.load()
        metadata = registry.get(name)
        if not isinstance(metadata, dict):
            raise ExtensionLoadError(f"Extension '{name}' is not registered.")
        if metadata.get("disabled"):
            raise ExtensionLoadError(f"Extension '{name}' is disabled: {metadata.get('error', 'disabled')}")
        core_range = (
            metadata.get("supported_core") or metadata.get("supported_core_version_range") or metadata.get("core_range")
        )
        if core_range and not is_core_compatible(ExtensionLoader.CURRENT_CORE_VERSION, core_range):
            raise ExtensionLoadError(
                f"Extension '{name}' requires core {core_range}, "
                f"but this binary is {ExtensionLoader.CURRENT_CORE_VERSION}."
            )

        module_name = metadata.get("module")
        class_name = metadata.get("class")
        if (
            not isinstance(module_name, str)
            or not all(part.isidentifier() for part in module_name.split("."))
            or not isinstance(class_name, str)
            or not class_name.isidentifier()
        ):
            raise ExtensionLoadError(f"Extension '{name}' registry entry has an invalid module or class.")

        extensions_dir = ExtensionRegistry.get_extensions_dir().resolve()
        for path_key in ("source_path", "dependency_path"):
            path_value = metadata.get(path_key)
            if path_value is None:
                continue
            if not isinstance(path_value, str):
                raise ExtensionLoadError(f"Extension '{name}' has an invalid {path_key}.")
            extension_path = Path(path_value).expanduser().resolve()
            if extensions_dir not in extension_path.parents or not extension_path.is_dir():
                raise ExtensionLoadError(f"Extension '{name}' {path_key} is outside its install directory.")
            if str(extension_path) not in sys.path:
                sys.path.append(str(extension_path))

        sys.dont_write_bytecode = True
        importlib.invalidate_caches()
        try:
            module = importlib.import_module(module_name)
            extension_class = getattr(module, class_name)
            instance = extension_class()
        except (ImportError, AttributeError, TypeError) as exc:
            raise ExtensionLoadError(f"Could not import {module_name}.{class_name}: {exc}") from exc

        if not isinstance(instance, OpenLinkTokenExtension):
            raise ExtensionLoadError(f"Extension '{name}' does not implement OpenLinkTokenExtension.")
        command_name = getattr(instance, "command_name", None)
        if command_name != metadata.get("command_name", name):
            raise ExtensionLoadError(
                f"Extension '{name}' command name '{command_name}' does not match its registry entry."
            )
        if not isinstance(getattr(instance, "description", None), str):
            raise ExtensionLoadError(f"Extension '{name}' description must be a string.")
        return instance

    @staticmethod
    def find_extension_command(args: list[str]) -> Optional[tuple[str, list[str]]]:
        """
        Find a registered top-level extension command without importing its code.

        Args:
            args: Original CLI arguments.

        Returns:
            The registry key and forwarded worker arguments, or ``None``.
        """
        command_index = None
        command = None
        for index, value in enumerate(args):
            if value in ("-h", "--help", "--version", "--"):
                return None
            if value == "--no-update-check":
                continue
            if value.startswith("-"):
                continue
            command_index = index
            command = value
            break
        if command_index is None or command is None:
            return None

        registry = ExtensionLoader._active_registry()
        if command == "help":
            extension_index = command_index + 1
            if extension_index >= len(args) or args[extension_index].startswith("-"):
                return None
            extension_name = args[extension_index]
            if extension_name in BUILTIN_COMMANDS or extension_name not in registry:
                return None
            if args[extension_index + 1 :]:
                return None
            prefix = args[:command_index]
            return extension_name, [*prefix, extension_name, "--help"]
        if command in BUILTIN_COMMANDS or command not in registry:
            return None

        forwarded_args = list(args)
        if not args[command_index + 1 :]:
            forwarded_args.append("--help")
        return command, forwarded_args

    @staticmethod
    def run_worker(name: str, args: list[str]) -> int:
        """
        Run one extension command in a fresh copy of the standalone executable.

        Args:
            name: Registry key identifying the extension.
            args: Original CLI arguments to parse inside the worker.

        Returns:
            The worker's exit status.
        """
        command = [sys.executable, WORKER_ARGUMENT, name, "--", *args]
        try:
            return subprocess.run(command, check=False).returncode
        except OSError as exc:
            print(f"Error: Could not start extension worker for '{name}': {exc}", file=sys.stderr)
            return 1

    @staticmethod
    def _register_standalone_stubs(
        subparsers: argparse._SubParsersAction,
        built_in_commands: set[str],
    ) -> None:
        """
        Register metadata-only parsers for standalone extensions.

        Args:
            subparsers: Root CLI subparsers.
            built_in_commands: Reserved built-in command names.
        """
        registry = ExtensionLoader._active_registry()
        registered: set[str] = set()
        for name, original_metadata in sorted(registry.items()):
            if not isinstance(original_metadata, dict):
                logger.warning("Extension '%s' registry entry is not an object; skipping.", name)
                continue
            metadata = dict(original_metadata)
            command_name = metadata.get("command_name", name)
            if not isinstance(command_name, str) or not _VALID_COMMAND_RE.fullmatch(command_name):
                logger.warning("Extension '%s' has an invalid command name; skipping.", name)
                continue
            if command_name in built_in_commands or command_name in registered:
                logger.warning("Extension '%s' conflicts with an existing command; skipping.", name)
                continue
            description = metadata.get("description")
            if not isinstance(description, str) or not description:
                worker_metadata = ExtensionLoader._metadata_from_worker(name)
                if worker_metadata is not None and worker_metadata["command_name"] == command_name:
                    description = worker_metadata["description"]
                    metadata.update(worker_metadata)
                    try:
                        from openlinktoken_cli.extension.extension_registry import ExtensionRegistry

                        stored_registry = ExtensionRegistry.load()
                        stored_metadata = stored_registry.get(name)
                        if isinstance(stored_metadata, dict):
                            stored_metadata.update(worker_metadata)
                            stored_registry[name] = stored_metadata
                            ExtensionRegistry.save(stored_registry)
                    except OSError:
                        logger.warning("Could not cache help metadata for extension '%s'.", name, exc_info=True)
                else:
                    description = "Installed extension"
            subparsers.add_parser(command_name, help=description)
            registered.add(command_name)

    @staticmethod
    def _active_registry() -> dict:
        """
        Return compatible, enabled registry entries without importing extension code.

        Returns:
            Registry entries that may be exposed by the standalone CLI.
        """
        from openlinktoken_cli.extension.extension_registry import ExtensionRegistry

        registry = ExtensionRegistry.load()
        active = {}
        for name, metadata in registry.items():
            if not isinstance(metadata, dict):
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
                    metadata = dict(metadata)
                    metadata["disabled"] = False
                else:
                    logger.info("Extension '%s' is disabled: %s", name, metadata.get("error", "disabled"))
                    continue
            command_name = metadata.get("command_name", name)
            if (
                not isinstance(command_name, str)
                or not _VALID_COMMAND_RE.fullmatch(command_name)
                or command_name != name
            ):
                logger.warning("Extension registry key '%s' does not match its command name; skipping.", name)
                continue
            active.setdefault(command_name, metadata)
        return active

    @staticmethod
    def _metadata_from_worker(name: str) -> Optional[dict[str, str]]:
        """
        Ask an isolated worker for legacy extension help metadata.

        Args:
            name: Registry key identifying the extension.

        Returns:
            Command name and description, or ``None`` when the worker fails.
        """
        try:
            result = subprocess.run(
                [sys.executable, METADATA_ARGUMENT, name],
                capture_output=True,
                text=True,
                check=False,
                timeout=_METADATA_WORKER_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("Could not query help metadata for extension '%s': %s", name, exc)
            return None
        if result.returncode != 0:
            logger.warning("Metadata worker for extension '%s' failed: %s", name, result.stderr.strip())
            return None

        for line in reversed(result.stdout.splitlines()):
            if not line.startswith(METADATA_MARKER):
                continue
            try:
                payload = json.loads(line[len(METADATA_MARKER) :])
            except json.JSONDecodeError:
                break
            if (
                isinstance(payload, dict)
                and isinstance(payload.get("command_name"), str)
                and isinstance(payload.get("description"), str)
                and payload["description"]
            ):
                return {
                    "command_name": payload["command_name"],
                    "description": payload["description"],
                }
            break
        logger.warning("Metadata worker for extension '%s' returned invalid help metadata.", name)
        return None

    @staticmethod
    def _record_state(name: str, *, disabled: bool, error: Optional[str]) -> None:
        """
        Persist loader state without allowing a registry failure to break startup.

        Args:
            name: Name identifying the item being processed.
            disabled: Whether to disabled.
            error: Error message or exception text to include in the status record.
        """
        try:
            from openlinktoken_cli.extension.extension_registry import ExtensionRegistry

            ExtensionRegistry.update_state(name, disabled=disabled, error=error)
        except Exception:  # noqa: BLE001
            logger.debug("Could not persist state for extension '%s'.", name, exc_info=True)


class ExtensionLoadError(ValueError):
    """Raised when an isolated extension cannot be loaded or validated."""
