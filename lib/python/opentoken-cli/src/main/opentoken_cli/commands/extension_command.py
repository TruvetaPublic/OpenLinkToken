"""
Copyright (c) Truveta. All rights reserved.
"""

import configparser
import logging
import shutil
import subprocess
import sys
import tempfile
import zipfile
from contextlib import contextmanager
import importlib
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from urllib.request import urlopen

from opentoken_cli.extension.extension_registry import ExtensionRegistry

logger = logging.getLogger(__name__)


@contextmanager
def _temporary_sys_path(path: Optional[Path]):
    """
    Temporarily add ``path`` to ``sys.path`` for dynamic imports.
    """
    if path is None:
        yield
        return

    path_str = str(path)
    if path_str in sys.path:
        yield
        return

    sys.path.insert(0, path_str)
    try:
        yield
    finally:
        try:
            sys.path.remove(path_str)
        except ValueError:
            pass


def _resolve_extension_command_name(
    module_name: str,
    class_name: str,
    src_dir: Optional[Path] = None,
) -> Optional[str]:
    """
    Import the extension class and return its ``command_name`` attribute.
    """
    try:
        with _temporary_sys_path(src_dir):
            module = importlib.import_module(module_name)
            extension_cls = getattr(module, class_name)
            extension_obj = extension_cls()
            command_name = getattr(extension_obj, "command_name", None)
            if not isinstance(command_name, str) or not command_name:
                return None
            return command_name
    except Exception as exc:
        logger.error(
            "Failed to resolve command_name for extension %s.%s: %s",
            module_name,
            class_name,
            exc,
        )
        return None

_SECURITY_WARNING = (
    "WARNING: Extensions are arbitrary Python code and are not verified by Truveta. "
    "Install only extensions from sources you trust."
)

#: Dependencies bundled into the frozen binary that extensions may rely on.
#: Derived from the packages collected in opentoken-cli.spec and requirements.txt.
_BUNDLED_DEPS: frozenset[str] = frozenset(
    {
        "opentoken",
        "opentoken-cli",
        "pandas",
        "pyarrow",
        "csv2parquet",
        "cryptography",
        "jwcrypto",
        "packaging",
    }
)

_REQUEST_TIMEOUT_SECONDS = 60


