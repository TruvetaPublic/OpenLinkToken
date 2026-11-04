# SPDX-License-Identifier: MIT
"""Tests for the frozen core distribution inventory."""

import importlib.metadata
import json
from pathlib import Path

import packaging
import pytest

from openlinktoken_cli.extension.core_runtime_inventory import (
    CoreRuntimeInventoryError,
    load_core_runtime_inventory,
    write_core_runtime_inventory,
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
