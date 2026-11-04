# SPDX-License-Identifier: MIT
"""Read and build the frozen CLI's bundled distribution inventory."""

from __future__ import annotations

import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Iterable

from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

_INVENTORY_RELATIVE_PATH = Path("openlinktoken_cli/data/core_runtime_inventory.json")
_CORE_DISTRIBUTIONS = ("openlinktoken-cli", "openlinktoken", "openlinktoken-core-ai")


class CoreRuntimeInventoryError(ValueError):
    """Raised when the frozen core distribution inventory is missing or invalid."""


def load_core_runtime_inventory(path: Path | None = None) -> dict[str, str]:
    """
    Load and validate the bundled distribution-to-version mapping.

    Args:
        path: Optional inventory path, primarily for focused tests.

    Returns:
        A mapping of normalized distribution names to installed versions.

    Raises:
        CoreRuntimeInventoryError: If the inventory is absent or malformed.
    """
    if path is None:
        bundle_root = getattr(sys, "_MEIPASS", None)
        if not bundle_root:
            raise CoreRuntimeInventoryError("the standalone runtime inventory is unavailable")
        path = Path(bundle_root) / _INVENTORY_RELATIVE_PATH

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CoreRuntimeInventoryError(f"could not read '{path}': {exc}") from exc

    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("schema_version"), int)
        or isinstance(payload.get("schema_version"), bool)
        or payload.get("schema_version") != 1
    ):
        raise CoreRuntimeInventoryError("unsupported or malformed inventory schema")
    distributions = payload.get("distributions")
    if not isinstance(distributions, dict) or not distributions:
        raise CoreRuntimeInventoryError("inventory has no distributions")

    normalized: dict[str, str] = {}
    for raw_name, raw_version in distributions.items():
        if not isinstance(raw_name, str) or not isinstance(raw_version, str):
            raise CoreRuntimeInventoryError("inventory distribution names and versions must be strings")
        name = canonicalize_name(raw_name)
        try:
            version = str(Version(raw_version))
        except InvalidVersion as exc:
            raise CoreRuntimeInventoryError(f"invalid version for '{raw_name}': {raw_version}") from exc
        if not name or name in normalized:
            raise CoreRuntimeInventoryError(f"duplicate or invalid distribution name '{raw_name}'")
        normalized[name] = version
    return normalized


def write_core_runtime_inventory(analysis_items: Iterable[tuple], output_path: Path) -> dict[str, str]:
    """
    Write versions for distributions whose files are included by PyInstaller.

    Args:
        analysis_items: PyInstaller Analysis entries from pure modules, binaries, and data.
        output_path: Destination for the generated JSON inventory.

    Returns:
        The normalized distribution-to-version mapping written to disk.

    Raises:
        CoreRuntimeInventoryError: If a core distribution cannot be identified.
        OSError: If the inventory cannot be written.
    """
    file_owners: dict[Path, tuple[str, str]] = {}
    for distribution in importlib.metadata.distributions():
        raw_name = distribution.metadata.get("Name")
        if not raw_name:
            continue
        name = canonicalize_name(raw_name)
        try:
            version = str(Version(distribution.version))
        except InvalidVersion as exc:
            raise CoreRuntimeInventoryError(f"invalid installed version for '{raw_name}'") from exc
        for file in distribution.files or ():
            try:
                file_owners[Path(distribution.locate_file(file)).resolve()] = (name, version)
            except OSError:
                continue

    included: dict[str, str] = {}
    for item in analysis_items:
        if len(item) < 2:
            continue
        try:
            owner = file_owners.get(Path(item[1]).resolve())
        except (OSError, TypeError):
            continue
        if owner is not None:
            _add_distribution(included, *owner)

    for name in _CORE_DISTRIBUTIONS:
        try:
            distribution = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise CoreRuntimeInventoryError(f"required core distribution '{name}' is not installed") from exc
        _add_distribution(included, canonicalize_name(distribution.metadata["Name"]), distribution.version)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"schema_version": 1, "distributions": dict(sorted(included.items()))}, indent=2) + "\n",
        encoding="utf-8",
    )
    return included


def _add_distribution(distributions: dict[str, str], name: str, version: str) -> None:
    """
    Add a normalized distribution, rejecting conflicting versions.

    Args:
        distributions: Inventory being assembled.
        name: Distribution name.
        version: Installed distribution version.

    Raises:
        CoreRuntimeInventoryError: If two versions claim the same distribution.
    """
    normalized_name = canonicalize_name(name)
    normalized_version = str(Version(version))
    existing = distributions.get(normalized_name)
    if existing is not None and existing != normalized_version:
        raise CoreRuntimeInventoryError(f"multiple versions of '{normalized_name}' are present in the frozen runtime")
    distributions[normalized_name] = normalized_version
