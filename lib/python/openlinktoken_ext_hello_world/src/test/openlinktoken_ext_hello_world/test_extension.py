# SPDX-License-Identifier: MIT
"""
Unit tests for HelloWorldExtension.
"""

import argparse
from unittest.mock import MagicMock

from openlinktoken_ext_hello_world.extension import HelloWorldExtension

# ---------------------------------------------------------------------------
# Tests: properties
# ---------------------------------------------------------------------------


class TestHelloWorldProperties:
    """Tests for HelloWorldExtension abstract-property implementations."""

    def setup_method(self):
        self.ext = HelloWorldExtension()

    def test_command_name(self):
        assert self.ext.command_name == "hello-world"

    def test_description(self):
        assert self.ext.description == "OpenLinkToken hello-world reference extension"

    def test_version(self):
        assert self.ext.version == "1.0.0"


# ---------------------------------------------------------------------------
# Tests: register_subcommand
# ---------------------------------------------------------------------------


class TestRegisterSubcommand:
    """Tests that register_subcommand adds the expected parser."""

    def test_adds_hello_world_parser(self):
        """register_subcommand registers a 'hello-world' choice in the subparsers."""
        root = argparse.ArgumentParser()
        subparsers = root.add_subparsers(dest="command")
        ext = HelloWorldExtension()

        ext.register_subcommand(subparsers)

        assert "hello-world" in subparsers.choices

    def test_hello_sub_subcommand_present(self):
        """The 'hello' sub-subcommand is accessible under 'hello-world'."""
        root = argparse.ArgumentParser()
        subparsers = root.add_subparsers(dest="command")
        ext = HelloWorldExtension()
        ext.register_subcommand(subparsers)

        assert "hello-world" in subparsers.choices
        # Parse a hello invocation — should not raise.
        parsed = root.parse_args(["hello-world", "hello", "--name", "Alice"])
        assert parsed.name == "Alice"

    def test_bye_sub_subcommand_present(self):
        """The 'bye' sub-subcommand is accessible under 'hello-world'."""
        root = argparse.ArgumentParser()
        subparsers = root.add_subparsers(dest="command")
        ext = HelloWorldExtension()
        ext.register_subcommand(subparsers)

        assert "hello-world" in subparsers.choices
        # Parse a bye invocation — should not raise.
        parsed = root.parse_args(["hello-world", "bye", "--name", "Alice"])
        assert parsed.name == "Alice"


# ---------------------------------------------------------------------------
# Tests: _hello dispatch
# ---------------------------------------------------------------------------


class TestHelloDispatch:
    """Tests for HelloWorldExtension._hello static method."""

    def test_hello_output(self, capsys):
        """_hello prints the expected greeting to stdout."""
        args = MagicMock()
        args.name = "Alice"

        result = HelloWorldExtension._hello(args)

        assert result == 0
        out = capsys.readouterr().out
        assert out.strip() == "Hello, Alice"

    def test_hello_different_name(self, capsys):
        """_hello uses the provided name in the output."""
        args = MagicMock()
        args.name = "Bob"

        HelloWorldExtension._hello(args)

        out = capsys.readouterr().out
        assert "Bob" in out


# ---------------------------------------------------------------------------
# Tests: _bye dispatch
# ---------------------------------------------------------------------------


class TestByeDispatch:
    """Tests for HelloWorldExtension._bye static method."""

    def test_bye_output(self, capsys):
        """_bye prints the expected farewell to stdout."""
        args = MagicMock()
        args.name = "Alice"

        result = HelloWorldExtension._bye(args)

        assert result == 0
        out = capsys.readouterr().out
        assert out.strip() == "Bye, Alice"

    def test_bye_different_name(self, capsys):
        """_bye uses the provided name in the output."""
        args = MagicMock()
        args.name = "Bob"

        HelloWorldExtension._bye(args)

        out = capsys.readouterr().out
        assert "Bob" in out
