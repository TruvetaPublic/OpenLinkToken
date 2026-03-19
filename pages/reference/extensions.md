---
layout: default
---

# Extension Author Reference

Complete reference for building OpenToken CLI extensions. This page documents the `OpenTokenExtension` ABC contract, entry-point declaration, extension lifecycle, conflict rules, security and trust model, and binary compatibility requirements.

---

## Overview

OpenToken extensions are self-contained Python packages that add top-level subcommands to the `opentoken` CLI. Each extension registers exactly one top-level subcommand (for example, `opentoken hello-world`) by implementing the `OpenTokenExtension` abstract base class and declaring an entry point in the `opentoken.extensions` group.

Extensions are installed to a user-local directory and loaded at CLI startup, so they appear alongside built-in commands in `opentoken --help`.

---

## `OpenTokenExtension` Interface

All extensions must implement the following abstract base class:

```python
from abc import ABC, abstractmethod


class OpenTokenExtension(ABC):
    """Abstract base class for all OpenToken CLI extensions.

    Implement this class and declare it as an entry point in the
    ``opentoken.extensions`` group to register a top-level subcommand.
    """

    @property
    @abstractmethod
    def command_name(self) -> str:
        """The top-level subcommand name.

        Must be unique across all installed extensions and must not
        conflict with any built-in OpenToken subcommand.

        Example: ``"hello-world"``
        """

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description shown in ``opentoken --help``."""

    @property
    @abstractmethod
    def version(self) -> str:
        """SemVer version string for this extension.

        Example: ``"1.0.0"``
        """

    @abstractmethod
    def register_subcommand(self, subparsers) -> None:
        """Add this extension's argparse parser to the CLI.

        Parameters
        ----------
        subparsers:
            The ``_SubParsersAction`` returned by
            ``ArgumentParser.add_subparsers()``.

        Implementation requirements
        ---------------------------
        * Call ``subparsers.add_parser(self.command_name, ...)`` to create
          your parser.
        * Call ``set_defaults(func=<handler>)`` on every leaf parser so the
          CLI dispatcher can invoke the correct handler.
        * Leaf parsers that omit ``set_defaults(func=...)`` will raise an
          ``AttributeError`` at dispatch time.
        """
```

### Example Implementation

```python
# opentoken_ext_hello_world/extension.py
from opentoken_cli.extension import OpenTokenExtension


class HelloWorldExtension(OpenTokenExtension):
    @property
    def command_name(self) -> str:
        return "hello-world"

    @property
    def description(self) -> str:
        return "Greet the world from an OpenToken extension"

    @property
    def version(self) -> str:
        return "1.0.0"

    def register_subcommand(self, subparsers) -> None:
        parser = subparsers.add_parser(
            self.command_name,
            help=self.description,
        )
        parser.set_defaults(func=lambda args: (parser.print_help(), 0)[1])

        sub = parser.add_subparsers()

        hello = sub.add_parser("hello", help="Greet a named person")
        hello.add_argument("--name", required=True, help="Name to greet")
        hello.set_defaults(func=self._run_hello)

        bye = sub.add_parser("bye", help="Say goodbye to a named person")
        bye.add_argument("--name", required=True, help="Name to say goodbye to")
        bye.set_defaults(func=self._run_bye)

    # --- handlers ---

    def _run_hello(self, args) -> int:
        print(f"Hello, {args.name}")
        return 0

    def _run_bye(self, args) -> int:
        print(f"Bye, {args.name}")
        return 0
```

---

## Entry-Point Declaration

Declare your extension class in `pyproject.toml` under the `opentoken.extensions` entry-point group:

```toml
[project.entry-points."opentoken.extensions"]
hello-world = "opentoken_ext_hello_world.extension:HelloWorldExtension"
```

The key (`hello-world`) must match `command_name` returned by your class. The CLI uses the entry-point group for discovery; the key is used only as an identifier — the authoritative command name comes from `command_name`.

---

## Extension Lifecycle

```
install → discover → load → register → invoke → uninstall
```

| Phase         | What happens                                                                                                                                                                                       |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **install**   | `opentoken extension install <url>` downloads the package, validates it, and records it in `registry.json`. A security warning is printed and confirmation is required (unless `--yes` is passed). |
| **discover**  | At startup the CLI scans the `opentoken.extensions` entry-point group (Python package installs) and/or `registry.json` (binary installs).                                                          |
| **load**      | Each discovered entry point is imported and instantiated. Load errors print a warning and skip the extension; they do not abort the CLI.                                                           |
| **register**  | `register_subcommand(subparsers)` is called for each successfully loaded extension.                                                                                                                |
| **invoke**    | The user runs `opentoken <command_name> [args]`. The CLI dispatches to the `func` set by `set_defaults`.                                                                                           |
| **uninstall** | `opentoken extension uninstall <name>` removes the package and its registry entry.                                                                                                                 |

---

## Conflict Rules

- **Command name uniqueness**: `command_name` must not duplicate a built-in subcommand name or another installed extension's `command_name`.
- **Conflict at load time**: If two installed extensions declare the same `command_name`, the CLI prints a warning and loads the extension that sorts first alphabetically by `command_name`. The conflicting extension is skipped.
- **Built-in precedence**: Built-in subcommands always take precedence. An extension whose `command_name` matches a built-in is skipped with a warning.
- **Registry records source**: `registry.json` stores the source URL for each installed extension, which is shown in `opentoken extension list` to help diagnose conflicts.

