"""
Copyright (c) Truveta. All rights reserved.

Unit tests for ExtensionRegistry.
"""

import json
import os
from unittest.mock import patch

from openlinktoken_cli.extension.extension_registry import ExtensionRegistry

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLoad:
    """Tests for ExtensionRegistry.load()."""

    def test_returns_empty_dict_when_file_absent(self, tmp_path):
        """load() returns {} when registry.json does not exist."""
        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            result = ExtensionRegistry.load()
        assert result == {}

    def test_returns_parsed_contents_when_file_exists(self, tmp_path):
        """load() parses and returns the registry JSON when the file is present."""
        data = {"my-ext": {"version": "1.0.0"}}
        (tmp_path / "registry.json").write_text(json.dumps(data))

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            result = ExtensionRegistry.load()

        assert result == data

    def test_returns_empty_dict_on_invalid_json(self, tmp_path):
        """load() returns {} and does not raise when the file contains invalid JSON."""
        (tmp_path / "registry.json").write_text("NOT VALID JSON{{}")

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            result = ExtensionRegistry.load()

        assert result == {}


class TestAddAndRoundTrip:
    """Tests for ExtensionRegistry.add_extension() + load() round-trip."""

    def test_add_extension_persists_and_reloads(self, tmp_path):
        """add_extension() writes the entry; a subsequent load() returns it."""
        meta = {
            "version": "2.0.0",
            "source_url": "https://example.com/ext.whl",
            "source_path": "/some/path",
            "module": "my_ext.extension",
            "class": "MyExt",
        }

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            ExtensionRegistry.add_extension("my-ext", meta)
            loaded = ExtensionRegistry.load()

        assert loaded["my-ext"] == meta

    def test_add_extension_overwrites_existing_entry(self, tmp_path):
        """add_extension() replaces an existing entry with the same name."""
        meta_v1 = {"version": "1.0.0"}
        meta_v2 = {"version": "2.0.0"}

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            ExtensionRegistry.add_extension("ext", meta_v1)
            ExtensionRegistry.add_extension("ext", meta_v2)
            loaded = ExtensionRegistry.load()

        assert loaded["ext"]["version"] == "2.0.0"


class TestRemoveExtension:
    """Tests for ExtensionRegistry.remove_extension()."""

    def test_remove_existing_entry(self, tmp_path):
        """remove_extension() deletes the named entry from the registry."""
        data = {"ext-a": {"version": "1.0.0"}, "ext-b": {"version": "0.1.0"}}
        (tmp_path / "registry.json").write_text(json.dumps(data))

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            ExtensionRegistry.remove_extension("ext-a")
            loaded = ExtensionRegistry.load()

        assert "ext-a" not in loaded
        assert "ext-b" in loaded

    def test_remove_absent_entry_is_noop(self, tmp_path):
        """remove_extension() does nothing (no error) when the entry is absent."""
        data = {"ext-a": {"version": "1.0.0"}}
        (tmp_path / "registry.json").write_text(json.dumps(data))

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            ExtensionRegistry.remove_extension("does-not-exist")
            loaded = ExtensionRegistry.load()

        assert loaded == data


class TestEnvVarOverride:
    """Tests for OPENTOKEN_EXTENSIONS_DIR environment variable override."""

    def test_env_var_overrides_default_dir(self, tmp_path):
        """get_extensions_dir() returns the path from OPENTOKEN_EXTENSIONS_DIR."""
        custom_dir = tmp_path / "custom_ext_dir"
        custom_dir.mkdir()

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(custom_dir)}):
            result = ExtensionRegistry.get_extensions_dir()

        assert result == custom_dir

    def test_registry_path_uses_custom_dir(self, tmp_path):
        """get_registry_path() is rooted inside OPENTOKEN_EXTENSIONS_DIR."""
        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            path = ExtensionRegistry.get_registry_path()

        assert path == tmp_path / "registry.json"

    def test_data_stored_in_custom_dir(self, tmp_path):
        """Registry data is written inside the overridden directory."""
        meta = {"version": "1.0.0"}

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            ExtensionRegistry.add_extension("x", meta)

        assert (tmp_path / "registry.json").exists()
