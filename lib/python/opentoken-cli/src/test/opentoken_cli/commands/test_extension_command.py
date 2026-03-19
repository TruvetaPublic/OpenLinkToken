"""
Copyright (c) Truveta. All rights reserved.

Unit tests for ExtensionCommand.
"""

import json
import logging
import os
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from opentoken_cli.commands.extension_command import _SECURITY_WARNING, ExtensionCommand

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_args(**kwargs) -> MagicMock:
    args = MagicMock()
    for k, v in kwargs.items():
        setattr(args, k, v)
    return args


def _make_wheel(dest: Path, name: str = "hello-world", version: str = "1.0.0") -> Path:
    """
    Write a minimal valid wheel (.whl) to *dest* and return the path.

    The wheel contains METADATA and entry_points.txt in a dist-info directory.
    """
    dist_info = f"opentoken_{name.replace('-', '_')}-{version}.dist-info"
    metadata_content = f"Metadata-Version: 2.1\nName: opentoken-{name}\nVersion: {version}\n"
    ep_content = f"[opentoken.extensions]\n{name} = opentoken_{name.replace('-', '_')}.extension:FakeExtension\n"

    whl_path = dest / f"opentoken_{name.replace('-', '_')}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(whl_path, "w") as zf:
        zf.writestr(f"{dist_info}/METADATA", metadata_content)
        zf.writestr(f"{dist_info}/entry_points.txt", ep_content)
        zf.writestr(f"opentoken_{name.replace('-', '_')}/__init__.py", "")
    return whl_path


# ---------------------------------------------------------------------------
# Tests: list
# ---------------------------------------------------------------------------


class TestExtensionList:
    """Tests for ``extension list``."""

    def test_list_empty_registry(self, tmp_path, capsys):
        """list prints a friendly message when no extensions are installed."""
        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("importlib.metadata.entry_points", return_value=[]):
                result = ExtensionCommand._list(_make_args())

        assert result == 0
        assert "No extensions installed" in capsys.readouterr().out

    def test_list_populated_registry(self, tmp_path, capsys):
        """list prints a table with name, version, command, and source_url columns."""
        data = {
            "my-ext": {
                "version": "1.2.3",
                "source_url": "https://example.com/my_ext.whl",
                "command_name": "my-ext",
            }
        }
        (tmp_path / "registry.json").write_text(json.dumps(data))

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            result = ExtensionCommand._list(_make_args())

        out = capsys.readouterr().out
        assert result == 0
        assert "my-ext" in out
        assert "1.2.3" in out
        assert "https://example.com/my_ext.whl" in out


# ---------------------------------------------------------------------------
# Tests: uninstall
# ---------------------------------------------------------------------------


