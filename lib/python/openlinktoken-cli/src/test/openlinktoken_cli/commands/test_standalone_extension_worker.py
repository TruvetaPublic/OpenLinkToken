# SPDX-License-Identifier: MIT
"""Tests for standalone extension worker dispatch."""

import subprocess
import sys
from unittest.mock import patch

from openlinktoken_cli.commands.open_link_token_command import OpenLinkTokenCommand
from openlinktoken_cli.extension.extension_loader import (
    METADATA_ARGUMENT,
    METADATA_MARKER,
    WORKER_ARGUMENT,
    ExtensionLoader,
)


def test_parent_routes_extension_commands_to_a_fresh_worker():
    with patch.object(sys, "frozen", True, create=True):
        with patch.object(
            ExtensionLoader,
            "find_extension_command",
            return_value=("demo", ["demo", "--help"]),
        ):
            with patch.object(ExtensionLoader, "run_worker", return_value=17) as run_worker:
                assert OpenLinkTokenCommand.main(["demo"]) == 17

    run_worker.assert_called_once_with("demo", ["demo", "--help"])


def test_command_discovery_reads_registry_without_importing_extension_code():
    registry = {"demo": {"command_name": "demo", "description": "Demo extension"}}

    with patch(
        "openlinktoken_cli.extension.extension_registry.ExtensionRegistry.load",
        return_value=registry,
    ):
        with patch("importlib.import_module") as import_module:
            assert ExtensionLoader.find_extension_command(["demo", "--option"]) == (
                "demo",
                ["demo", "--option"],
            )
            assert ExtensionLoader.find_extension_command(["help", "demo"]) == (
                "demo",
                ["demo", "--help"],
            )

    import_module.assert_not_called()


def test_worker_command_preserves_child_exit_status():
    completed = subprocess.CompletedProcess(args=[], returncode=17)

    with patch("openlinktoken_cli.extension.extension_loader.subprocess.run", return_value=completed) as run:
        assert ExtensionLoader.run_worker("demo", ["demo", "--help"]) == 17

    assert run.call_args.args[0] == [
        sys.executable,
        WORKER_ARGUMENT,
        "demo",
        "--",
        "demo",
        "--help",
    ]
    assert run.call_args.kwargs["check"] is False


def test_metadata_worker_returns_only_command_help_metadata(capsys):
    class Metadata:
        command_name = "demo"
        description = "Demo extension"

    with patch.object(sys, "frozen", True, create=True):
        with patch.object(ExtensionLoader, "load_worker_extension", return_value=Metadata()):
            assert OpenLinkTokenCommand._handle_internal_worker_args([METADATA_ARGUMENT, "demo"]) == 0

    assert capsys.readouterr().out.strip() == (
        f'{METADATA_MARKER}{{"command_name": "demo", "description": "Demo extension"}}'
    )


def test_worker_rejects_mismatched_command_before_loading_extension(capsys):
    with patch.object(sys, "frozen", True, create=True):
        with patch.object(ExtensionLoader, "find_extension_command", return_value=("other", ["other"])):
            assert OpenLinkTokenCommand._handle_internal_worker_args([WORKER_ARGUMENT, "demo", "--", "other"]) == 2

    assert "do not select extension 'demo'" in capsys.readouterr().err
