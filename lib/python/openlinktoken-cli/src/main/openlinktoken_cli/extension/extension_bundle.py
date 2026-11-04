# SPDX-License-Identifier: MIT
"""Validation and offline installation helpers for standalone extension bundles."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import stat
import sys
import zipfile
from collections import defaultdict, deque
from dataclasses import dataclass
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import Mapping

from installer import install
from installer.destinations import SchemeDictionaryDestination
from installer.exceptions import InstallerError
from installer.sources import WheelFile
from packaging.markers import UndefinedEnvironmentName, default_environment
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.tags import sys_tags
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import InvalidVersion, Version

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_BUNDLE_MANIFEST_NAME = "bundle-manifest.json"


class BundleValidationError(ValueError):
    """Raised when an extension dependency bundle is incomplete or inconsistent."""


@dataclass(frozen=True)
class LockedWheel:
    """A wheel file validated against the bundle's lock manifest."""

    filename: str
    name: str
    version: str
    tags: frozenset[str]
    sha256: str
    path: Path
    requirements: tuple[str, ...]


def current_extension_target() -> tuple[str, str]:
    """
    Return this standalone runtime's supported bundle target and CPython ABI.

    Returns:
        The platform target and ABI, such as ``("linux-x64", "cp312")``.

    Raises:
        BundleValidationError: If the standalone platform is not supported.
    """
    if sys.implementation.name != "cpython":
        raise BundleValidationError("extension bundles require the embedded CPython runtime")

    machine = platform.machine().lower()
    if machine in {"amd64", "x64"}:
        machine = "x86_64"
    elif machine == "aarch64":
        machine = "arm64"

    if sys.platform == "linux" and machine == "x86_64":
        target = "linux-x64"
    elif sys.platform == "win32" and machine == "x86_64":
        target = "windows-x64"
    elif sys.platform == "darwin" and machine == "arm64":
        target = "macos-arm64"
    else:
        raise BundleValidationError(f"unsupported standalone extension target: {sys.platform}/{machine}")

    cache_tag = sys.implementation.cache_tag or ""
    if not cache_tag.startswith("cpython-"):
        raise BundleValidationError(f"could not determine the embedded CPython ABI from '{cache_tag}'")
    abi = f"cp{cache_tag.removeprefix('cpython-')}"
    return target, abi


