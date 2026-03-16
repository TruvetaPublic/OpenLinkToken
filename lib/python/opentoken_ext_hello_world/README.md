# OpenToken Hello-World Reference Extension

This package demonstrates how to build an OpenToken CLI extension.

## Implementing `OpenTokenExtension`

Create a class that inherits from `OpenTokenExtension` and implements the four abstract members:

```python
from opentoken_cli.extension import OpenTokenExtension
import argparse

class MyExtension(OpenTokenExtension):
    @property
    def command_name(self) -> str:
        return "my-ext"                 # becomes `opentoken my-ext ...`

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
[project.entry-points."opentoken.extensions"]
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
opentoken extension install file://./dist/opentoken_ext_hello_world-1.0.0-py3-none-any.whl

# From a remote URL
opentoken extension install https://example.com/opentoken_ext_hello_world-1.0.0-py3-none-any.whl
```

Pass `--yes` / `-y` to skip the security confirmation prompt.

## Invoking the Extension

```bash
opentoken hello-world greet --name Alice
# → Hello, Alice! — from OpenToken hello-world extension
```

## PyInstaller / Frozen Binary Compatibility

When using the pre-built OpenToken binary (compiled with PyInstaller), extensions
are loaded from the registry file (`~/.opentoken/extensions/registry.json`) rather
than Python entry points.

**Tier-1 (fully supported)**: Extensions with **no external dependencies** beyond
the packages already bundled inside the binary. The hello-world extension is a
tier-1 extension because `dependencies = []` in its `pyproject.toml`.

**Tier-2 (not supported in frozen binaries)**: Extensions that require third-party
packages not bundled in the binary will fail to install via `opentoken extension
install` when running the frozen binary. Use the `pip`-installed Python package
version of the CLI for such extensions.