class TestExtensionUninstall:
    """Tests for ``extension uninstall``."""

    def test_uninstall_removes_directory_and_registry_entry(self, tmp_path):
        """uninstall removes the extension's directory and its registry entry (frozen mode)."""
        data = {"bye-ext": {"version": "1.0.0", "source_url": "", "dist_name": "opentoken-bye-ext"}}
        (tmp_path / "registry.json").write_text(json.dumps(data))
        ext_dir = tmp_path / "bye-ext"
        ext_dir.mkdir()
        (ext_dir / "dummy.py").write_text("")

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("sys.frozen", True, create=True):
                result = ExtensionCommand._uninstall(_make_args(name="bye-ext"))

        assert result == 0
        assert not ext_dir.exists()
        registry = json.loads((tmp_path / "registry.json").read_text())
        assert "bye-ext" not in registry

    def test_uninstall_calls_pip_in_non_frozen_mode(self, tmp_path):
        """uninstall calls pip uninstall for registry entries in a normal Python environment."""
        data = {"my-ext": {"version": "1.0.0", "source_url": "", "dist_name": "opentoken-my-ext"}}
        (tmp_path / "registry.json").write_text(json.dumps(data))

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("subprocess.run", return_value=mock_result) as mock_pip:
                result = ExtensionCommand._uninstall(_make_args(name="my-ext"))

        assert result == 0
        mock_pip.assert_called_once()
        call_args = mock_pip.call_args[0][0]
        assert "uninstall" in call_args
        assert "opentoken-my-ext" in call_args

    def test_uninstall_pip_installed_extension_shows_guidance(self, tmp_path, capsys):
        """uninstall prints pip guidance and returns 1 for entry-point extensions."""
        mock_ep = MagicMock()
        mock_ep.name = "pip-ext"

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
                result = ExtensionCommand._uninstall(_make_args(name="pip-ext"))

        assert result == 1
        output = capsys.readouterr()
        assert "pip" in output.err
        assert "pip-ext" in output.err

    def test_uninstall_unknown_extension_returns_error(self, tmp_path, capsys):
        """uninstall returns 1 with an error message for unknown extension names."""
        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("importlib.metadata.entry_points", return_value=[]):
                result = ExtensionCommand._uninstall(_make_args(name="ghost-ext"))

        assert result == 1
        assert "not installed" in capsys.readouterr().err

    def test_uninstall_invalid_dist_name_returns_error(self, tmp_path, capsys):
        """_uninstall returns 1 and does not call pip when the registry dist_name is invalid."""
        data = {"evil-ext": {"version": "1.0.0", "source_url": "", "dist_name": "-r evil.txt"}}
        (tmp_path / "registry.json").write_text(json.dumps(data))

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("subprocess.run") as mock_pip:
                result = ExtensionCommand._uninstall(_make_args(name="evil-ext"))

        assert result == 1
        mock_pip.assert_not_called()
        err = capsys.readouterr().err
        assert "invalid" in err.lower() or "valid" in err.lower()


# ---------------------------------------------------------------------------
# Tests: install security warning
# ---------------------------------------------------------------------------


