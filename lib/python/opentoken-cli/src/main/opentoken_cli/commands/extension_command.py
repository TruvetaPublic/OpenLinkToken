"""
Copyright (c) Truveta. All rights reserved.
"""

import configparser
import logging
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
from urllib.request import urlopen

from opentoken_cli.extension.extension_registry import ExtensionRegistry

logger = logging.getLogger(__name__)

_SECURITY_WARNING = (
    "WARNING: Extensions are arbitrary Python code and are not verified by Truveta. "
    "Install only extensions from sources you trust."
)

#: Dependencies bundled into the frozen binary that extensions may rely on.
_BUNDLED_DEPS: frozenset[str] = frozenset(
    {
        "opentoken",
        "opentoken-cli",
    }
)

_REQUEST_TIMEOUT_SECONDS = 60


class ExtensionCommand:
    """
    Manage OpenToken CLI extensions.

    Provides sub-subcommands to install, list, uninstall, and update extensions.
    """

    @staticmethod
    def register_subcommand(subparsers) -> None:
        """Register the ``extension`` subcommand and its sub-subcommands."""
        parser = subparsers.add_parser(
            "extension",
            help="Manage OpenToken CLI extensions",
            description="Install, list, uninstall, and update OpenToken CLI extensions.",
        )
        sub = parser.add_subparsers(dest="extension_subcommand")

        # install
        install_parser = sub.add_parser(
            "install",
            help="Install an extension from a URL or local file path",
        )
        install_parser.add_argument(
            "url",
            help="URL (https://) or local path (file://) to the extension .whl",
        )
        install_parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            default=False,
            dest="yes",
            help="Skip the security confirmation prompt",
        )
        install_parser.set_defaults(func=ExtensionCommand._install)

        # list
        list_parser = sub.add_parser("list", help="List installed extensions")
        list_parser.set_defaults(func=ExtensionCommand._list)

        # uninstall
        uninstall_parser = sub.add_parser("uninstall", help="Uninstall an extension by name")
        uninstall_parser.add_argument("name", help="Extension name to uninstall")
        uninstall_parser.set_defaults(func=ExtensionCommand._uninstall)

        # update
        update_parser = sub.add_parser("update", help="Re-install an extension from its original source URL")
        update_parser.add_argument("name", help="Extension name to update")
        update_parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            default=False,
            dest="yes",
            help="Skip the security confirmation prompt",
        )
        update_parser.set_defaults(func=ExtensionCommand._update)

        parser.set_defaults(func=lambda args: (parser.print_help(), 0)[1])

    # ------------------------------------------------------------------
    # Sub-command handlers
    # ------------------------------------------------------------------

    @staticmethod
    def _install(args) -> int:
        """Handle ``extension install <url>``."""
        url: str = args.url
        skip_confirm: bool = getattr(args, "yes", False)

        print(_SECURITY_WARNING)
        if not skip_confirm and sys.stdin.isatty():
            try:
                answer = input("Do you want to continue? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""
            if answer not in ("y", "yes"):
                print("Installation cancelled.")
                return 0

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / "extension.whl"
            if not ExtensionCommand._download(url, tmp_path):
                return 1

            return ExtensionCommand._install_wheel(tmp_path, source_url=url)

    @staticmethod
    def _list(args) -> int:  # noqa: ARG004
        """Handle ``extension list``."""
        rows: dict[str, dict] = {}

        # Registry entries (installed via `extension install`).
        for name, meta in ExtensionRegistry.load().items():
            rows[name] = {
                "version": meta.get("version", ""),
                "command": meta.get("command_name", name),
                "source": meta.get("source_url", ""),
            }

        # Entry-point extensions (installed via pip / editable install).
        # These are not in the registry, so we surface them separately.
        if not getattr(sys, "frozen", False):
            import importlib.metadata

            try:
                eps = importlib.metadata.entry_points(group="opentoken.extensions")
                for ep in eps:
                    if ep.name not in rows:
                        version = ""
                        try:
                            version = ep.dist.metadata["Version"] or ""
                        except Exception:
                            pass
                        rows[ep.name] = {
                            "version": version,
                            "command": ep.name,
                            "source": "pip-installed",
                        }
            except Exception as exc:
                logger.debug("Could not query entry points for list: %s", exc)

        if not rows:
            print("No extensions installed.")
            return 0

        col_widths = {"name": 4, "version": 7, "command": 7, "source": 10}
        for name, meta in rows.items():
            col_widths["name"] = max(col_widths["name"], len(name))
            col_widths["version"] = max(col_widths["version"], len(meta["version"]))
            col_widths["command"] = max(col_widths["command"], len(meta["command"]))
            col_widths["source"] = max(col_widths["source"], len(meta["source"]))

        header = (
            f"{'Name':<{col_widths['name']}}  "
            f"{'Version':<{col_widths['version']}}  "
            f"{'Command':<{col_widths['command']}}  "
            f"Source"
        )
        print(header)
        print("-" * len(header))
        for name, meta in sorted(rows.items()):
            print(
                f"{name:<{col_widths['name']}}  "
                f"{meta['version']:<{col_widths['version']}}  "
                f"{meta['command']:<{col_widths['command']}}  "
                f"{meta['source']}"
            )
        return 0

    @staticmethod
    def _uninstall(args) -> int:
        """Handle ``extension uninstall <name>``."""
        name: str = args.name
        registry = ExtensionRegistry.load()

        if name not in registry:
            # Check if it exists as a pip-installed entry-point extension.
            pip_installed = False
            if not getattr(sys, "frozen", False):
                import importlib.metadata

                try:
                    eps = importlib.metadata.entry_points(group="opentoken.extensions")
                    pip_installed = any(ep.name == name for ep in eps)
                except Exception:
                    pass

            if pip_installed:
                print(
                    f"Error: '{name}' was installed via pip and cannot be removed by this command.\n"
                    f"Uninstall it with your package manager instead, for example:\n"
                    f"\n"
                    f"    pip uninstall {name}\n"
                    f"    uv pip uninstall {name}",
                    file=sys.stderr,
                )
                return 1

            print(f"Error: Extension '{name}' is not installed.", file=sys.stderr)
            return 1

        ext_dir = ExtensionRegistry.get_extensions_dir() / name
        if ext_dir.exists():
            shutil.rmtree(ext_dir)
        ExtensionRegistry.remove_extension(name)
        print(f"Extension '{name}' uninstalled.")
        return 0

    @staticmethod
    def _update(args) -> int:
        """Handle ``extension update <name>``."""
        name: str = args.name
        skip_confirm: bool = getattr(args, "yes", False)
        meta = ExtensionRegistry.get_extension(name)
        if meta is None:
            print(f"Error: Extension '{name}' is not installed.", file=sys.stderr)
            return 1

        source_url = meta.get("source_url")
        if not source_url:
            print(f"Error: No source URL recorded for extension '{name}'.", file=sys.stderr)
            return 1

        # Reuse install logic; pass --yes through.
        ext_dir = ExtensionRegistry.get_extensions_dir() / name
        if ext_dir.exists():
            shutil.rmtree(ext_dir)

        print(_SECURITY_WARNING)
        if not skip_confirm and sys.stdin.isatty():
            try:
                answer = input("Do you want to continue? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""
            if answer not in ("y", "yes"):
                print("Update cancelled.")
                return 0

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / "extension.whl"
            if not ExtensionCommand._download(source_url, tmp_path):
                return 1
            return ExtensionCommand._install_wheel(tmp_path, source_url=source_url)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _download(url: str, dest: Path) -> bool:
        """
        Download *url* to *dest*.

        Supports ``https://`` (via ``urllib.request.urlopen``) and
        ``file://`` (via ``shutil.copy``).

        Returns:
            ``True`` on success, ``False`` on failure (error printed to stderr).
        """
        if url.startswith("file://"):
            local_path = Path(url[len("file://") :])
            try:
                shutil.copy(str(local_path), str(dest))
                return True
            except OSError as exc:
                print(f"Error: Could not copy local file '{local_path}': {exc}", file=sys.stderr)
                return False

        try:
            with urlopen(url, timeout=_REQUEST_TIMEOUT_SECONDS) as resp, dest.open("wb") as out:
                shutil.copyfileobj(resp, out)
            return True
        except Exception as exc:
            print(f"Error: Download failed for '{url}': {exc}", file=sys.stderr)
            return False

    @staticmethod
    def _install_wheel(whl_path: Path, source_url: str) -> int:
        """
        Unpack *whl_path* and register the extension.

        Args:
            whl_path: Path to the downloaded ``.whl`` file.
            source_url: Original URL used to fetch the wheel (stored in registry).

        Returns:
            Exit code (0 on success).
        """
        if not zipfile.is_zipfile(whl_path):
            print(f"Error: '{whl_path.name}' is not a valid wheel (zip) file.", file=sys.stderr)
            return 1

        with zipfile.ZipFile(whl_path, "r") as zf:
            # Check for unacceptable external dependencies when frozen.
            if getattr(sys, "frozen", False):
                issue = ExtensionCommand._check_frozen_deps(zf)
                if issue:
                    print(
                        f"Error: This extension requires external dependencies that are not bundled "
                        f"in the OpenToken binary: {issue}\n"
                        "Install the Python package version of OpenToken CLI to use this extension.",
                        file=sys.stderr,
                    )
                    return 1

            entry_point_info = ExtensionCommand._extract_entry_point(zf)
            if entry_point_info is None:
                print(
                    "Error: No 'opentoken.extensions' entry point found in the wheel.",
                    file=sys.stderr,
                )
                return 1

            ext_name, module_name, class_name, version = entry_point_info
            ext_dir = ExtensionRegistry.get_extensions_dir() / ext_name
            src_dir = ext_dir / "src"
            src_dir.mkdir(parents=True, exist_ok=True)

            zf.extractall(src_dir)

        metadata: dict = {
            "version": version,
            "source_url": source_url,
            "source_path": str(src_dir),
            "module": module_name,
            "class": class_name,
            "command_name": ext_name,
        }
        ExtensionRegistry.add_extension(ext_name, metadata)
        print(f"Extension '{ext_name}' (v{version}) installed successfully.")
        print(f"Run: opentoken {ext_name} --help")
        return 0

    @staticmethod
    def _check_frozen_deps(zf: zipfile.ZipFile) -> Optional[str]:
        """
        Return a description of unsatisfied external dependencies, or ``None`` if all are bundled.

        Reads ``Requires-Dist`` headers from the wheel's ``METADATA`` file.

        Args:
            zf: An open ZipFile handle for the wheel.
        """
        metadata_candidates = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
        if not metadata_candidates:
            return None

        content = zf.read(metadata_candidates[0]).decode("utf-8", errors="replace")
        external = []
        for line in content.splitlines():
            if line.startswith("Requires-Dist:"):
                dep = line.split(":", 1)[1].strip()
                # Extract just the package name (before any version specifier / extras).
                dep_name = dep.split(";")[0].split("[")[0].strip().rstrip("><=! ").lower()
                # Normalise dashes/underscores.
                dep_name_norm = dep_name.replace("_", "-")
                if dep_name_norm not in _BUNDLED_DEPS:
                    external.append(dep_name)
        return ", ".join(external) if external else None

    @staticmethod
    def _extract_entry_point(zf: zipfile.ZipFile) -> Optional[tuple[str, str, str, str]]:
        """
        Parse the wheel's ``entry_points.txt`` and return the first ``opentoken.extensions`` entry.

        Also reads the ``METADATA`` file to obtain the package version.

        Returns:
            ``(entry_name, module, class_name, version)`` or ``None`` if not found.
        """
        ep_candidates = [n for n in zf.namelist() if n.endswith(".dist-info/entry_points.txt")]
        if not ep_candidates:
            return None

        raw = zf.read(ep_candidates[0]).decode("utf-8", errors="replace")
        cp = configparser.ConfigParser()
        cp.read_string(raw)

        if not cp.has_section("opentoken.extensions"):
            return None

        items = list(cp.items("opentoken.extensions"))
        if not items:
            return None

        entry_name, target = items[0]
        # target is like "some.module:ClassName"
        if ":" not in target:
            return None
        module_name, class_name = target.rsplit(":", 1)
        module_name = module_name.strip()
        class_name = class_name.strip()

        # Read version from METADATA.
        version = "0.0.0"
        metadata_candidates = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
        if metadata_candidates:
            meta_content = zf.read(metadata_candidates[0]).decode("utf-8", errors="replace")
            for line in meta_content.splitlines():
                if line.startswith("Version:"):
                    version = line.split(":", 1)[1].strip()
                    break

        return entry_name, module_name, class_name, version
