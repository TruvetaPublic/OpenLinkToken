# SPDX-License-Identifier: MIT

import configparser
import hashlib
import importlib
import json
import logging
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Optional
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname, urlopen

from packaging.markers import UndefinedEnvironmentName, default_environment
from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

from openlinktoken_cli.extension.core_runtime_inventory import (
    CoreRuntimeInventoryError,
    load_core_runtime_inventory,
)
from openlinktoken_cli.extension.extension_bundle import (
    BundleValidationError,
    current_extension_target,
    extract_and_validate_bundle,
    install_wheel_file,
)
from openlinktoken_cli.extension.extension_loader import BUILTIN_COMMANDS
from openlinktoken_cli.extension.extension_manifest import (
    CURRENT_CORE_VERSION,
    STANDALONE_EXTENSION_RUNTIME_PROTOCOL,
    BundleRecord,
    ExtensionManifest,
    ManifestValidationError,
    is_core_compatible,
    parse_manifest,
)
from openlinktoken_cli.extension.extension_registry import ExtensionRegistry
from openlinktoken_cli.util.app_paths import get_openlinktoken_home

logger = logging.getLogger(__name__)


@contextmanager
def _temporary_sys_path(path: Optional[Path]):
    """
    Temporarily add ``path`` to ``sys.path`` for dynamic imports.

    Args:
        path: Directory to temporarily add to Python's module search path.

    Yields:
        Control passes to the with block while the temporary directories are on sys.path.
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

    Args:
        module_name: Name of the module.
        class_name: Name of the class.
        src_dir: Directory used for the src.

    Returns:
        Resolved extension command name as a str] instance.
    """
    try:
        from openlinktoken_cli.extension.extension_interface import OpenLinkTokenExtension

        module_root = module_name.split(".", 1)[0]
        for loaded_name in list(sys.modules):
            if loaded_name == module_root or loaded_name.startswith(f"{module_root}."):
                sys.modules.pop(loaded_name, None)
        importlib.invalidate_caches()
        with _temporary_sys_path(src_dir):
            module = importlib.import_module(module_name)
            extension_cls = getattr(module, class_name)
            extension_obj = extension_cls()
            if not isinstance(extension_obj, OpenLinkTokenExtension):
                return None
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
    "WARNING: Extensions are arbitrary Python code and are not verified by the Open Link Token project. "
    "Install only extensions from sources you trust."
)

_REQUEST_TIMEOUT_SECONDS = 60
_MANIFEST_CACHE_TTL_SECONDS = 24 * 60 * 60

#: PEP 508 / PEP 440 package name pattern (letters, digits, dashes, dots, underscores;
#: must start and end with a letter or digit).
_VALID_DIST_NAME_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$")


def _validate_dist_name(dist_name: str) -> bool:
    """
    Return *True* if *dist_name* is a valid PEP 508 distribution name.

    Args:
        dist_name: Name of the dist.

    Returns:
        True when the check succeeds; otherwise, False.
    """
    return bool(_VALID_DIST_NAME_RE.match(dist_name))