---

## Security and Trust Model

OpenToken does not perform hash or signature verification on extension wheel files. There is no checksum comparison, code-signing check, or certificate validation during installation — the CLI installs whatever `.whl` is located at the given URL or path. Verifying the source and integrity of an extension wheel is the responsibility of the person running the install command.

### What the CLI does at install time

- Prints a `_SECURITY_WARNING` banner before taking any action. This banner is intentional and cannot be suppressed; it reads: _"Extensions are arbitrary Python code and are not verified by Truveta. Install only extensions from sources you trust."_
- Displays the source URL and prompts for confirmation.
- Confirmation is required unless `--yes` is passed. In automated environments, pass `--yes` explicitly and ensure you have independently validated the source before running the command.

**Sample install prompt:**

```
WARNING: Extensions are arbitrary Python code and are not verified by Truveta.
Install only extensions from sources you trust.
You are about to install an extension from:
  https://example.com/opentoken-ext-hello-world-1.0.0-py3-none-any.whl
Do you want to continue? [y/N]
```

### What the CLI does not do

- **No hash verification**: The CLI does not verify a SHA-256 or other checksum against a published sidecar. If the wheel file is modified in transit or at rest, the CLI will install the modified package without warning.
- **No signature verification**: There is no code-signing or certificate check on the wheel contents.
- **No origin allowlist**: Any valid `.whl` URL is accepted; the CLI has no concept of a trusted registry.

### Implications for use

Extensions run with the same privileges as the CLI process. A malicious or tampered extension has full access to the system, credentials, and data available to the user running `opentoken`.

Before installing an extension:

1. Confirm the wheel URL or file path comes from a source you control or have audited.
2. Optionally verify the SHA-256 hash of the downloaded file against a hash published by the author through an out-of-band channel (for example, a GitHub release asset or an internal artifact store).

### Operators in regulated environments

Organisations that operate in regulated or high-assurance environments should not allow end users to install extensions directly from public URLs. Instead:

- Host approved extension wheels in an internal artifact registry with access controls (for example, a private PyPI server, an internal S3 bucket, or a container image layer).
- Distribute the registry URL and, if your tooling supports it, a corresponding SHA-256 hash to employees through a controlled channel.
- Consider pre-baking approved extensions into a Docker image at build time using `--yes` against the internal registry URL so that runtime installs are not required.

This limits the install-time attack surface without requiring changes to the CLI itself.

---

## Binary Compatibility

The pre-built OpenToken binary is a PyInstaller-frozen executable. Extensions that depend on packages not bundled in the binary cannot be loaded under it.

### Three Dependency Tiers

| Tier                       | Dependencies                                                                                                            | Binary compatible? |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------- | :----------------: |
| **1 — Zero-dep**           | None (stdlib only)                                                                                                      |       ✅ Yes       |
| **2 — OpenToken-provided** | Only packages bundled in the binary (e.g., `pyarrow`, `pandas`, `csv2parquet`, `cryptography`, `jwcrypto`, `packaging`) |       ✅ Yes       |
| **3 — External**           | Any other packages                                                                                                      |       ❌ No        |

**Recommendation:** Keep extensions at Tier 1 whenever possible. Tier 1 extensions work under both the binary and a Python package install.

`opentoken extension install` aborts with a clear error when it detects a Tier-3 extension under the binary:

```
Error: This extension requires external dependencies that are not bundled in the OpenToken binary: requests, boto3
Install the Python package version of OpenToken CLI to use this extension.
```

---

## PyInstaller Constraints

PyInstaller produces a frozen binary that bundles the Python interpreter and all required packages. Entry points declared in `pyproject.toml` are metadata attached to installed packages and are **invisible** inside a frozen binary because `importlib.metadata` cannot traverse the bundle's file structure the same way it traverses a normal site-packages directory.

### Two-Track Loader

OpenToken uses a two-track loader to work around this constraint:

| Install type           | Discovery mechanism                                                   |
| ---------------------- | --------------------------------------------------------------------- |
| **Python package**     | `importlib.metadata` entry points in the `opentoken.extensions` group |
| **PyInstaller binary** | `registry.json` + `sys.path` injection                                |

Under the binary, `opentoken extension install` writes each extension's package path to `~/.opentoken/extensions/registry.json`. At startup the loader reads `registry.json`, injects each package path into `sys.path`, and then imports the extension class directly using the stored module and class name.

**Implication for authors:** You do not need to do anything special to support the binary loader. As long as your class is importable from its module path and you have declared the entry point correctly, both tracks work automatically.

### `registry.json` Schema

```json
{
  "hello-world": {
    "version": "1.0.0",
    "source_url": "file:///home/user/dist/opentoken_ext_hello_world-1.0.0-py3-none-any.whl",
    "source_path": "/home/user/.opentoken/extensions/hello-world/src",
    "module": "opentoken_ext_hello_world.extension",
    "class": "HelloWorldExtension",
    "command_name": "hello-world",
    "dist_name": "opentoken-ext-hello-world"
  }
}
```

The top-level keys are the extension `command_name` values. Each value is a metadata object with the fields shown above.

---

## Related Documentation

- [Managing Extensions](../operations/managing-extensions.md) — Install, list, and uninstall extensions
- [Extension Quickstart](../quickstarts/extension-quickstart.md) — Build and install your first extension end-to-end
- [CLI Reference](cli.md) — `opentoken extension` subcommands and environment variables
