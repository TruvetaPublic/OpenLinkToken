---
layout: default
---

# Extension Quickstart

Build, package, and install your first Open Link Token CLI extension end-to-end. This walkthrough uses the `hello-world` reference extension from the Open Link Token monorepo (`lib/python/openlinktoken_ext_hello_world/`).

By the end you will have a new `hello-world` subcommand available in your local `openlinktoken` installation.

---

## Prerequisites

- Open Link Token CLI installed (binary or Python package). See [CLI Quickstart](cli-quickstart.md).
- Python 3.10 or later.
- `build` package: `pip install build`

---

## 1. Implement the Extension

Create a new Python package directory:

```bash
mkdir openlinktoken-hello-world
cd openlinktoken-hello-world
mkdir openlinktoken_ext_hello_world
touch openlinktoken_ext_hello_world/__init__.py
```

Create `openlinktoken_ext_hello_world/extension.py`:

```python
from openlinktoken_cli.extension import OpenLinkTokenExtension


class HelloWorldExtension(OpenLinkTokenExtension):
    """Reference extension — greet the world."""

    @property
    def command_name(self) -> str:
        return "hello-world"

    @property
    def description(self) -> str:
        return "Greet the world from an Open Link Token extension"

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

This extension uses only the Python standard library and the `openlinktoken.extension` base class — it is **Tier 1 (zero-dep)** and works under both the binary and a Python package install.

---

## 2. Declare the Entry Point

Create `pyproject.toml` in the `openlinktoken-hello-world/` directory:

```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "openlinktoken-ext-hello-world"
version = "1.0.0"
description = "Hello-world reference extension for the Open Link Token CLI"
requires-python = ">=3.10"

[project.entry-points."openlinktoken.extensions"]
hello-world = "openlinktoken_ext_hello_world.extension:HelloWorldExtension"
```

The entry-point key (`hello-world`) must match the `command_name` property in your class.

---

## 3. Package It

Build a wheel from the `openlinktoken-hello-world/` directory:

```bash
python -m build
```

This creates a `dist/` directory containing:

```
dist/
  openlinktoken_ext_hello_world-1.0.0-py3-none-any.whl
  openlinktoken_ext_hello_world-1.0.0.tar.gz
```

---

## 4. Install It

Install the wheel into Open Link Token using the `file://` scheme with an absolute path:

```bash
olt extension install file://$(pwd)/dist/openlinktoken_ext_hello_world-1.0.0-py3-none-any.whl
```

Open Link Token prints a security warning and asks for confirmation:

```text
⚠ Security warning: you are about to install an extension from an unverified source.

  Extensions run with full access to your system. Only install extensions
  from sources you trust.

Install this extension? [y/N]: y

✓ Installed hello-world 1.0.0 (command: hello-world)
```

Enter `y` to proceed. To skip the prompt in scripts, pass `--yes`:

```bash
olt extension install --yes file://$(pwd)/dist/openlinktoken_ext_hello_world-1.0.0-py3-none-any.whl
```

---

## 5. Verify the Extension Is Registered

Confirm the extension appears in the help output:

```bash
olt --help
```

You should see `hello-world` listed alongside the built-in subcommands:

```
...
  hello-world         Greet the world from an Open Link Token extension
...
```

Confirm it is tracked in the registry:

```bash
olt extension list
```

```
NAME          VERSION  COMMAND       SOURCE
hello-world   1.0.0    hello-world   file:///home/user/openlinktoken-hello-world/dist/openlinktoken_ext_hello_world-1.0.0-py3-none-any.whl
```

---

## 6. Run It

Run the `hello` subcommand:

```bash
olt hello-world hello --name Alice
```

```
Hello, Alice
```

Run the `bye` subcommand:

```bash
olt hello-world bye --name Bob
```

```
Bye, Bob
```

---

## Keeping Extensions Binary-Compatible

The `hello-world` extension uses only the Python standard library — it is **Tier 1 (zero-dep)**. This means it installs and loads correctly under both the pre-built Open Link Token binary and a Python package install.

If your extension needs additional packages, check the [Extension Author Reference: Binary Compatibility](../reference/extensions.md#binary-compatibility) for the list of packages bundled in the binary. Packages that are bundled (e.g., `pandas`, `pyarrow`, `cryptography`) are **Tier 2** (Open Link Token-provided) and are also binary-compatible. Any package not in the list makes your extension **Tier 3** (external), which is incompatible with the binary.

For more detail on the three tiers and the two-track loader, see [Extension Author Reference: Binary Compatibility](../reference/extensions.md#binary-compatibility).

---

## Next Steps

- [Extension Author Reference](../reference/extensions.md) — Full ABC contract, conflict rules, security model
- [Managing Extensions](../operations/managing-extensions.md) — Uninstall and CI/container workflows
- [CLI Reference](../reference/cli.md) — `olt extension` command options