class ExtensionCommand:
    """
    Manage Open Link Token CLI extensions.

    Provides sub-subcommands to install, list, and uninstall extensions.
    """

    @staticmethod
    def register_subcommand(subparsers) -> None:
        """
        Register the ``extension`` subcommand and its sub-subcommands.

        Args:
            subparsers: Argument-parser subparsers to configure with command handlers.
        """
        parser = subparsers.add_parser(
            "extension",
            help="Manage Open Link Token CLI extensions",
            description="Install, list, and uninstall Open Link Token CLI extensions.",
        )
        sub = parser.add_subparsers(dest="extension_subcommand")

        # install
        install_parser = sub.add_parser(
            "install",
            help="Install an extension from a URL or local file path",
        )
        install_source = install_parser.add_mutually_exclusive_group(required=True)
        install_source.add_argument(
            "url",
            nargs="?",
            help="Wheel or bootstrap manifest URL/path",
        )
        install_source.add_argument(
            "--manifest",
            dest="manifest",
            help="Explicit bootstrap manifest URL/path",
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
        update_parser = sub.add_parser("update", help="Update one or all persistent extensions")
        update_target = update_parser.add_mutually_exclusive_group(required=True)
        update_target.add_argument("name", nargs="?", help="Extension name to update")
        update_target.add_argument("--all", action="store_true", dest="all", help="Update every installed extension")
        update_parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            default=False,
            dest="yes",
            help="Skip confirmation prompts",
        )
        update_parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            dest="dry_run",
            help="Show compatible updates without installing them",
        )
        update_parser.set_defaults(func=ExtensionCommand._update)

        parser.set_defaults(func=lambda args: (parser.print_help(), 0)[1])

    # ------------------------------------------------------------------
    # Sub-command handlers
    # ------------------------------------------------------------------

    @staticmethod
    def _install(args) -> int:
        """
        Handle ``extension install <url>``.

        Args:
            args: Parsed command-line options for this command.

        Returns:
            Integer value produced by install.
        """
        manifest_option = getattr(args, "manifest", None)
        if not isinstance(manifest_option, str):
            manifest_option = None
        url_option = getattr(args, "url", None)
        if not isinstance(url_option, str):
            url_option = None
        url = manifest_option or url_option
        if not url:
            print("Error: Provide a wheel or bootstrap manifest URL/path.", file=sys.stderr)
            return 1
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
            # Preserve the source filename for readable diagnostics, then inspect
            # the downloaded bytes to support manifest URLs without relying on a
            # filename suffix.
            url_filename = Path(urlparse(url).path or url).name
            download_name = url_filename or "extension.download"
            tmp_path = Path(tmp_dir) / download_name
            if not ExtensionCommand._download(url, tmp_path):
                return 1

            if zipfile.is_zipfile(tmp_path):
                return ExtensionCommand._install_wheel(tmp_path, source_url=url)

            try:
                manifest_payload = json.loads(tmp_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                print(
                    f"Error: '{url}' is neither a valid wheel nor a JSON bootstrap manifest.",
                    file=sys.stderr,
                )
                return 1
            return ExtensionCommand._install_bootstrap_manifest(
                manifest_payload,
                source_url=url,
            )

    @staticmethod
    def _install_bootstrap_manifest(payload: object, *, source_url: str) -> int:
        """
        Validate a bootstrap manifest and install its declared wheel.

        Args:
            payload: Structured payload to parse, validate, or encrypt.
            source_url: URL for the source resource.

        Returns:
            Validated a bootstrap manifest and install its declared wheel.
        """
        parsed_source = urlparse(source_url)
        allow_local = parsed_source.scheme == "file" or (
            not parsed_source.scheme and Path(source_url).expanduser().is_file()
        )
        try:
            manifest = parse_manifest(payload, allow_local=allow_local)
        except ManifestValidationError as exc:
            print(f"Error: Invalid bootstrap manifest: {exc}", file=sys.stderr)
            return 1
        if manifest.schema_version == 2:
            if not getattr(sys, "frozen", False):
                print(
                    "Error: Schema-version-2 dependency bundles are supported by the standalone CLI only.",
                    file=sys.stderr,
                )
                return 1
            if not ExtensionCommand._supports_runtime_protocol(manifest):
                return 1
            bundle = ExtensionCommand._select_bundle(manifest)
            if bundle is None:
                return 1
            with tempfile.TemporaryDirectory() as tmp_dir:
                bundle_path = Path(tmp_dir) / (Path(urlparse(bundle.url).path).name or "extension-bundle.zip")
                if not ExtensionCommand._download(bundle.url, bundle_path):
                    return 1
                return ExtensionCommand._install_frozen_bundle(
                    bundle_path,
                    source_url=bundle.url,
                    expected_sha256=bundle.sha256,
                    expected_name=manifest.name,
                    expected_version=manifest.version,
                    command_name=manifest.command_name or manifest.name,
                    description=manifest.description or "",
                    update_manifest_url=manifest.update_manifest_url,
                    core_range=manifest.core_specifier,
                )

        artifact = manifest.artifacts[0]
        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_name = Path(urlparse(artifact.url).path).name or "extension.whl"
            wheel_path = Path(tmp_dir) / artifact_name
            if not ExtensionCommand._download(artifact.url, wheel_path):
                return 1
            return ExtensionCommand._install_wheel(
                wheel_path,
                source_url=artifact.url,
                expected_sha256=artifact.sha256,
                signature=artifact.signature,
                update_manifest_url=manifest.update_manifest_url,
                core_range=manifest.core_specifier,
                expected_name=manifest.name,
                expected_version=manifest.version,
            )

    @staticmethod
    def _supports_runtime_protocol(manifest: ExtensionManifest) -> bool:
        """
        Ensure the manifest's worker protocol is supported by this binary.

        Args:
            manifest: Validated schema-version-2 extension manifest.

        Returns:
            Whether the current standalone runtime supports the requested protocol.
        """
        protocol = manifest.minimum_runtime_protocol
        if protocol is None or protocol > STANDALONE_EXTENSION_RUNTIME_PROTOCOL:
            required = protocol if protocol is not None else "unknown"
            print(
                f"Error: This extension requires runtime protocol {required}; "
                f"update Open Link Token to a runtime supporting protocol "
                f"{STANDALONE_EXTENSION_RUNTIME_PROTOCOL} or later.",
                file=sys.stderr,
            )
            return False
        return True

    @staticmethod
    def _select_bundle(manifest: ExtensionManifest) -> Optional[BundleRecord]:
        """
        Select the bundle matching this runtime's operating system, architecture, and ABI.

        Args:
            manifest: Validated schema-version-2 extension manifest.

        Returns:
            Matching bundle record, or ``None`` after printing an actionable error.
        """
        try:
            target, python_abi = current_extension_target()
        except BundleValidationError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return None
        for bundle in manifest.bundles:
            if bundle.target == target and bundle.python_abi == python_abi:
                return bundle
        print(
            f"Error: No extension bundle is available for {target}/{python_abi}. "
            "Update Open Link Token or use a supported platform.",
            file=sys.stderr,
        )
        return None

    @staticmethod
    def _list(args) -> int:  # noqa: ARG004
        """
        Handle ``extension list``.

        Args:
            args: Parsed command-line options for this command.

        Returns:
            The result value returned by the operation.
        """
        rows: dict[str, dict] = {}

        # Registry entries (installed via `extension install`).
        for name, meta in ExtensionRegistry.load().items():
            rows[name] = {
                "version": meta.get("version", ""),
                "command": meta.get("command_name", name),
                "source": meta.get("source_url", ""),
                "state": "disabled" if meta.get("disabled") else ("error" if meta.get("error") else "enabled"),
                "error": meta.get("error"),
            }

        # Entry-point extensions (installed via pip / editable install).
        # These are not in the registry, so we surface them separately.
        if not getattr(sys, "frozen", False):
            import importlib.metadata

            try:
                eps = importlib.metadata.entry_points(group="openlinktoken.extensions")
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
                            "state": "enabled",
                            "error": None,
                        }
            except Exception as exc:
                logger.debug("Could not query entry points for list: %s", exc)

        if not rows:
            print("No extensions installed.")
            return 0

        col_widths = {"name": 4, "version": 7, "command": 7, "source": 10, "state": 5}
        for name, meta in rows.items():
            col_widths["name"] = max(col_widths["name"], len(name))
            col_widths["version"] = max(col_widths["version"], len(meta["version"]))
            col_widths["command"] = max(col_widths["command"], len(meta["command"]))
            col_widths["source"] = max(col_widths["source"], len(meta["source"]))
            col_widths["state"] = max(col_widths["state"], len(meta["state"]))

        header = (
            f"{'Name':<{col_widths['name']}}  "
            f"{'Version':<{col_widths['version']}}  "
            f"{'Command':<{col_widths['command']}}  "
            f"{'State':<{col_widths['state']}}  "
            "Source"
        )
        print(header)
        print("-" * len(header))
        for name, meta in sorted(rows.items()):
            print(
                f"{name:<{col_widths['name']}}  "
                f"{meta['version']:<{col_widths['version']}}  "
                f"{meta['command']:<{col_widths['command']}}  "
                f"{meta['state']:<{col_widths['state']}}  "
                f"{meta['source']}"
            )
            if meta.get("error"):
                print(f"  Error: {meta['error']}")
        return 0

    @staticmethod
    def _uninstall(args) -> int:
        """
        Handle ``extension uninstall <name>``.

        Args:
            args: Parsed command-line options for this command.

        Returns:
            Integer value produced by uninstall.
        """
        name: str = args.name
        registry = ExtensionRegistry.load()

        if name not in registry:
            # Check if it exists as a pip-installed entry-point extension.
            pip_installed = False
            if not getattr(sys, "frozen", False):
                import importlib.metadata

                try:
                    eps = importlib.metadata.entry_points(group="openlinktoken.extensions")
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
                        eps = importlib.metadata.entry_points(group="openlinktoken.extensions")
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
            if not _validate_dist_name(name):
                print(f"Error: Invalid extension name '{name}'.", file=sys.stderr)
                return 1
            ext_dir = ExtensionRegistry.get_extensions_dir() / name
            if ext_dir.exists():
                shutil.rmtree(ext_dir)
        else:
            # Normal Python: uninstall via pip using the recorded dist name.
            dist_name = meta.get("dist_name") or name
            if not _validate_dist_name(dist_name):
                print(
                    f"Error: Recorded distribution name '{dist_name}' is not a valid package name "
                    "and cannot be passed to pip. Remove the extension manually.",
                    file=sys.stderr,
                )
                return 1
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

    @staticmethod
    def _update(args) -> int:
        """
        Handle ``extension update <name>`` and ``extension update --all``.

        Args:
            args: Parsed command-line options for this command.

        Returns:
            Updated result as a integer value.
        """
        registry = ExtensionRegistry.load()
        update_all = getattr(args, "all", False)
        names = sorted(registry) if update_all else [args.name]
        if not names:
            print("No extensions installed.")
            return 0
        failures = 0
        for name in names:
            result = ExtensionCommand._update_one(
                name,
                registry.get(name),
                dry_run=getattr(args, "dry_run", False),
                skip_confirm=getattr(args, "yes", False),
                require_manifest=not update_all,
            )
            if result != 0:
                failures += 1
        return 1 if failures else 0

    @staticmethod
    def _update_one(
        name: str,
        metadata: Optional[dict],
        *,
        dry_run: bool,
        skip_confirm: bool,
        require_manifest: bool = False,
    ) -> int:
        """
        Resolve, validate, and optionally install one manifest update.

        Args:
            name: Name identifying the item being processed.
            metadata: Metadata to validate, normalize, or serialize.
            dry_run: Whether to dry run.
            skip_confirm: Whether to skip confirm.
            require_manifest: Whether to require manifest.

        Returns:
            Updated one as a integer value.
        """
        if metadata is None:
            print(f"[{name}] failed: extension is not installed.", file=sys.stderr)
            return 1
        manifest_url = metadata.get("update_manifest_url")
        if not manifest_url:
            if require_manifest:
                print(f"[{name}] failed: no update manifest URL is registered.", file=sys.stderr)
                return 1
            print(f"[{name}] skipped: no update manifest URL is registered.")
            return 0
        try:
            manifest_payload = ExtensionCommand._fetch_manifest(manifest_url)
            manifest = parse_manifest(manifest_payload, expected_name=name)
        except (ManifestValidationError, OSError, ValueError) as exc:
            print(f"[{name}] failed: invalid update manifest: {exc}", file=sys.stderr)
            return 1
        if not is_core_compatible(CURRENT_CORE_VERSION, manifest.core_specifier):
            print(
                f"[{name}] failed: manifest requires core {manifest.core_specifier}, "
                f"but this binary is {CURRENT_CORE_VERSION}.",
                file=sys.stderr,
            )
            return 1
        if manifest.schema_version == 2:
            if not getattr(sys, "frozen", False):
                print(
                    f"[{name}] failed: schema-version-2 dependency bundles require the standalone CLI.",
                    file=sys.stderr,
                )
                return 1
            if not ExtensionCommand._supports_runtime_protocol(manifest):
                return 1

        current_version = metadata.get("version", "0.0.0")
        try:
            current = Version(current_version)
        except ValueError as exc:
            print(f"[{name}] failed: invalid installed version: {exc}", file=sys.stderr)
            return 1

        bundle = None
        artifact = None
        if manifest.schema_version == 2:
            if Version(manifest.version) <= current:
                print(f"[{name}] up to date ({current_version}).")
                return 0
            bundle = ExtensionCommand._select_bundle(manifest)
            if bundle is None:
                return 1
            artifact_version = manifest.version
            artifact_url = bundle.url
        else:
            candidates = [item for item in manifest.artifacts if item.version and Version(item.version) > current]
            if not candidates:
                print(f"[{name}] up to date ({current_version}).")
                return 0
            artifact = max(candidates, key=lambda item: Version(item.version or "0.0.0"))
            artifact_version = artifact.version or manifest.version
            artifact_url = artifact.url

        if dry_run:
            print(f"[{name}] would update {current_version} -> {artifact_version} from {artifact_url}")
            return 0

        if not skip_confirm:
            if not sys.stdin.isatty():
                print(f"[{name}] failed: pass --yes in non-interactive mode.", file=sys.stderr)
                return 1
            try:
                answer = input(f"Update extension '{name}' to {artifact_version}? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""
            if answer not in ("y", "yes"):
                print(f"[{name}] cancelled.")
                return 0

        with tempfile.TemporaryDirectory() as tmp_dir:
            filename = Path(urlparse(artifact_url).path).name or f"{name}.zip"
            artifact_path = Path(tmp_dir) / filename
            if not ExtensionCommand._download(artifact_url, artifact_path):
                print(f"[{name}] failed: artifact download failed.", file=sys.stderr)
                return 1
            if bundle is not None:
                result = ExtensionCommand._install_frozen_bundle(
                    artifact_path,
                    source_url=bundle.url,
                    expected_sha256=bundle.sha256,
                    expected_name=name,
                    expected_version=artifact_version,
                    command_name=manifest.command_name or name,
                    description=manifest.description or "",
                    update_manifest_url=manifest_url,
                    core_range=manifest.core_specifier,
                )
            else:
                result = ExtensionCommand._install_wheel(
                    artifact_path,
                    source_url=artifact_url,
                    expected_sha256=artifact.sha256,
                    signature=artifact.signature,
                    update_manifest_url=manifest_url,
                    core_range=manifest.core_specifier,
                    expected_name=name,
                    expected_version=artifact_version,
                )
        if result == 0:
            print(f"[{name}] updated to {artifact_version}.")
        else:
            print(f"[{name}] failed: previous installation was retained.", file=sys.stderr)
        return result

    @staticmethod
    def _install_frozen_bundle(
        bundle_path: Path,
        *,
        source_url: str,
        expected_sha256: str,
        expected_name: str,
        expected_version: str,
        command_name: str,
        description: str,
        update_manifest_url: Optional[str],
        core_range: str,
    ) -> int:
        """
        Validate, stage, and atomically activate a locked standalone bundle.

        Args:
            bundle_path: Downloaded bundle ZIP.
            source_url: URL used to fetch the bundle.
            expected_sha256: Bundle digest from the bootstrap or update manifest.
            expected_name: Expected extension command name.
            expected_version: Expected extension release version.
            command_name: Top-level command name from the manifest.
            description: Top-level help description from the manifest.
            update_manifest_url: URL for future extension updates.
            core_range: Core-version compatibility range required by the extension.

        Returns:
            Zero on success, or one if validation or activation fails.
        """
        if not getattr(sys, "frozen", False):
            print("Error: Locked dependency bundles require the standalone CLI.", file=sys.stderr)
            return 1
        if command_name in BUILTIN_COMMANDS:
            print(
                f"Error: Extension command '{command_name}' conflicts with a built-in command.",
                file=sys.stderr,
            )
            return 1
        if not _validate_dist_name(expected_name):
            print(f"Error: Invalid extension name '{expected_name}'.", file=sys.stderr)
            return 1
        if not is_core_compatible(CURRENT_CORE_VERSION, core_range):
            print(
                f"Error: Extension '{expected_name}' requires core '{core_range}', "
                f"but this binary is {CURRENT_CORE_VERSION}.",
                file=sys.stderr,
            )
            return 1

        actual_sha256 = ExtensionCommand._sha256_file(bundle_path)
        if actual_sha256 != expected_sha256.lower():
            print(
                f"Error: Bundle checksum verification failed.\n"
                f"  Expected: {expected_sha256}\n"
                f"  Actual  : {actual_sha256}",
                file=sys.stderr,
            )
            return 1
        try:
            core_inventory = load_core_runtime_inventory()
        except CoreRuntimeInventoryError as exc:
            print(f"Error: Could not verify the standalone core runtime: {exc}", file=sys.stderr)
            return 1

        extensions_dir = ExtensionRegistry.get_extensions_dir()
        versions_dir = extensions_dir / expected_name / "versions"
        stage_dir: Optional[Path] = None
        try:
            versions_dir.mkdir(parents=True, exist_ok=True)
            stage_dir = Path(tempfile.mkdtemp(prefix=".stage-", dir=versions_dir))
            with tempfile.TemporaryDirectory() as wheel_dir:
                wheels = extract_and_validate_bundle(
                    bundle_path,
                    Path(wheel_dir),
                    expected_name=expected_name,
                    expected_version=expected_version,
                    core_inventory=core_inventory,
                )
                extension_wheels = []
                entry_point_info = None
                extension_wheel = None
                for wheel in wheels:
                    with zipfile.ZipFile(wheel.path) as archive:
                        wheel_entry_point = ExtensionCommand._extract_entry_point(archive)
                    if wheel_entry_point is not None:
                        extension_wheels.append(wheel)
                        entry_point_info = wheel_entry_point
                        extension_wheel = wheel
                if len(extension_wheels) != 1 or entry_point_info is None or extension_wheel is None:
                    raise BundleValidationError("bundle must contain exactly one extension entry point")

                entry_name, module_name, class_name, version, dist_name = entry_point_info
                if entry_name != expected_name or command_name != expected_name:
                    raise BundleValidationError("extension command name does not match the bundle manifest")
                if Version(version) != Version(expected_version) or Version(extension_wheel.version) != Version(
                    expected_version
                ):
                    raise BundleValidationError("extension wheel version does not match the bundle manifest")
                if canonicalize_name(dist_name) != extension_wheel.name:
                    raise BundleValidationError("extension wheel distribution name does not match its lock entry")

                dependency_wheels = [wheel for wheel in wheels if wheel is not extension_wheel]
                install_wheel_file(extension_wheel.path, stage_dir / "extension")
                for wheel in dependency_wheels:
                    install_wheel_file(wheel.path, stage_dir / "dependencies")

            target, python_abi = current_extension_target()
            metadata = {
                "schema_version": 2,
                "version": expected_version,
                "source_url": source_url,
                "update_manifest_url": update_manifest_url,
                "supported_core": core_range,
                "supported_core_version_range": core_range,
                "core_range": core_range,
                "bundle_sha256": actual_sha256,
                "artifact_sha256": extension_wheel.sha256,
                "sha256": extension_wheel.sha256,
                "signature": None,
                "artifact_signature": None,
                "runtime_protocol": STANDALONE_EXTENSION_RUNTIME_PROTOCOL,
                "bundle_target": target,
                "python_abi": python_abi,
                "module": module_name,
                "class": class_name,
                "command_name": command_name,
                "description": description,
                "dist_name": dist_name,
                "distribution_name": dist_name,
                "disabled": False,
                "error": None,
            }
            ExtensionCommand._activate_frozen_install(
                stage_dir,
                extension_name=expected_name,
                version=expected_version,
                artifact_sha256=actual_sha256,
                metadata=metadata,
                source_relative_path=Path("extension") / "site-packages",
                dependency_relative_path=(Path("dependencies") / "site-packages" if dependency_wheels else None),
            )
            print(f"Extension '{expected_name}' (v{expected_version}) installed successfully.")
            print(f"Run: olt {command_name} --help")
            return 0
        except (BundleValidationError, CoreRuntimeInventoryError, OSError, ValueError, zipfile.BadZipFile) as exc:
            print(f"Error: Could not install dependency bundle for '{expected_name}': {exc}", file=sys.stderr)
            return 1
        finally:
            if stage_dir is not None and stage_dir.exists():
                shutil.rmtree(stage_dir, ignore_errors=True)

    @staticmethod
    def _activate_frozen_install(
        stage_dir: Path,
        *,
        extension_name: str,
        version: str,
        artifact_sha256: str,
        metadata: dict,
        source_relative_path: Path,
        dependency_relative_path: Optional[Path] = None,
    ) -> dict:
        """
        Atomically point the registry at a newly staged immutable extension version.

        Args:
            stage_dir: Staged extension version directory.
            extension_name: Registry key identifying the extension.
            version: Extension version string.
            artifact_sha256: Digest used to identify this immutable installation.
            metadata: Registry metadata to activate.
            source_relative_path: Relative path to the extension's installed Python files.
            dependency_relative_path: Optional path to private dependency Python files.

        Returns:
            The registry metadata with its final installation paths.

        Raises:
            OSError: If the staged directory or registry cannot be committed.
        """
        base_dir = ExtensionRegistry.get_extensions_dir()
        versions_dir = base_dir / extension_name / "versions"
        final_dir = versions_dir / f"{Version(version)}-{artifact_sha256[:16]}-{uuid.uuid4().hex[:8]}"
        metadata = dict(metadata)
        metadata["install_location"] = str(final_dir)
        metadata["source_path"] = str(final_dir / source_relative_path)
        if dependency_relative_path is not None:
            metadata["dependency_path"] = str(final_dir / dependency_relative_path)

        stage_dir.replace(final_dir)
        try:
            registry = ExtensionRegistry.load()
            registry[extension_name] = metadata
            ExtensionRegistry.save(registry)
        except OSError:
            shutil.rmtree(final_dir, ignore_errors=True)
            raise
        return metadata

    @staticmethod
    def _fetch_manifest(url: str) -> dict:
        """
        Fetch a data-only HTTPS manifest, using a bounded local cache.

        Args:
            url: URL for the remote manifest, artifact, or release resource to fetch.

        Returns:
            Mapping produced by fetch manifest.
        """
        cache_path = ExtensionCommand._manifest_cache_path(url)
        now = datetime.now(timezone.utc)
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            checked = datetime.fromisoformat(cached["last_checked"])
            if checked.tzinfo is None:
                checked = checked.replace(tzinfo=timezone.utc)
            if (now - checked).total_seconds() <= _MANIFEST_CACHE_TTL_SECONDS:
                return cached["payload"]
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            pass

        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ManifestValidationError("Update manifest URLs must use HTTPS.")
        request = urlopen(url, timeout=_REQUEST_TIMEOUT_SECONDS)
        with request as response:
            final_url = response.geturl()
            final_parsed = urlparse(final_url)
            if final_parsed.scheme != "https" or not final_parsed.netloc:
                raise ManifestValidationError("Update manifest redirected to a non-HTTPS URL.")
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ManifestValidationError("Update manifest must be a JSON object.")
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps({"last_checked": now.isoformat(), "payload": payload}),
                encoding="utf-8",
            )
        except OSError:
            logger.debug("Could not cache extension manifest %s", url, exc_info=True)
        return payload

    @staticmethod
    def _manifest_cache_path(url: str) -> Path:
        """
        Return a stable cache path for one vendor manifest URL.

        Args:
            url: URL for the remote manifest, artifact, or release resource to fetch.

        Returns:
            A stable cache path for one vendor manifest URL.
        """
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return get_openlinktoken_home() / "extension-manifests" / f"{key}.json"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _download(url: str, dest: Path) -> bool:
        """
        Download *url* to *dest*.

        Supports ``https://`` (via ``urllib.request.urlopen``) and
        ``file://`` (via ``shutil.copy``).

        Args:
            url: URL for the remote manifest, artifact, or release resource to fetch.
            dest: Destination path for the downloaded extension wheel.


        Returns:
            ``True`` on success, ``False`` on failure (error printed to stderr).
        """
        parsed_url = urlparse(url)
        if parsed_url.scheme == "file":
            if parsed_url.netloc not in ("", "localhost"):
                print(f"Error: Unsupported local file host in '{url}'.", file=sys.stderr)
                return False
            local_path = Path(url2pathname(unquote(parsed_url.path)))
            try:
                shutil.copy(str(local_path), str(dest))
                return True
            except OSError as exc:
                print(f"Error: Could not copy local file '{local_path}': {exc}", file=sys.stderr)
                return False

        local_path = Path(url).expanduser()
        if parsed_url.scheme != "https" and local_path.is_file():
            try:
                shutil.copy(str(local_path), str(dest))
                return True
            except OSError as exc:
                print(f"Error: Could not copy local file '{local_path}': {exc}", file=sys.stderr)
                return False

        if parsed_url.scheme != "https":
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
        except (OSError, ValueError) as exc:
            print(f"Error: Download failed for '{url}': {exc}", file=sys.stderr)
            return False

    @staticmethod
    def _safe_extract_wheel(zf: zipfile.ZipFile, dest_dir: Path) -> None:
        """
        Safely extract a wheel, ensuring no archive entry escapes *dest_dir*.

        Args:
            zf: Zf value to extract.
            dest_dir: Directory used for the dest.


        Raises:
            ValueError: If an entry's resolved path is outside *dest_dir*.
        """
        dest_dir_resolved = dest_dir.resolve()

        for member in zf.infolist():
            if not member.filename:
                continue
            member_path = PurePosixPath(member.filename)
            mode = member.external_attr >> 16
            if "\\" in member.filename or member_path.is_absolute() or ".." in member_path.parts or stat.S_ISLNK(mode):
                raise ValueError(f"Illegal path in wheel entry: {member.filename!r}")

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

    @staticmethod
    def _install_wheel(
        whl_path: Path,
        source_url: str,
        *,
        expected_sha256: Optional[str] = None,
        signature: Optional[dict[str, str]] = None,
        update_manifest_url: Optional[str] = None,
        core_range: Optional[str] = None,
        expected_name: Optional[str] = None,
        expected_version: Optional[str] = None,
    ) -> int:
        """
        Install *whl_path* and register the extension.

        In a normal Python environment the wheel is installed via ``pip`` so that
        the extension's entry point is discoverable by ``importlib.metadata``.
        In a frozen binary the wheel is extracted manually because ``pip`` is not
        available, and the extension is loaded later via ``sys.path`` injection.

        Args:
            whl_path: Path to the downloaded ``.whl`` file.
            source_url: Original URL used to fetch the wheel (stored in registry).
            expected_sha256: Expected sha256 used to check the actual result.
            signature: Artifact signature metadata to validate before installation.
            update_manifest_url: URL for the update manifest resource.
            core_range: Core-version compatibility range required by the extension manifest.
            expected_name: Expected name used to check the actual result.
            expected_version: Expected version used to check the actual result.

        Returns:
            Exit code (0 on success).
        """
        if not zipfile.is_zipfile(whl_path):
            print(f"Error: '{whl_path.name}' is not a valid wheel (zip) file.", file=sys.stderr)
            return 1

        actual_sha256 = ExtensionCommand._sha256_file(whl_path)
        if expected_sha256 and actual_sha256 != expected_sha256.lower():
            print(
                f"Error: Checksum verification failed.\n  Expected: {expected_sha256}\n  Actual  : {actual_sha256}",
                file=sys.stderr,
            )
            return 1

        with zipfile.ZipFile(whl_path, "r") as zf:
            if getattr(sys, "frozen", False):
                issue = ExtensionCommand._check_frozen_deps(zf)
                if issue:
                    print(
                        f"Error: This extension requires external dependencies that are not bundled "
                        f"in the Open Link Token binary: {issue}\n"
                        "Install it from a schema-version-2 dependency bundle or use the Python-package CLI.",
                        file=sys.stderr,
                    )
                    return 1

            entry_point_info = ExtensionCommand._extract_entry_point(zf)
            if entry_point_info is None:
                print(
                    "Error: No 'openlinktoken.extensions' entry point found in the wheel.",
                    file=sys.stderr,
                )
                return 1

            ext_name, module_name, class_name, version, dist_name = entry_point_info
            if expected_name and ext_name != expected_name:
                print(
                    f"Error: Manifest extension '{expected_name}' does not match wheel entry point '{ext_name}'.",
                    file=sys.stderr,
                )
                return 1
            if expected_version and Version(version) != Version(expected_version):
                print(
                    f"Error: Manifest version '{expected_version}' does not match wheel version '{version}'.",
                    file=sys.stderr,
                )
                return 1
            if core_range and not is_core_compatible(CURRENT_CORE_VERSION, core_range):
                print(
                    f"Error: Extension '{ext_name}' requires core '{core_range}', "
                    f"but this binary is {CURRENT_CORE_VERSION}.",
                    file=sys.stderr,
                )
                return 1
            if getattr(sys, "frozen", False) and not _validate_dist_name(ext_name):
                print(
                    f"Error: Wheel entry-point key '{ext_name}' is not a valid extension name.",
                    file=sys.stderr,
                )
                return 1

            command_name = ext_name
            if getattr(sys, "frozen", False):
                metadata = ExtensionCommand._install_frozen_wheel(
                    zf,
                    ext_name=ext_name,
                    module_name=module_name,
                    class_name=class_name,
                    version=version,
                    dist_name=dist_name,
                    source_url=source_url,
                    artifact_sha256=actual_sha256,
                    signature=signature,
                    update_manifest_url=update_manifest_url,
                    core_range=core_range,
                )
                if metadata is None:
                    return 1
                command_name = metadata["command_name"]
            else:
                # Normal Python: pip-install the wheel so entry points are registered.
                if not _validate_dist_name(ext_name):
                    print(
                        f"Error: Wheel entry-point key '{ext_name}' is not a valid extension name.",
                        file=sys.stderr,
                    )
                    return 1
                # --upgrade ensures a newer version replaces the old one.
                # --no-deps is intentionally omitted here so that pip resolves transitive
                # dependencies normally; omitting it in non-frozen mode prevents silent
                # load failures caused by missing transitive packages.
                pip_result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", str(whl_path)],
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
                        f"Error: Unable to determine extension command name from {module_name}.{class_name}.",
                        file=sys.stderr,
                    )
                    logger.warning(
                        "Rolling back pip install of '%s' because the extension class could not be resolved.",
                        dist_name,
                    )
                    subprocess.run(
                        [sys.executable, "-m", "pip", "uninstall", "-y", dist_name],
                        check=False,
                    )
                    return 1
                if resolved_command_name != ext_name:
                    print(
                        "Error: Extension command name mismatch: entry point "
                        f"'{ext_name}' does not match extension.command_name "
                        f"'{resolved_command_name}'. These values must be identical.",
                        file=sys.stderr,
                    )
                    logger.warning(
                        "Rolling back pip install of '%s' because the resolved command name '%s' "
                        "does not match the expected name '%s'.",
                        dist_name,
                        resolved_command_name,
                        ext_name,
                    )
                    subprocess.run(
                        [sys.executable, "-m", "pip", "uninstall", "-y", dist_name],
                        check=False,
                    )
                    return 1
                command_name = resolved_command_name
                metadata = {
                    "schema_version": 1,
                    "version": version,
                    "source_url": source_url,
                    "install_location": None,
                    "module": module_name,
                    "class": class_name,
                    "command_name": command_name,
                    "dist_name": dist_name,
                    "distribution_name": dist_name,
                    "artifact_sha256": actual_sha256,
                    "sha256": actual_sha256,
                    "signature": signature,
                    "artifact_signature": signature,
                    "update_manifest_url": update_manifest_url,
                    "supported_core": core_range,
                    "supported_core_version_range": core_range,
                    "core_range": core_range,
                    "disabled": False,
                    "error": None,
                }

        if getattr(sys, "frozen", False):
            # _install_frozen_wheel commits the directory and registry together.
            print(f"Extension '{ext_name}' (v{version}) installed successfully.")
            print(f"Run: olt {ext_name} --help")
            return 0

        ExtensionRegistry.add_extension(command_name, metadata)
        print(f"Extension '{ext_name}' (v{version}) installed successfully.")
        print(f"Run: olt {ext_name} --help")
        return 0

    @staticmethod
    def _install_frozen_wheel(
        zf: zipfile.ZipFile,
        *,
        ext_name: str,
        module_name: str,
        class_name: str,
        version: str,
        dist_name: str,
        source_url: str,
        artifact_sha256: str,
        signature: Optional[dict[str, str]],
        update_manifest_url: Optional[str],
        core_range: Optional[str],
    ) -> Optional[dict]:
        """
        Stage, validate, and atomically activate one frozen extension.

        Args:
            zf: ZipFile archive containing the extension wheel to install.
            ext_name: Name of the ext.
            module_name: Name of the module.
            class_name: Name of the class.
            version: Version string to validate, compare, or include in generated metadata.
            dist_name: Name of the dist.
            source_url: URL for the source resource.
            artifact_sha256: Expected SHA-256 digest of the wheel artifact.
            signature: Artifact signature metadata to validate before installation.
            update_manifest_url: URL for the update manifest resource.
            core_range: Core-version compatibility range required by the extension manifest.

        Returns:
            Mapping produced by install frozen wheel.
        """
        if not _validate_dist_name(ext_name):
            print(f"Error: Wheel entry-point key '{ext_name}' is not a valid extension name.", file=sys.stderr)
            return None
        versions_dir = ExtensionRegistry.get_extensions_dir() / ext_name / "versions"
        stage_dir: Optional[Path] = None
        try:
            versions_dir.mkdir(parents=True, exist_ok=True)
            stage_dir = Path(tempfile.mkdtemp(prefix=f".{ext_name}.stage-", dir=versions_dir))
            src_dir = stage_dir / "src"
            src_dir.mkdir(parents=True, exist_ok=True)
            ExtensionCommand._safe_extract_wheel(zf, src_dir)
            resolved_command_name = ext_name
            metadata = {
                "schema_version": 1,
                "version": version,
                "source_url": source_url,
                "update_manifest_url": update_manifest_url,
                "supported_core": core_range,
                "supported_core_version_range": core_range,
                "core_range": core_range,
                "artifact_sha256": artifact_sha256,
                "sha256": artifact_sha256,
                "signature": signature,
                "artifact_signature": signature,
                "module": module_name,
                "class": class_name,
                "command_name": resolved_command_name,
                "description": None,
                "dist_name": dist_name,
                "distribution_name": dist_name,
                "disabled": False,
                "error": None,
            }
            return ExtensionCommand._activate_frozen_install(
                stage_dir,
                extension_name=ext_name,
                version=version,
                artifact_sha256=artifact_sha256,
                metadata=metadata,
                source_relative_path=Path("src"),
            )
        except (OSError, ValueError, ImportError) as exc:
            print(f"Error: Could not install frozen extension '{ext_name}': {exc}", file=sys.stderr)
            if stage_dir is not None and stage_dir.exists():
                shutil.rmtree(stage_dir, ignore_errors=True)
            return None

    @staticmethod
    def _sha256_file(path: Path) -> str:
        """
        Return the lowercase SHA-256 digest for a file.

        Args:
            path: Path to the file whose SHA-256 digest is computed.

        Returns:
            The lowercase SHA-256 digest for a file.
        """
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _check_frozen_deps(zf: zipfile.ZipFile) -> Optional[str]:
        """
        Return a description of unsatisfied external dependencies, or ``None`` if all are bundled.

        Reads ``Requires-Dist`` headers from the wheel's ``METADATA`` file.

        Args:
            zf: An open ZipFile handle for the wheel.

        Returns:
            A description of unsatisfied external dependencies, or ``None`` if all are bundled.
        """
        metadata_candidates = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
        if not metadata_candidates:
            return None

        if len(metadata_candidates) > 1:
            logger.warning(
                "Wheel contains multiple dist-info directories (%s); this is invalid per PEP 427. "
                "Only the first will be checked.",
                metadata_candidates,
            )

        try:
            core_inventory = load_core_runtime_inventory()
        except CoreRuntimeInventoryError as exc:
            return f"core runtime inventory is unavailable ({exc})"

        content = zf.read(metadata_candidates[0]).decode("utf-8", errors="replace")
        external = []
        for line in content.splitlines():
            if line.startswith("Requires-Dist:"):
                raw_dep = line.split(":", 1)[1].strip()
                try:
                    req = Requirement(raw_dep)
                except InvalidRequirement:
                    external.append(f"invalid requirement '{raw_dep}'")
                    continue
                if req.marker is not None:
                    try:
                        if not req.marker.evaluate(environment=default_environment()):
                            continue  # marker evaluates to False in this environment; skip
                    except UndefinedEnvironmentName:
                        continue  # marker references a variable missing from this environment (e.g. "extra")
                dep_name_norm = canonicalize_name(req.name)
                core_version = core_inventory.get(dep_name_norm)
                if core_version is None:
                    external.append(req.name)
                elif req.specifier and Version(core_version) not in req.specifier:
                    external.append(f"{req.name} {req.specifier} (core provides {core_version})")
        return ", ".join(external) if external else None

    @staticmethod
    def _extract_entry_point(zf: zipfile.ZipFile) -> Optional[tuple[str, str, str, str, str]]:
        """
        Parse the wheel's ``entry_points.txt`` and return the first ``openlinktoken.extensions`` entry.

        Also reads the ``METADATA`` file to obtain the package version and distribution name.

        Args:
            zf: Zf value to extract.


        Returns:
            ``(entry_name, module, class_name, version, dist_name)`` or ``None`` if not found.
        """
        ep_candidates = [n for n in zf.namelist() if n.endswith(".dist-info/entry_points.txt")]
        if not ep_candidates:
            return None

        raw = zf.read(ep_candidates[0]).decode("utf-8", errors="replace")
        cp = configparser.ConfigParser(interpolation=None)
        cp.optionxform = str
        try:
            cp.read_string(raw)
        except configparser.Error:
            return None

        if not cp.has_section("openlinktoken.extensions"):
            return None

        items = list(cp.items("openlinktoken.extensions"))
        if not items:
            return None

        if len(items) > 1:
            logger.warning(
                "Wheel contains %d openlinktoken.extensions entry points; only the first (%s) will be registered.",
                len(items),
                items[0][0],
            )

        entry_name, target = items[0]
        # target is like "some.module:ClassName"
        if ":" not in target:
            return None
        module_name, class_name = target.rsplit(":", 1)
        module_name = module_name.strip()
        class_name = class_name.strip()
        if not module_name or not class_name or not all(part.isidentifier() for part in module_name.split(".")):
            return None
        if not class_name.isidentifier():
            return None

        # Read version and dist name from METADATA.
        version = ""
        dist_name = ""
        metadata_candidates = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
        if len(metadata_candidates) != 1:
            return None
        meta_content = zf.read(metadata_candidates[0]).decode("utf-8", errors="replace")
        for line in meta_content.splitlines():
            if line.startswith("Version:"):
                version = line.split(":", 1)[1].strip()
            elif line.startswith("Name:"):
                dist_name = line.split(":", 1)[1].strip()
        if not version or not dist_name or not _validate_dist_name(dist_name):
            return None
        try:
            Version(version)
        except ValueError:
            return None

        return entry_name, module_name, class_name, version, dist_name