class TestExtensionInstall:
    """Tests for ``extension install``."""

    def test_install_prints_security_warning(self, tmp_path, capsys):
        """install always prints the security warning before any other action."""
        args = _make_args(url="file:///nonexistent.whl", yes=True)
        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            # The file doesn't exist — we just want to confirm the warning is printed.
            ExtensionCommand._install(args)

        out = capsys.readouterr().out
        assert _SECURITY_WARNING in out

    def test_install_yes_flag_skips_prompt(self, tmp_path, capsys):
        """--yes skips the interactive confirmation prompt."""
        args = _make_args(url="file:///nonexistent.whl", yes=True)
        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("builtins.input") as mock_input:
                ExtensionCommand._install(args)
                mock_input.assert_not_called()

    def test_install_prompts_without_yes(self, tmp_path, capsys):
        """Without --yes, the user is prompted when stdin is a tty."""
        args = _make_args(url="file:///nonexistent.whl", yes=False)
        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.isatty.return_value = True
                with patch("builtins.input", return_value="n"):
                    result = ExtensionCommand._install(args)

        assert result == 0  # cancelled — clean exit
        out = capsys.readouterr().out
        assert "cancelled" in out.lower()

    def test_install_file_url(self, tmp_path, capsys):
        """install file:// downloads from a local path and registers the extension."""
        whl = _make_wheel(tmp_path)
        args = _make_args(url=f"file://{whl}", yes=True)

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("subprocess.run", return_value=mock_result):
                with patch(
                    "opentoken_cli.commands.extension_command._resolve_extension_command_name",
                    return_value="hello-world",
                ):
                    result = ExtensionCommand._install(args)

        assert result == 0
        out = capsys.readouterr().out
        assert "installed successfully" in out

        registry = json.loads((tmp_path / "registry.json").read_text())
        assert "hello-world" in registry
        assert registry["hello-world"]["version"] == "1.0.0"

    def test_install_non_interactive_without_yes_fails(self, tmp_path, capsys):
        """Without --yes and in a non-TTY context, install must fail with a clear error."""
        args = _make_args(url="file:///nonexistent.whl", yes=False)
        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.isatty.return_value = False
                result = ExtensionCommand._install(args)
                mock_stdin.isatty.assert_called_once()

        assert result == 1
        err = capsys.readouterr().err
        assert "--yes" in err

    def test_install_rejects_non_https_url(self, tmp_path, capsys):
        """install must reject URLs with schemes other than https:// or file://."""
        args = _make_args(url="http://example.com/ext.whl", yes=True)
        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            result = ExtensionCommand._install(args)

        assert result == 1
        err = capsys.readouterr().err
        assert "Unsupported URL scheme" in err

    def test_install_pip_uses_upgrade_without_no_deps(self, tmp_path, capsys):
        """install passes --upgrade to pip but NOT --no-deps so transitive dependencies are resolved normally."""
        whl = _make_wheel(tmp_path)
        args = _make_args(url=f"file://{whl}", yes=True)

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("subprocess.run", return_value=mock_result) as mock_pip:
                ExtensionCommand._install(args)

        # call_args_list[0] is the pip install call; the second call (if present) is the rollback.
        install_call_args = mock_pip.call_args_list[0][0][0]
        assert "--upgrade" in install_call_args
        assert "--no-deps" not in install_call_args

    def test_install_rolls_back_pip_on_none_command_name(self, tmp_path):
        """install rolls back pip when _resolve_extension_command_name returns None."""
        whl = _make_wheel(tmp_path)
        args = _make_args(url=f"file://{whl}", yes=True)

        pip_install_result = MagicMock()
        pip_install_result.returncode = 0

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("subprocess.run", return_value=pip_install_result) as mock_pip:
                with patch(
                    "opentoken_cli.commands.extension_command._resolve_extension_command_name",
                    return_value=None,
                ):
                    result = ExtensionCommand._install(args)

        assert result != 0
        # Expect two calls: pip install, then pip uninstall rollback.
        assert mock_pip.call_count == 2
        uninstall_call_args = mock_pip.call_args_list[1][0][0]
        assert "uninstall" in uninstall_call_args
        assert "opentoken-hello-world" in uninstall_call_args

    def test_frozen_install_cleans_up_src_dir_on_extract_error(self, tmp_path):
        """install removes src_dir when _safe_extract_wheel raises ValueError."""
        whl = _make_wheel(tmp_path)
        args = _make_args(url=f"file://{whl}", yes=True)

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("sys.frozen", True, create=True):
                with patch.object(
                    ExtensionCommand,
                    "_safe_extract_wheel",
                    side_effect=ValueError("bad path"),
                ):
                    result = ExtensionCommand._install(args)

        assert result != 0
        # src_dir must not be left on disk after the ValueError
        src_dir = tmp_path / "hello-world" / "src"
        assert not src_dir.exists()

    def test_frozen_install_cleans_up_src_dir_on_none_command_name(self, tmp_path):
        """install removes src_dir when _resolve_extension_command_name returns None (frozen mode)."""
        whl = _make_wheel(tmp_path)
        args = _make_args(url=f"file://{whl}", yes=True)

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("sys.frozen", True, create=True):
                with patch.object(ExtensionCommand, "_safe_extract_wheel"):
                    with patch(
                        "opentoken_cli.commands.extension_command._resolve_extension_command_name",
                        return_value=None,
                    ):
                        result = ExtensionCommand._install(args)

        assert result != 0
        src_dir = tmp_path / "hello-world" / "src"
        assert not src_dir.exists()

    def test_frozen_install_cleans_up_src_dir_on_command_name_mismatch(self, tmp_path):
        """install removes src_dir when _resolve_extension_command_name returns a mismatched name (frozen mode)."""
        whl = _make_wheel(tmp_path)
        args = _make_args(url=f"file://{whl}", yes=True)

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("sys.frozen", True, create=True):
                with patch.object(ExtensionCommand, "_safe_extract_wheel"):
                    with patch(
                        "opentoken_cli.commands.extension_command._resolve_extension_command_name",
                        return_value="wrong-name",
                    ):
                        result = ExtensionCommand._install(args)

        assert result != 0
        src_dir = tmp_path / "hello-world" / "src"
        assert not src_dir.exists()

    def test_install_rolls_back_pip_on_command_name_mismatch(self, tmp_path):
        """install rolls back pip when _resolve_extension_command_name returns a name that doesn't match."""
        whl = _make_wheel(tmp_path)
        args = _make_args(url=f"file://{whl}", yes=True)

        pip_install_result = MagicMock()
        pip_install_result.returncode = 0

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("subprocess.run", return_value=pip_install_result) as mock_pip:
                with patch(
                    "opentoken_cli.commands.extension_command._resolve_extension_command_name",
                    return_value="wrong-name",
                ):
                    result = ExtensionCommand._install(args)

        assert result != 0
        # Expect two calls: pip install, then pip uninstall rollback.
        assert mock_pip.call_count == 2
        uninstall_call_args = mock_pip.call_args_list[1][0][0]
        assert "uninstall" in uninstall_call_args
        assert "opentoken-hello-world" in uninstall_call_args

    def test_nonfrozen_install_invalid_ext_name_returns_error(self, tmp_path, capsys):
        """_install_wheel returns 1 without calling pip when ext_name is not a valid dist name (non-frozen)."""
        whl = _make_wheel(tmp_path)

        with patch.object(
            ExtensionCommand,
            "_extract_entry_point",
            return_value=("-r evil.txt", "some_module", "SomeClass", "1.0.0", "test"),
        ):
            with patch("subprocess.run") as mock_pip:
                result = ExtensionCommand._install_wheel(whl, source_url="file:///test.whl")

        assert result == 1
        mock_pip.assert_not_called()
        err = capsys.readouterr().err
        assert "valid" in err.lower() or "invalid" in err.lower()


