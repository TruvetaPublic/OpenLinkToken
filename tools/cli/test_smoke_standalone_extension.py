#!/usr/bin/env python3
"""Tests for the frozen standalone extension smoke helper."""

import hashlib
import json
import zipfile
from pathlib import Path

from openlinktoken_cli.extension.extension_manifest import parse_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_HELPER = REPO_ROOT / "tools" / "cli" / "smoke_standalone_extension.py"


def test_smoke_manifest_builds_a_local_locked_hello_world_bundle(tmp_path, monkeypatch):
    """The smoke helper should produce a valid local manifest and locked wheel bundle."""
    assert SMOKE_HELPER.is_file(), "The frozen extension smoke helper must exist."
    monkeypatch.syspath_prepend(str(SMOKE_HELPER.parent))
    import smoke_standalone_extension as smoke_helper

    monkeypatch.setattr(smoke_helper, "current_extension_target", lambda: ("linux-x64", "cp311"))

    wheel_path = tmp_path / "openlinktoken_ext_hello_world-1.0.0-py3-none-any.whl"
    wheel_bytes = b"hello world wheel"
    wheel_path.write_bytes(wheel_bytes)
    output_dir = tmp_path / "artifacts"

    manifest_path = smoke_helper.create_smoke_manifest(wheel_path, output_dir)

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = parse_manifest(manifest_data, expected_name="hello-world", allow_local=True)
    assert manifest.version == "1.0.0"
    assert manifest.command_name == "hello-world"
    assert len(manifest.bundles) == 1

    bundle_path = output_dir / "hello-world-1.0.0.zip"
    bundle = manifest.bundles[0]
    assert bundle.url == bundle_path.as_uri()
    assert bundle.sha256 == hashlib.sha256(bundle_path.read_bytes()).hexdigest()

    with zipfile.ZipFile(bundle_path) as archive:
        bundle_manifest = json.loads(archive.read("bundle-manifest.json"))
        assert archive.read(wheel_path.name) == wheel_bytes

    assert bundle_manifest["schema_version"] == 1
    assert bundle_manifest["extension"] == {"name": "hello-world", "version": "1.0.0"}
    assert bundle_manifest["target"] == bundle.target
    assert bundle_manifest["python_abi"] == bundle.python_abi
    assert bundle_manifest["wheels"] == [
        {
            "filename": wheel_path.name,
            "name": "openlinktoken-ext-hello-world",
            "version": "1.0.0",
            "tags": ["py3-none-any"],
            "sha256": hashlib.sha256(wheel_bytes).hexdigest(),
        }
    ]
