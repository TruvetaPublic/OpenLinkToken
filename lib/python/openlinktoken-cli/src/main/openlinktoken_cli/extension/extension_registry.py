# SPDX-License-Identifier: MIT

import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_EXTENSIONS_SUBDIR = Path(".openlinktoken") / "extensions"


class ExtensionRegistry:
    """
    Manages the Open Link Token extension registry stored at ``~/.openlinktoken/extensions/registry.json``.

    The registry is a JSON file that maps extension names to their installation metadata.
    The base directory can be overridden via the ``OLT_EXTENSIONS_DIR`` environment variable.

    Registry JSON schema (one entry per installed extension):

    .. code-block:: json

        {
          "hello-world": {
            "version": "1.0.0",
            "source_url": "https://example.com/hello_world-1.0.0-py3-none-any.whl",
            "source_path": "~/.openlinktoken/extensions/hello-world/src",
            "module": "openlinktoken_ext_hello_world.extension",
            "class": "HelloWorldExtension",
            "command_name": "hello-world",
            "dist_name": "openlinktoken-ext-hello-world"
          }
        }
    """

    @staticmethod
    def get_extensions_dir() -> Path:
        """
        Return the base directory for installed extensions.

        Uses the ``OLT_EXTENSIONS_DIR`` environment variable when set;
        otherwise defaults to ``~/.openlinktoken/extensions/``.
        """
        env_override = os.environ.get("OLT_EXTENSIONS_DIR")
        if env_override:
            base_path = Path(env_override).expanduser()
            if not base_path.is_absolute():
                base_path = Path.home() / base_path
            return base_path.resolve()
        return (Path.home() / _DEFAULT_EXTENSIONS_SUBDIR).resolve()

    @staticmethod
    def get_registry_path() -> Path:
        """Return the full path to the registry JSON file."""
        return ExtensionRegistry.get_extensions_dir() / "registry.json"

    @staticmethod
    def load() -> dict:
        """
        Load and return the registry contents.

        Returns an empty dict if the registry file does not exist or cannot be parsed.
        """
        registry_path = ExtensionRegistry.get_registry_path()
        if not registry_path.exists():
            return {}
        try:
            return json.loads(registry_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load extension registry at %s: %s", registry_path, exc)
            return {}

    @staticmethod
    def save(registry: dict) -> None:
        """
        Write the registry to disk atomically (write to a temp file, then rename).

        Args:
            registry: The full registry dict to persist.
        """
        registry_path = ExtensionRegistry.get_registry_path()
        registry_path.parent.mkdir(parents=True, exist_ok=True)

        content = json.dumps(registry, indent=2, sort_keys=True) + "\n"
        dir_ = registry_path.parent
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=dir_,
                delete=False,
                suffix=".tmp",
            ) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
            tmp_path.replace(registry_path)
        except OSError as exc:
            logger.error("Failed to save extension registry to %s: %s", registry_path, exc)
            raise

    @staticmethod
    def add_extension(name: str, metadata: dict) -> None:
        """
        Add or update an extension entry in the registry.

        Args:
            name: The extension's canonical name (matches ``command_name``).
            metadata: Dict with keys ``version``, ``source_url``, ``source_path``, ``module``, ``class``,
                ``command_name``, and ``dist_name``.
        """
        registry = ExtensionRegistry.load()
        registry[name] = metadata
        ExtensionRegistry.save(registry)

    @staticmethod
    def remove_extension(name: str) -> None:
        """
        Remove an extension entry from the registry.

        A no-op if the extension is not present.

        Args:
            name: The extension name to remove.
        """
        registry = ExtensionRegistry.load()
        if name in registry:
            del registry[name]
            ExtensionRegistry.save(registry)