def extract_and_validate_bundle(
    bundle_path: Path,
    destination: Path,
    *,
    expected_name: str,
    expected_version: str,
    core_inventory: Mapping[str, str],
) -> tuple[LockedWheel, ...]:
    """
    Verify a bundle lock and extract its wheel files without installing them.

    Args:
        bundle_path: Downloaded bundle ZIP.
        destination: Temporary directory for the verified wheels.
        expected_name: Extension command name required by the bootstrap manifest.
        expected_version: Extension version required by the bootstrap manifest.
        core_inventory: Normalized core distribution names and fixed versions.

    Returns:
        The extension wheel and all locked dependency wheels.

    Raises:
        BundleValidationError: If the bundle, wheel metadata, or dependency lock is invalid.
        OSError: If a verified wheel cannot be written to the staging directory.
    """
    target, abi = current_extension_target()
    accepted_tags = {str(tag) for tag in sys_tags()}
    normalized_core = {canonicalize_name(name): version for name, version in core_inventory.items()}
    destination.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(bundle_path) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise BundleValidationError("bundle contains duplicate archive entries")
        for info in infos:
            _validate_archive_filename(info)

        manifest_info = next((info for info in infos if info.filename == _BUNDLE_MANIFEST_NAME), None)
        if manifest_info is None:
            raise BundleValidationError(f"bundle is missing {_BUNDLE_MANIFEST_NAME}")
        try:
            bundle_manifest = json.loads(archive.read(manifest_info).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BundleValidationError(f"{_BUNDLE_MANIFEST_NAME} is not valid UTF-8 JSON") from exc

        wheel_records = _parse_bundle_manifest(
            bundle_manifest,
            expected_name=expected_name,
            expected_version=expected_version,
            expected_target=target,
            expected_abi=abi,
            accepted_tags=accepted_tags,
        )
        expected_files = {_BUNDLE_MANIFEST_NAME, *(record.filename for record in wheel_records)}
        if set(names) != expected_files:
            unexpected = sorted(set(names) - expected_files)
            missing = sorted(expected_files - set(names))
            details = []
            if unexpected:
                details.append(f"unexpected files: {', '.join(unexpected)}")
            if missing:
                details.append(f"missing files: {', '.join(missing)}")
            raise BundleValidationError("bundle contents do not match its lock (" + "; ".join(details) + ")")

        info_by_name = {info.filename: info for info in infos}
        extracted = []
        for record in wheel_records:
            wheel_path = destination / record.filename
            digest = hashlib.sha256()
            with archive.open(info_by_name[record.filename]) as source, wheel_path.open("xb") as target_file:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
                    target_file.write(chunk)
            if digest.hexdigest() != record.sha256:
                raise BundleValidationError(f"SHA-256 mismatch for wheel '{record.filename}'")
            requirements = _validate_wheel_file(wheel_path, record)
            extracted.append(
                LockedWheel(
                    filename=record.filename,
                    name=record.name,
                    version=record.version,
                    tags=record.tags,
                    sha256=record.sha256,
                    path=wheel_path,
                    requirements=requirements,
                )
            )

    _validate_dependency_lock(extracted, normalized_core)
    return tuple(extracted)


def install_wheel_file(wheel_path: Path, destination: Path) -> None:
    """
    Install a validated wheel into a private, isolated filesystem scheme.

    Args:
        wheel_path: Wheel to install.
        destination: Root directory for this wheel's installed files.

    Raises:
        OSError: If the destination cannot be created or written.
        ValueError: If the wheel is rejected by the standards-compliant installer.
    """
    site_packages = destination / "site-packages"
    scheme_dict = {
        "purelib": str(site_packages),
        "platlib": str(site_packages),
        "headers": str(destination / "headers"),
        "scripts": str(destination / "bin"),
        "data": str(destination / "data"),
    }
    script_kind = "win-amd64" if sys.platform == "win32" else "posix"
    target = SchemeDictionaryDestination(
        scheme_dict=scheme_dict,
        interpreter=sys.executable,
        script_kind=script_kind,
    )
    try:
        with WheelFile.open(wheel_path) as source:
            install(source, target, {})
    except InstallerError as exc:
        raise BundleValidationError(f"could not install wheel '{wheel_path.name}': {exc}") from exc


@dataclass(frozen=True)
class _WheelRecord:
    """A validated entry read from bundle-manifest.json."""

    filename: str
    name: str
    version: str
    tags: frozenset[str]
    sha256: str


def _validate_archive_filename(info: zipfile.ZipInfo) -> None:
    """
    Reject paths and special files in the flat bundle and wheel archives.

    Args:
        info: Archive entry to validate.

    Raises:
        BundleValidationError: If the archive entry is not a regular root-level file.
    """
    name = info.filename
    path = PurePosixPath(name)
    mode = info.external_attr >> 16
    if (
        info.is_dir()
        or not name
        or "\\" in name
        or path.is_absolute()
        or len(path.parts) != 1
        or path.parts[0] in {".", ".."}
        or stat.S_ISLNK(mode)
    ):
        raise BundleValidationError(f"unsafe or unexpected archive path '{name}'")


def _parse_bundle_manifest(
    payload: object,
    *,
    expected_name: str,
    expected_version: str,
    expected_target: str,
    expected_abi: str,
    accepted_tags: set[str],
) -> tuple[_WheelRecord, ...]:
    """
    Validate bundle identity, target, and wheel lock records.

    Args:
        payload: Parsed JSON object from the bundle lock.
        expected_name: Extension command name from the outer manifest.
        expected_version: Extension version from the outer manifest.
        expected_target: Runtime platform target.
        expected_abi: Runtime CPython ABI.
        accepted_tags: Wheel tags accepted by the current interpreter.

    Returns:
        Validated wheel records.

    Raises:
        BundleValidationError: If any bundle manifest field is invalid.
    """
    schema_version = payload.get("schema_version") if isinstance(payload, dict) else None
    if (
        not isinstance(payload, dict)
        or isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != 1
    ):
        raise BundleValidationError("unsupported or malformed bundle manifest schema")
    extension = payload.get("extension")
    if not isinstance(extension, dict):
        raise BundleValidationError("bundle manifest requires an extension object")
    if extension.get("name") != expected_name or extension.get("version") != expected_version:
        raise BundleValidationError("bundle extension identity does not match the bootstrap manifest")
    if payload.get("target") != expected_target:
        raise BundleValidationError(
            f"bundle target '{payload.get('target')}' does not match this runtime '{expected_target}'"
        )
    if payload.get("python_abi") != expected_abi:
        raise BundleValidationError(
            f"bundle ABI '{payload.get('python_abi')}' does not match this runtime '{expected_abi}'"
        )

    records_payload = payload.get("wheels")
    if not isinstance(records_payload, list) or not records_payload:
        raise BundleValidationError("bundle manifest requires a non-empty wheels list")

    records = []
    filenames: set[str] = set()
    names: set[str] = set()
    for raw_record in records_payload:
        if not isinstance(raw_record, dict):
            raise BundleValidationError("each wheel lock entry must be an object")
        filename = raw_record.get("filename")
        name = raw_record.get("name")
        version = raw_record.get("version")
        raw_tags = raw_record.get("tags")
        sha256 = raw_record.get("sha256")
        if (
            not isinstance(filename, str)
            or not filename.endswith(".whl")
            or "\\" in filename
            or len(PurePosixPath(filename).parts) != 1
        ):
            raise BundleValidationError("wheel filename must be a .whl basename")
        if not isinstance(name, str) or canonicalize_name(name) != name:
            raise BundleValidationError(f"wheel name '{name}' must be normalized")
        if not isinstance(version, str):
            raise BundleValidationError(f"wheel '{filename}' requires a version")
        try:
            parsed_version = Version(version)
            parsed_name, filename_version, _, parsed_tags = parse_wheel_filename(filename)
        except (InvalidVersion, ValueError) as exc:
            raise BundleValidationError(f"invalid wheel filename or version '{filename}'") from exc
        if canonicalize_name(str(parsed_name)) != name or filename_version != parsed_version:
            raise BundleValidationError(f"wheel filename does not match lock identity for '{filename}'")
        if not isinstance(raw_tags, list) or not raw_tags or not all(isinstance(tag, str) for tag in raw_tags):
            raise BundleValidationError(f"wheel '{filename}' requires a non-empty tags list")
        tags = frozenset(raw_tags)
        actual_tags = frozenset(str(tag) for tag in parsed_tags)
        if tags != actual_tags:
            raise BundleValidationError(f"wheel tags do not match filename for '{filename}'")
        if not tags.intersection(accepted_tags):
            raise BundleValidationError(f"wheel '{filename}' is incompatible with this Python runtime")
        if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
            raise BundleValidationError(f"wheel '{filename}' requires a lowercase SHA-256 digest")
        if filename in filenames or name in names:
            raise BundleValidationError(f"bundle contains duplicate wheel '{filename}' or distribution '{name}'")
        filenames.add(filename)
        names.add(name)
        records.append(_WheelRecord(filename, name, str(parsed_version), tags, sha256))
    return tuple(records)


def _validate_wheel_file(wheel_path: Path, record: _WheelRecord) -> tuple[str, ...]:
    """
    Verify wheel paths and distribution metadata against one lock record.

    Args:
        wheel_path: Extracted wheel file.
        record: Corresponding validated lock entry.

    Returns:
        The wheel's Requires-Dist declarations.

    Raises:
        BundleValidationError: If the wheel is invalid or disagrees with its lock.
    """
    try:
        with zipfile.ZipFile(wheel_path) as wheel:
            infos = wheel.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise BundleValidationError(f"wheel '{record.filename}' contains duplicate archive entries")
            for info in infos:
                name = info.filename
                path = PurePosixPath(name)
                mode = info.external_attr >> 16
                if not name or "\\" in name or path.is_absolute() or ".." in path.parts or stat.S_ISLNK(mode):
                    raise BundleValidationError(f"wheel '{record.filename}' contains unsafe path '{name}'")
            metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
            if len(metadata_names) != 1:
                raise BundleValidationError(f"wheel '{record.filename}' must contain exactly one METADATA file")
            metadata = BytesParser().parsebytes(wheel.read(metadata_names[0]))
    except zipfile.BadZipFile as exc:
        raise BundleValidationError(f"wheel '{record.filename}' is not a valid ZIP archive") from exc

    raw_name = metadata.get("Name")
    raw_version = metadata.get("Version")
    if not isinstance(raw_name, str) or not isinstance(raw_version, str):
        raise BundleValidationError(f"wheel '{record.filename}' has incomplete distribution metadata")
    try:
        metadata_version = Version(raw_version)
    except InvalidVersion as exc:
        raise BundleValidationError(f"wheel '{record.filename}' has an invalid metadata version") from exc
    if canonicalize_name(raw_name) != record.name or metadata_version != Version(record.version):
        raise BundleValidationError(f"wheel metadata does not match lock entry for '{record.filename}'")
    raw_requires_python = metadata.get("Requires-Python")
    if raw_requires_python is not None:
        try:
            requires_python = SpecifierSet(raw_requires_python)
        except InvalidSpecifier as exc:
            raise BundleValidationError(f"wheel '{record.filename}' has invalid Requires-Python metadata") from exc
        runtime_version = Version(platform.python_version())
        if runtime_version not in requires_python:
            raise BundleValidationError(
                f"wheel '{record.filename}' has incompatible Requires-Python "
                f"'{raw_requires_python}' for runtime '{runtime_version}'"
            )
    return tuple(metadata.get_all("Requires-Dist", []))


def _validate_dependency_lock(wheels: list[LockedWheel], core_inventory: Mapping[str, str]) -> None:
    """
    Confirm every active runtime requirement is provided by the core or the lock.

    Args:
        wheels: Verified wheel records with their Requires-Dist metadata.
        core_inventory: Normalized core distribution names and versions.

    Raises:
        BundleValidationError: If the lock omits, duplicates, or conflicts with a dependency.
    """
    wheel_by_name = {wheel.name: wheel for wheel in wheels}
    for name in wheel_by_name:
        if name in core_inventory:
            raise BundleValidationError(f"bundle duplicates core-owned distribution '{name}'")

    extension_wheels = [wheel for wheel in wheels if _has_extension_entry_point(wheel.path)]
    if len(extension_wheels) != 1:
        raise BundleValidationError("bundle must contain exactly one extension wheel")
    root_name = extension_wheels[0].name

    requested_extras: dict[str, set[str]] = defaultdict(set)
    processed_extras: dict[str, set[str]] = {}
    pending = deque([root_name])
    reachable = {root_name}
    environment = default_environment()

    while pending:
        name = pending.popleft()
        extras = requested_extras[name]
        if name in processed_extras and processed_extras[name] >= extras:
            continue
        processed_extras[name] = set(extras)
        wheel = wheel_by_name[name]
        for raw_requirement in wheel.requirements:
            try:
                requirement = Requirement(raw_requirement)
            except InvalidRequirement as exc:
                raise BundleValidationError(
                    f"wheel '{wheel.filename}' declares invalid requirement '{raw_requirement}'"
                ) from exc
            contexts = {"", *extras}
            if requirement.marker is not None:
                try:
                    if not any(requirement.marker.evaluate(environment=environment, extra=extra) for extra in contexts):
                        continue
                except UndefinedEnvironmentName as exc:
                    raise BundleValidationError(
                        f"wheel '{wheel.filename}' has an unsupported dependency marker"
                    ) from exc

            dependency = canonicalize_name(requirement.name)
            if dependency in core_inventory:
                core_version = Version(core_inventory[dependency])
                if requirement.specifier and core_version not in requirement.specifier:
                    raise BundleValidationError(
                        f"core dependency conflict for '{dependency}': "
                        f"extension requires '{requirement.specifier}', core provides '{core_version}'"
                    )
                if requirement.extras:
                    raise BundleValidationError(
                        f"extension bundles may not request extras from core distribution '{dependency}'"
                    )
                continue

            locked = wheel_by_name.get(dependency)
            if locked is None:
                raise BundleValidationError(
                    f"bundle lock is incomplete: '{wheel.filename}' requires missing '{dependency}'"
                )
            dependency_version = Version(locked.version)
            if requirement.specifier and dependency_version not in requirement.specifier:
                raise BundleValidationError(
                    f"bundle version conflict for '{dependency}': "
                    f"'{wheel.filename}' requires '{requirement.specifier}', lock provides '{dependency_version}'"
                )
            reachable.add(dependency)
            new_extras = set(requirement.extras) - requested_extras[dependency]
            if dependency not in processed_extras or new_extras:
                requested_extras[dependency].update(new_extras)
                pending.append(dependency)

    unused = sorted(set(wheel_by_name) - reachable)
    if unused:
        raise BundleValidationError(f"bundle lock contains unreferenced wheels: {', '.join(unused)}")


def _has_extension_entry_point(wheel_path: Path) -> bool:
    """
    Return whether a wheel declares an Open Link Token extension entry point.

    Args:
        wheel_path: Wheel to inspect.

    Returns:
        Whether the wheel declares the ``openlinktoken.extensions`` group.
    """
    with zipfile.ZipFile(wheel_path) as wheel:
        for info in wheel.infolist():
            name = info.filename
            if name.endswith(".dist-info/entry_points.txt"):
                if "[openlinktoken.extensions]" in wheel.read(name).decode("utf-8", errors="replace"):
                    return True
    return False
