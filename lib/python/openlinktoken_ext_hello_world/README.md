# Open Link Token Hello-World Reference Extension

This package demonstrates how to build an Open Link Token CLI extension.

## Implementing `OpenLinkTokenExtension`

Create a class that inherits from `OpenLinkTokenExtension` and implements the four abstract members:

```python
from openlinktoken_cli.extension import OpenLinkTokenExtension
import argparse

class MyExtension(OpenLinkTokenExtension):
    @property
    def command_name(self) -> str:
        return "my-ext"                 # becomes `openlinktoken my-ext ...`

    @property
    def description(self) -> str:
        return "My custom extension"

    @property
    def version(self) -> str:
        return "1.0.0"

    def register_subcommand(self, subparsers: argparse._SubParsersAction) -> None:
        parser = subparsers.add_parser(self.command_name, help=self.description)
        sub = parser.add_subparsers(dest="my_ext_subcommand")

        run = sub.add_parser("run", help="Run something")
        run.add_argument("--input", required=True)
        run.set_defaults(func=MyExtension._run)

        parser.set_defaults(func=lambda args: (parser.print_help(), 0)[1])

    @staticmethod
    def _run(args) -> int:
        print(f"Running with: {args.input}")
        return 0
```

## Declaring the Entry Point

In your `pyproject.toml`:

```toml
[project.entry-points."openlinktoken.extensions"]
my-ext = "my_package.extension:MyExtension"
```

The key (`my-ext`) is the entry-point name; the value points to the class using
`module:ClassName` notation.

## Building the Wheel

```bash
pip install build
python -m build
```

This produces `dist/my_package-1.0.0-py3-none-any.whl`.

## Installing the Extension

```bash
# From a local build
olt extension install file:///$(pwd)/dist/openlinktoken_ext_hello_world-1.0.0-py3-none-any.whl

# From a remote URL
olt extension install https://example.com/openlinktoken_ext_hello_world-1.0.0-py3-none-any.whl
```

Pass `--yes` / `-y` to skip the security confirmation prompt.

## Invoking the Extension

```bash
olt hello-world hello --name Alice
# → Hello, Alice

olt hello-world bye --name Bob
# → Bye, Bob
```

## PyInstaller / Frozen Binary Compatibility

When using the pre-built Open Link Token binary (compiled with PyInstaller), extensions
are loaded from the registry file (`~/.openlinktoken/extensions/registry.json`) rather
than Python entry points.

**Tier-1 (fully supported)**: Extensions with **no external dependencies** beyond
the standard library. The hello-world extension is a Tier-1 extension because
`dependencies = []` in its `pyproject.toml`.

**Tier-2 (supported)**: Extensions that depend only on packages already bundled
inside the binary (e.g., `pandas`, `pyarrow`, `cryptography`). These are binary-compatible
because those packages are shipped inside the executable.

**Tier-3 (not supported in frozen binaries)**: Extensions that require third-party
packages not bundled in the binary will fail to install via `olt extension
install` when running the frozen binary. Use the `pip`-installed Python package
version of the CLI for such extensions.