# ---------------------------------------------------------------------------
# Tests: _check_frozen_deps
# ---------------------------------------------------------------------------


class TestCheckFrozenDeps:
    """Unit tests for ExtensionCommand._check_frozen_deps."""

    def _make_wheel_with_metadata(self, dest: Path, metadata_content: str) -> zipfile.ZipFile:
        whl_path = dest / "test-1.0.0-py3-none-any.whl"
        with zipfile.ZipFile(whl_path, "w") as zf:
            zf.writestr("test-1.0.0.dist-info/METADATA", metadata_content)
        return zipfile.ZipFile(whl_path, "r")

    def test_no_metadata_returns_none(self, tmp_path):
        whl_path = tmp_path / "test-1.0.0-py3-none-any.whl"
        with zipfile.ZipFile(whl_path, "w") as zf:
            zf.writestr("test/__init__.py", "")
        with zipfile.ZipFile(whl_path, "r") as zf:
            assert ExtensionCommand._check_frozen_deps(zf) is None

    def test_all_bundled_deps_returns_none(self, tmp_path):
        metadata = (
            "Metadata-Version: 2.1\n"
            "Name: my-extension\n"
            "Requires-Dist: opentoken\n"
            "Requires-Dist: pandas\n"
            "Requires-Dist: pyarrow\n"
        )
        with self._make_wheel_with_metadata(tmp_path, metadata) as zf:
            assert ExtensionCommand._check_frozen_deps(zf) is None

    def test_version_specifier_with_parentheses_is_parsed_correctly(self, tmp_path):
        """Wheel METADATA may use 'pkg (>=1.2)' format; the name must be extracted cleanly."""
        metadata = (
            "Metadata-Version: 2.1\n"
            "Name: my-extension\n"
            "Requires-Dist: opentoken (>=2.0)\n"
            "Requires-Dist: pandas (>=1.3,<3.0)\n"
            "Requires-Dist: requests (>=2.28)\n"
        )
        with self._make_wheel_with_metadata(tmp_path, metadata) as zf:
            result = ExtensionCommand._check_frozen_deps(zf)
        assert result == "requests"

    def test_version_specifier_without_parentheses_is_parsed_correctly(self, tmp_path):
        metadata = (
            "Metadata-Version: 2.1\nName: my-extension\nRequires-Dist: opentoken>=2.0\nRequires-Dist: requests>=2.28\n"
        )
        with self._make_wheel_with_metadata(tmp_path, metadata) as zf:
            result = ExtensionCommand._check_frozen_deps(zf)
        assert result == "requests"

    def test_underscore_normalized_to_dash(self, tmp_path):
        """Package names with underscores should be treated the same as dashes."""
        metadata = "Metadata-Version: 2.1\nName: my-extension\nRequires-Dist: opentoken_cli\n"
        with self._make_wheel_with_metadata(tmp_path, metadata) as zf:
            result = ExtensionCommand._check_frozen_deps(zf)
        assert result is None

    def test_multiple_external_deps_reported(self, tmp_path):
        metadata = (
            "Metadata-Version: 2.1\n"
            "Name: my-extension\n"
            "Requires-Dist: opentoken\n"
            "Requires-Dist: requests (>=2.28)\n"
            "Requires-Dist: httpx\n"
        )
        with self._make_wheel_with_metadata(tmp_path, metadata) as zf:
            result = ExtensionCommand._check_frozen_deps(zf)
        assert result is not None
        assert "requests" in result
        assert "httpx" in result

    def test_warns_on_multiple_dist_info_directories(self, tmp_path, caplog):
        """_check_frozen_deps emits a warning when the wheel has multiple dist-info directories."""
        whl_path = tmp_path / "multi-1.0.0-py3-none-any.whl"
        with zipfile.ZipFile(whl_path, "w") as zf:
            zf.writestr("foo-1.0.dist-info/METADATA", "Metadata-Version: 2.1\nName: foo\nVersion: 1.0\n")
            zf.writestr("bar-2.0.dist-info/METADATA", "Metadata-Version: 2.1\nName: bar\nVersion: 2.0\n")

        with zipfile.ZipFile(whl_path, "r") as zf:
            with caplog.at_level(logging.WARNING, logger="opentoken_cli.commands.extension_command"):
                result = ExtensionCommand._check_frozen_deps(zf)

        assert any("multiple dist-info" in msg.lower() for msg in caplog.messages)
        assert result is None  # Neither METADATA entry has Requires-Dist lines

    def test_frozen_deps_skips_extras_conditional_dep(self, tmp_path):
        """_check_frozen_deps returns None when the only Requires-Dist entry is extras-conditional."""
        metadata = 'Metadata-Version: 2.1\nName: my-extension\nRequires-Dist: requests; extra == "dev"\n'
        with self._make_wheel_with_metadata(tmp_path, metadata) as zf:
            result = ExtensionCommand._check_frozen_deps(zf)
        assert result is None


