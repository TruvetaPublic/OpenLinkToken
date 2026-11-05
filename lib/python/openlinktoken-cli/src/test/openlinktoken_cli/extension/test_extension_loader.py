# SPDX-License-Identifier: MIT
"""
Unit tests for ExtensionLoader.
"""

import argparse
import sys
from unittest.mock import MagicMock, patch

from openlinktoken_cli.extension.extension_interface import OpenLinkTokenExtension
from openlinktoken_cli.extension.extension_loader import ExtensionLoader

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_subparsers() -> argparse._SubParsersAction:
    """Return a fresh subparsers action for use in tests."""
    parser = argparse.ArgumentParser()
    return parser.add_subparsers(dest="command")


def _make_extension(command_name: str = "test-ext") -> OpenLinkTokenExtension:
    """Build a minimal concrete OpenLinkTokenExtension instance."""

    class _TestExt(OpenLinkTokenExtension):
        @property
        def command_name(self) -> str:
            return command_name

        @property
        def description(self) -> str:
            return "Test extension"

        @property
        def version(self) -> str:
            return "0.1.0"

        def register_subcommand(self, subparsers: argparse._SubParsersAction) -> None:
            subparsers.add_parser(self.command_name, help=self.description)

    return _TestExt()


def _make_entry_point(ext_instance: OpenLinkTokenExtension) -> MagicMock:
    """Wrap an extension instance in a mock importlib EntryPoint."""
    ep = MagicMock()
    ep.name = ext_instance.command_name
    ep.load.return_value = type(ext_instance)
    return ep


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLoadExtensionsEntryPoints:
    """Tests for the Python package (entry-point) discovery track."""

    def test_mock_entry_point_gets_registered(self):
        """An extension discovered via entry points is added to the subparsers."""
        ext = _make_extension("demo-cmd")
        ep = _make_entry_point(ext)
        subparsers = _make_subparsers()

        with patch("importlib.metadata.entry_points", return_value=[ep]):
            ExtensionLoader.load_extensions(subparsers, set())

        assert "demo-cmd" in subparsers.choices

    def test_conflict_with_builtin_is_skipped(self):
        """An extension whose command_name matches a built-in is silently skipped."""
        ext = _make_extension("help")
        ep = _make_entry_point(ext)
        subparsers = _make_subparsers()

        with patch("importlib.metadata.entry_points", return_value=[ep]):
            # Should silently skip without raising.
            ExtensionLoader.load_extensions(subparsers, {"help"})

        assert "help" not in subparsers.choices

    def test_conflict_with_already_registered_extension_is_skipped(self):
        """When two extensions share the same command_name, only the first is kept."""
        ext1 = _make_extension("shared-cmd")
        ext2 = _make_extension("shared-cmd")
        ep1 = _make_entry_point(ext1)
        ep2 = _make_entry_point(ext2)

        # Make load() return distinct instances for the two entry points.
        ep1.load.return_value = type(ext1)
        ep2.load.return_value = type(ext2)

        subparsers = _make_subparsers()

        with patch("importlib.metadata.entry_points", return_value=[ep1, ep2]):
            ExtensionLoader.load_extensions(subparsers, set())

        # Only one parser should be registered.
        assert list(subparsers.choices.keys()).count("shared-cmd") == 1

    def test_import_error_emits_warning_but_does_not_crash(self, caplog):
        """An exception during entry-point load is caught and warns but doesn't raise."""
        ep = MagicMock()
        ep.name = "bad-ext"
        ep.load.side_effect = ImportError("broken module")
        subparsers = _make_subparsers()

        import logging

        with patch("importlib.metadata.entry_points", return_value=[ep]):
            with caplog.at_level(logging.WARNING, logger="openlinktoken_cli.extension.extension_loader"):
                ExtensionLoader.load_extensions(subparsers, set())

        assert "bad-ext" in caplog.text
        assert "bad-ext" not in subparsers.choices

    def test_extensions_sorted_deterministically(self):
        """Extensions are registered in alphabetical order of command_name."""
        names = ["zebra", "alpha", "mango"]
        exts = [_make_extension(n) for n in names]
        eps = [_make_entry_point(e) for e in exts]
        subparsers = _make_subparsers()

        with patch("importlib.metadata.entry_points", return_value=eps):
            ExtensionLoader.load_extensions(subparsers, set())

        registered = list(subparsers.choices.keys())
        assert registered == sorted(names)


