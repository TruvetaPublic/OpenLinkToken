# SPDX-License-Identifier: MIT
"""Tests for the frozen core distribution inventory."""

import importlib.metadata
import json
from pathlib import Path
from types import SimpleNamespace

import packaging
import pytest

from openlinktoken_cli.extension.core_runtime_inventory import (
    CoreRuntimeInventoryError,
    load_core_runtime_inventory,
    write_core_runtime_inventory,
)


def _fake_packaging_distribution(version, root):
    return SimpleNamespace(
        metadata={"Name": "packaging"},
        version=version,
        files=(Path("packaging/__init__.py"),),
        locate_file=lambda file: root / file,
    )


def test_load_core_runtime_inventory_normalizes_names_and_versions(tmp_path):
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "distributions": {"OpenLinkToken_Cli": "2.2.1", "Packaging": "26.3"},
            }
        ),
        encoding="utf-8",
    )

    inventory = load_core_runtime_inventory(inventory_path)

    assert inventory == {"openlinktoken-cli": "2.2.1", "packaging": "26.3"}


@pytest.mark.parametrize(
    "payload",
    [
        {"schema_version": True, "distributions": {"packaging": "26.3"}},
        {"schema_version": 1, "distributions": {}},
        {"schema_version": 1, "distributions": {"packaging": "not-a-version"}},
    ],
)
def test_load_core_runtime_inventory_rejects_malformed_files(tmp_path, payload):
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CoreRuntimeInventoryError):
        load_core_runtime_inventory(inventory_path)


def test_write_core_runtime_inventory_includes_analyzed_and_required_distributions(tmp_path):
    inventory_path = tmp_path / "data" / "core_runtime_inventory.json"
    inventory = write_core_runtime_inventory(
        [("packaging", str(Path(packaging.__file__).resolve()), "PYMODULE")],
        inventory_path,
    )

    assert inventory["packaging"] == importlib.metadata.version("packaging")
    assert {
        "openlinktoken-cli",
        "openlinktoken",
        "openlinktoken-core-ai",
    }.issubset(inventory)
    assert json.loads(inventory_path.read_text(encoding="utf-8"))["distributions"] == inventory


def test_write_core_runtime_inventory_ignores_vendored_distribution_metadata(tmp_path, monkeypatch):
    installed_distributions = list(importlib.metadata.distributions())
    site_packages = tmp_path / "site-packages"
    vendored_root = site_packages / "setuptools" / "_vendor"
    fake_distributions = [
        _fake_packaging_distribution("26.3", site_packages),
        _fake_packaging_distribution("26.0", vendored_root),
    ]
    monkeypatch.setattr(
        importlib.metadata,
        "distributions",
        lambda: [*installed_distributions, *fake_distributions],
    )
    inventory_path = tmp_path / "data" / "core_runtime_inventory.json"

    inventory = write_core_runtime_inventory(
        [
            ("packaging", str(site_packages / "packaging" / "__init__.py"), "PYMODULE"),
            (
                "setuptools._vendor.packaging",
                str(vendored_root / "packaging" / "__init__.py"),
                "PYMODULE",
            ),
        ],
        inventory_path,
    )

    assert inventory["packaging"] == "26.3"


def test_write_core_runtime_inventory_rejects_conflicting_top_level_versions(tmp_path, monkeypatch):
    installed_distributions = list(importlib.metadata.distributions())
    first_root = tmp_path / "first" / "site-packages"
    second_root = tmp_path / "second" / "site-packages"
    fake_distributions = [
        _fake_packaging_distribution("26.3", first_root),
        _fake_packaging_distribution("26.0", second_root),
    ]
    monkeypatch.setattr(
        importlib.metadata,
        "distributions",
        lambda: [*installed_distributions, *fake_distributions],
    )

    with pytest.raises(CoreRuntimeInventoryError, match="multiple versions of 'packaging'"):
        write_core_runtime_inventory(
            [
                ("packaging", str(first_root / "packaging" / "__init__.py"), "PYMODULE"),
                ("packaging", str(second_root / "packaging" / "__init__.py"), "PYMODULE"),
            ],
            tmp_path / "data" / "core_runtime_inventory.json",
        )