class ExtensionCommand:
    """
    Manage OpenToken CLI extensions.

    Provides sub-subcommands to install, list, and uninstall extensions.
    """

    @staticmethod
    def register_subcommand(subparsers) -> None:
        """Register the ``extension`` subcommand and its sub-subcommands."""
        parser = subparsers.add_parser(
            "extension",
            help="Manage OpenToken CLI extensions",
            description="Install, list, and uninstall OpenToken CLI extensions.",
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

        parser.set_defaults(func=lambda args: (parser.print_help(), 0)[1])

    # ------------------------------------------------------------------
    # Sub-command handlers
    # ------------------------------------------------------------------

    @staticmethod
    def _install(args) -> int:
        """Handle ``extension install <url>``."""
        url: str = args.url
        skip_confirm: bool = getattr(args, "yes", False)

        print(f"{_SECURITY_WARNING}\nYou are about to install an extension from:\n  {url}")
        if not skip_confirm:
            if sys.stdin.isatty():
                try:
                    answer = input("Do you want to continue? [y/N] ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    answer = ""
                if answer not in ("y", "yes"):
                    print("Installation cancelled.")
                    return 0
            else:
                print(
                    "Error: stdin is not a TTY. Pass --yes to confirm installation in non-interactive mode.",
                    file=sys.stderr,
                )
                return 1

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Preserve the original wheel filename so pip can parse its metadata.
            import urllib.parse

            url_filename = Path(urllib.parse.urlparse(url).path).name
            whl_name = url_filename if url_filename.endswith(".whl") else "extension.whl"
            tmp_path = Path(tmp_dir) / whl_name
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
                # Look up the distribution name so the user can uninstall the
                # correct package (the entry-point key and the dist name often differ).
                dist_name = name
                if not getattr(sys, "frozen", False):
                    import importlib.metadata

                    try:
                        eps = importlib.metadata.entry_points(group="opentoken.extensions")
                        for ep in eps:
                            if ep.name == name:
                                name_from_meta = ep.dist.metadata.get("Name")
                                dist_name = name_from_meta or ep.dist.name or name
                                break
                    except Exception:
                        pass
                print(
                    f"Error: '{name}' was installed via pip and cannot be removed by this command.\n"
                    f"Uninstall it with your package manager instead, for example:\n"
                    f"\n"
                    f"    pip uninstall {dist_name}\n"
                    f"    uv pip uninstall {dist_name}",
                    file=sys.stderr,
                )
                return 1

            print(f"Error: Extension '{name}' is not installed.", file=sys.stderr)
            return 1

        meta = registry[name]

        if getattr(sys, "frozen", False):
            # Frozen binary: remove the extracted source directory.
            ext_dir = ExtensionRegistry.get_extensions_dir() / name
            if ext_dir.exists():
                shutil.rmtree(ext_dir)
        else:
            # Normal Python: uninstall via pip using the recorded dist name.
            dist_name = meta.get("dist_name") or name
            pip_result = subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", dist_name],
                capture_output=True,
                text=True,
            )
            if pip_result.returncode != 0:
                print(
                    f"Error: pip uninstall failed:\n{pip_result.stderr}",
                    file=sys.stderr,
                )
                return 1

        ExtensionRegistry.remove_extension(name)
        print(f"Extension '{name}' uninstalled.")
        return 0

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

        if not url.startswith("https://"):
            print(
                f"Error: Unsupported URL scheme in '{url}'. Only 'https://' and 'file://' are supported.",
                file=sys.stderr,
            )
            return False

        try:
            with urlopen(url, timeout=_REQUEST_TIMEOUT_SECONDS) as resp:
                final_url = resp.geturl()
                parsed_final = urlparse(final_url)
                if parsed_final.scheme.lower() != "https":
                    print(
                        "Error: Download was redirected to a non-HTTPS URL "
                        f"('{final_url}'). Insecure downloads are not allowed.",
                        file=sys.stderr,
                    )
                    return False

                with dest.open("wb") as out:
                    shutil.copyfileobj(resp, out)
            return True
        except Exception as exc:
            print(f"Error: Download failed for '{url}': {exc}", file=sys.stderr)
            return False

    @staticmethod
    @staticmethod
    def _safe_extract_wheel(zf: zipfile.ZipFile, dest_dir: Path) -> None:
        """
        Safely extract a wheel, ensuring no archive entry escapes *dest_dir*.

        Raises:
            ValueError: If an entry's resolved path is outside *dest_dir*.
        """
        dest_dir_resolved = dest_dir.resolve()

        for member in zf.infolist():
            member_path = Path(member.filename)

            # Skip empty names
            if not member.filename:
                continue

            target_path = (dest_dir_resolved / member_path).resolve()

            # Prevent Zip Slip / path traversal by ensuring the target path
            # stays within the destination directory.
            if target_path != dest_dir_resolved and dest_dir_resolved not in target_path.parents:
                raise ValueError(f"Illegal path in wheel entry: {member.filename!r}")

            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
                continue

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member, "r") as source, target_path.open("wb") as target:
                shutil.copyfileobj(source, target)

    def _install_wheel(whl_path: Path, source_url: str) -> int:
        """
        Install *whl_path* and register the extension.

        In a normal Python environment the wheel is installed via ``pip`` so that
        the extension's entry point is discoverable by ``importlib.metadata``.
        In a frozen binary the wheel is extracted manually because ``pip`` is not
        available, and the extension is loaded later via ``sys.path`` injection.

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

            ext_name, module_name, class_name, version, dist_name = entry_point_info

            command_name = ext_name
            if getattr(sys, "frozen", False):
                # Frozen binary: extract wheel contents and inject via sys.path at runtime.
                ext_dir = ExtensionRegistry.get_extensions_dir() / ext_name
                src_dir = ext_dir / "src"
                if src_dir.exists():
                    try:
                        shutil.rmtree(src_dir)
                    except FileNotFoundError:
                        # Directory was removed concurrently; safe to proceed.
                        pass
                src_dir.mkdir(parents=True, exist_ok=True)
                try:
                    ExtensionCommand._safe_extract_wheel(zf, src_dir)
                except ValueError as exc:
                    print(
                        f"Error: Unsafe path found in wheel '{whl_path.name}': {exc}",
                        file=sys.stderr,
                    )
                    return 1
                resolved_command_name = _resolve_extension_command_name(
                    module_name,
                    class_name,
                    src_dir,
                )
                if resolved_command_name is None:
                    print(
                        "Error: Unable to determine extension command name from "
                        f"{module_name}.{class_name}.",
                        file=sys.stderr,
                    )
                    return 1
                if resolved_command_name != ext_name:
                    print(
                        "Error: Extension command name mismatch: entry point "
                        f"'{ext_name}' does not match extension.command_name "
                        f"'{resolved_command_name}'. These values must be identical.",
                        file=sys.stderr,
                    )
                    return 1
                command_name = resolved_command_name
                metadata: dict = {
                    "version": version,
                    "source_url": source_url,
                    "source_path": str(src_dir),
                    "module": module_name,
                    "class": class_name,
                    "command_name": command_name,
                    "dist_name": dist_name,
                }
            else:
                # Normal Python: pip-install the wheel so entry points are registered.
                # --upgrade ensures a newer version replaces the old one;
                # --no-deps avoids re-downloading unchanged transitive dependencies.
                pip_result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "--no-deps", str(whl_path)],
                    capture_output=True,
                    text=True,
                )
                if pip_result.returncode != 0:
                    print(
                        f"Error: pip install failed:\n{pip_result.stderr}",
                        file=sys.stderr,
                    )
                    return 1
                resolved_command_name = _resolve_extension_command_name(
                    module_name,
                    class_name,
                )
                if resolved_command_name is None:
                    print(
                        "Error: Unable to determine extension command name from "
                        f"{module_name}.{class_name}.",
                        file=sys.stderr,
                    )
                    return 1
                if resolved_command_name != ext_name:
                    print(
                        "Error: Extension command name mismatch: entry point "
                        f"'{ext_name}' does not match extension.command_name "
                        f"'{resolved_command_name}'. These values must be identical.",
                        file=sys.stderr,
                    )
                    return 1
                command_name = resolved_command_name
                metadata = {
                    "version": version,
                    "source_url": source_url,
                    "module": module_name,
                    "class": class_name,
                    "command_name": command_name,
                    "dist_name": dist_name,
                }

        ExtensionRegistry.add_extension(command_name, metadata)
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
    def _extract_entry_point(zf: zipfile.ZipFile) -> Optional[tuple[str, str, str, str, str]]:
        """
        Parse the wheel's ``entry_points.txt`` and return the first ``opentoken.extensions`` entry.

        Also reads the ``METADATA`` file to obtain the package version and distribution name.

        Returns:
            ``(entry_name, module, class_name, version, dist_name)`` or ``None`` if not found.
        """
        ep_candidates = [n for n in zf.namelist() if n.endswith(".dist-info/entry_points.txt")]
        if not ep_candidates:
            return None

        raw = zf.read(ep_candidates[0]).decode("utf-8", errors="replace")
        cp = configparser.ConfigParser(interpolation=None)
        cp.optionxform = str
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

        # Read version and dist name from METADATA.
        version = "0.0.0"
        dist_name = entry_name
        metadata_candidates = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
        if metadata_candidates:
            meta_content = zf.read(metadata_candidates[0]).decode("utf-8", errors="replace")
            for line in meta_content.splitlines():
                if line.startswith("Version:"):
                    version = line.split(":", 1)[1].strip()
                elif line.startswith("Name:"):
                    dist_name = line.split(":", 1)[1].strip()

        return entry_name, module_name, class_name, version, dist_name