class TestLoadExtensionsFrozen:
    """Tests for the frozen-binary (registry) discovery track."""

    def test_frozen_track_loads_extension_from_registry(self):
        """Frozen CLI help registration reads metadata without importing extensions."""
        fake_registry = {
            "frozen-cmd": {
                "version": "1.0.0",
                "command_name": "frozen-cmd",
                "description": "Frozen extension",
            }
        }
        subparsers = _make_subparsers()

        with patch.object(sys, "frozen", True, create=True):
            with patch(
                "openlinktoken_cli.extension.extension_registry.ExtensionRegistry.load",
                return_value=fake_registry,
            ):
                with patch("importlib.import_module") as import_module:
                    ExtensionLoader.load_extensions(subparsers, set())

        assert "frozen-cmd" in subparsers.choices
        import_module.assert_not_called()

    def test_worker_loads_only_the_requested_extension(self, tmp_path, monkeypatch):
        """A frozen worker imports one extension and appends only its private paths."""
        extensions_dir = tmp_path / "extensions"
        source_path = extensions_dir / "demo" / "extension" / "site-packages"
        dependency_path = extensions_dir / "demo" / "dependencies" / "site-packages"
        source_path.mkdir(parents=True)
        dependency_path.mkdir(parents=True)
        (source_path / "worker_demo.py").write_text(
            "from openlinktoken_cli.extension import OpenLinkTokenExtension\n"
            "class WorkerDemo(OpenLinkTokenExtension):\n"
            "    @property\n"
            "    def command_name(self): return 'demo'\n"
            "    @property\n"
            "    def description(self): return 'Demo extension'\n"
            "    @property\n"
            "    def version(self): return '1.0.0'\n"
            "    def register_subcommand(self, subparsers): subparsers.add_parser('demo')\n"
        )
        (source_path / "must_not_import.py").write_text("raise RuntimeError('unselected extension imported')\n")
        registry = {
            "demo": {
                "command_name": "demo",
                "description": "Demo extension",
                "module": "worker_demo",
                "class": "WorkerDemo",
                "source_path": str(source_path),
                "dependency_path": str(dependency_path),
            },
            "other": {
                "command_name": "other",
                "module": "must_not_import",
                "class": "OtherExtension",
                "source_path": str(source_path),
            },
        }
        monkeypatch.setenv("OLT_EXTENSIONS_DIR", str(extensions_dir))
        monkeypatch.setattr(sys, "path", list(sys.path))
        monkeypatch.setattr(sys, "dont_write_bytecode", False)
        monkeypatch.delitem(sys.modules, "worker_demo", raising=False)
        monkeypatch.delitem(sys.modules, "must_not_import", raising=False)
        subparsers = _make_subparsers()

        with patch.object(sys, "frozen", True, create=True):
            with patch(
                "openlinktoken_cli.extension.extension_registry.ExtensionRegistry.load",
                return_value=registry,
            ):
                ExtensionLoader.load_extensions(subparsers, set(), worker_extension_name="demo")

        assert "demo" in subparsers.choices
        assert str(source_path) in sys.path
        assert str(dependency_path) in sys.path
        assert "must_not_import" not in sys.modules

    def test_incompatible_extension_is_disabled_without_importing_code(self):
        """An incompatible registry entry is skipped and marked disabled."""
        subparsers = _make_subparsers()
        registry = {
            "future": {
                "version": "1.0.0",
                "supported_core": ">=99.0.0",
                "module": "future_ext",
                "class": "FutureExtension",
            }
        }

        with patch.object(sys, "frozen", True, create=True):
            with patch(
                "openlinktoken_cli.extension.extension_registry.ExtensionRegistry.load",
                return_value=registry,
            ):
                with patch(
                    "openlinktoken_cli.extension.extension_registry.ExtensionRegistry.update_state"
                ) as update_state:
                    with patch("importlib.import_module") as import_module:
                        ExtensionLoader.load_extensions(subparsers, set())

        assert "future" not in subparsers.choices
        import_module.assert_not_called()
        update_state.assert_called_once()
        assert update_state.call_args.kwargs["disabled"] is True

    def test_malformed_registry_entry_is_skipped(self):
        """A non-object registry entry does not prevent other extensions from loading."""
        subparsers = _make_subparsers()
        registry = {"malformed": None}

        with patch.object(sys, "frozen", True, create=True):
            with patch(
                "openlinktoken_cli.extension.extension_registry.ExtensionRegistry.load",
                return_value=registry,
            ):
                ExtensionLoader.load_extensions(subparsers, set())

        assert not subparsers.choices
