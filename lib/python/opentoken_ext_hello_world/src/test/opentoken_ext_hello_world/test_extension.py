"""
Copyright (c) Truveta. All rights reserved.

Unit tests for HelloWorldExtension.
"""

import argparse
from unittest.mock import MagicMock

from opentoken_ext_hello_world.extension import HelloWorldExtension

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
        assert self.ext.description == "OpenToken hello-world reference extension"

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

    def test_greet_sub_subcommand_present(self):
        """The 'greet' sub-subcommand is accessible under 'hello-world'."""
        root = argparse.ArgumentParser()
        subparsers = root.add_subparsers(dest="command")
        ext = HelloWorldExtension()
        ext.register_subcommand(subparsers)

        assert "hello-world" in subparsers.choices
        # Parse a greet invocation — should not raise.
        parsed = root.parse_args(["hello-world", "greet", "--name", "Alice"])
        assert parsed.name == "Alice"


# ---------------------------------------------------------------------------
# Tests: _greet dispatch
# ---------------------------------------------------------------------------


class TestGreetDispatch:
    """Tests for HelloWorldExtension._greet static method."""

    def test_greet_output(self, capsys):
        """_greet prints the expected greeting to stdout."""
        args = MagicMock()
        args.name = "Alice"

        result = HelloWorldExtension._greet(args)

        assert result == 0
        out = capsys.readouterr().out
        assert out.strip() == "Hello, Alice! — from OpenToken hello-world extension"

    def test_greet_different_name(self, capsys):
        """_greet uses the provided name in the output."""
        args = MagicMock()
        args.name = "Bob"

        HelloWorldExtension._greet(args)

        out = capsys.readouterr().out
        assert "Bob" in out
