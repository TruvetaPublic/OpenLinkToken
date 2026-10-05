# SPDX-License-Identifier: MIT
"""Tests for the data-only extension manifest contract."""

import pytest
from packaging.specifiers import SpecifierSet

from openlinktoken_cli.extension.extension_manifest import (
    ManifestValidationError,
    parse_manifest,
)


def _bootstrap_manifest(**extension_overrides):
    extension = {
        "name": "demo",
        "version": "1.0.0",
        "artifact_url": "https://example.com/demo-1.0.0.whl",
        "update_manifest_url": "https://example.com/demo.json",
        "sha256": "a" * 64,
    }
    extension.update(extension_overrides)
    return {
        "schema_version": 1,
        "extension": extension,
        "core": {"min_version": "2.1.0", "max_version": "<3.0.0"},
    }


def test_parse_bootstrap_manifest_returns_normalized_artifact():
    manifest = parse_manifest(_bootstrap_manifest(), expected_name="demo")

    assert manifest.name == "demo"
    assert manifest.version == "1.0.0"
    assert manifest.core_specifier == str(SpecifierSet(">=2.1.0,<3.0.0"))
    assert manifest.artifacts[0].sha256 == "a" * 64


def test_parse_update_manifest_rejects_signature_only_artifact():
    manifest = {
        "schema_version": 1,
        "extension": "demo",
        "latest_version": "1.1.0",
        "requires_core": ">=2.1.0,<3.0.0",
        "artifacts": [
            {
                "url": "https://example.com/demo-1.1.0.whl",
                "signature": {"algorithm": "ed25519", "value": "sig"},
            }
        ],
    }

    with pytest.raises(ManifestValidationError, match="sha256"):
        parse_manifest(manifest, expected_name="demo")


def test_parse_manifest_rejects_non_https_url_without_local_install():
    with pytest.raises(ManifestValidationError, match="HTTPS"):
        parse_manifest(
            _bootstrap_manifest(artifact_url="http://example.com/demo.whl"),
            expected_name="demo",
        )


def test_parse_manifest_accepts_file_url_only_for_explicit_local_install():
    manifest = parse_manifest(
        _bootstrap_manifest(artifact_url="file:///tmp/demo.whl", sha256=None),
        expected_name="demo",
        allow_local=True,
    )

    assert manifest.artifacts[0].url.startswith("file://")


def test_parse_manifest_rejects_unknown_signature_fields():
    with pytest.raises(ManifestValidationError, match="signature"):
        parse_manifest(
            _bootstrap_manifest(
                signature={
                    "algorithm": "ed25519",
                    "value": "sig",
                    "public_key": "not-supported",
                }
            ),
            expected_name="demo",
        )
