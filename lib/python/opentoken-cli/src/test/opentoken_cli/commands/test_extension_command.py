"""
Copyright (c) Truveta. All rights reserved.

Unit tests for ExtensionCommand.
"""

import json
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

    def test_install_pip_uses_upgrade_no_deps(self, tmp_path, capsys):
        """install passes --upgrade --no-deps to pip so the package is updated without re-downloading unchanged deps."""
        whl = _make_wheel(tmp_path)
        args = _make_args(url=f"file://{whl}", yes=True)

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.dict(os.environ, {"OPENTOKEN_EXTENSIONS_DIR": str(tmp_path)}):
            with patch("subprocess.run", return_value=mock_result) as mock_pip:
                ExtensionCommand._install(args)

        call_args = mock_pip.call_args[0][0]
        assert "--upgrade" in call_args
        assert "--no-deps" in call_args