# ---------------------------------------------------------------------------
# Tests: _extract_entry_point
# ---------------------------------------------------------------------------


class TestExtractEntryPoint:
    """Unit tests for ExtensionCommand._extract_entry_point."""

    def test_warns_on_multiple_entry_points(self, tmp_path, caplog):
        """_extract_entry_point warns and picks the first of multiple opentoken.extensions entries."""
        ep_content = "[opentoken.extensions]\ncmd-one = mymodule:MyClass\ncmd-two = mymodule:OtherClass\n"
        metadata_content = "Metadata-Version: 2.1\nName: mymodule\nVersion: 1.0.0\n"
        whl_path = tmp_path / "mymodule-1.0.0-py3-none-any.whl"
        with zipfile.ZipFile(whl_path, "w") as zf:
            zf.writestr("mymodule-1.0.0.dist-info/entry_points.txt", ep_content)
            zf.writestr("mymodule-1.0.0.dist-info/METADATA", metadata_content)

        with zipfile.ZipFile(whl_path, "r") as zf:
            with caplog.at_level(logging.WARNING, logger="opentoken_cli.commands.extension_command"):
                result = ExtensionCommand._extract_entry_point(zf)

        assert any("opentoken.extensions" in msg for msg in caplog.messages)
        assert result is not None
        assert result[0] == "cmd-one"
