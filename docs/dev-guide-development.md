# Development guide

This guide covers local setup, builds, tests, and cross-language changes.
Repository rules live in
[`.github/instructions/`](../.github/instructions/); the
[branch workflow](./branch-workflow-and-release-process.md) and
[publishing guide](./publishing-guide.md) cover releases.

## Development environment

The Dev Container is the supported setup. In VS Code, open the repository and
select **Dev Containers: Reopen in Container**. It provides:

- JDK 21 and Maven 3.8.8
- Python 3.11 and `uv`
- Node.js, Docker, Git LFS, and GitHub CLI

The project supports Python 3.10 or newer. The container stores the shared
Python environment at `/home/vscode/.local/share/openlinktoken/.venv`.
Do not create a nested virtual environment inside a package directory.

From the repository root, install the workspace dependencies:

```bash
uv sync --all-packages --dev
```

The workspace contains the following packages:

```text
lib/java/
  pom.xml
  openlinktoken/
  openlinktoken-core-ai/
lib/python/
  openlinktoken/
  openlinktoken-core-ai/
  openlinktoken-cli/
  openlinktoken-pyspark/
lib/python/openlinktoken_ext_hello_world/
resources/
tools/
docs/
pages/
```

## Build and test

Build the Java modules:

```bash
(cd lib/java && mvn clean install)
```

Run Java tests:

```bash
(cd lib/java && mvn test)
```

Checkstyle runs as part of the Java build; run it standalone with
`(cd lib/java && mvn checkstyle:check)`.

Run Python tests for the packages changed by your work:

```bash
(cd lib/python/openlinktoken && PYTHONPATH=src/main uv run pytest src/test)
(cd lib/python/openlinktoken-core-ai && PYTHONPATH=src/main:../openlinktoken/src/main uv run pytest src/test)
(cd lib/python/openlinktoken-cli && PYTHONPATH=src/main:../openlinktoken/src/main:../openlinktoken-core-ai/src/main uv run pytest src/test)
(cd lib/python/openlinktoken-pyspark && PYTHONPATH=src/main:../openlinktoken/src/main uv run pytest src/test)
```

The PySpark tests require a compatible Spark installation. Use the package
extras in `lib/python/openlinktoken-pyspark/pyproject.toml`. See
[Spark or Databricks](../pages/operations/spark-or-databricks.md) for
distributed-processing setup and usage.

Run the repository formatter and linter through the tools already configured in
the workspace:

```bash
uv run ruff check .
uv run ruff format --check .
```

After changing files, run the pre-commit hooks for those files:

```bash
prek run --files <changed-file>...
```

Build the Docker image when the Docker surface changes:

```bash
docker build . -t openlinktoken
```

## CLI smoke test

The CLI package provides the `olt` command. After `uv sync`:

```bash
uv run olt --help
uv run olt tokenize \
  -i resources/sample.csv \
  -o /tmp/openlinktoken-output.csv \
  --mode demo \
  --disable-inferencing
```

Use `package` with an exchange configuration for encrypted output. See the
[CLI quickstart](../pages/quickstarts/cli-quickstart.md) for the complete
key-exchange flow, including `generate-key-pair`. For programmatic use of the
core library instead of the CLI, see the
[Java API reference](../pages/reference/java-api.md) and
[Python API reference](../pages/reference/python-api.md).

To build the self-contained CLI used by the release workflow:

```bash
uv run pyinstaller --clean --noconfirm lib/python/openlinktoken-cli/openlinktoken-cli.spec
```

The executable is written to `dist/olt` or `dist/olt.exe`. To create the
release archive and checksum for one platform:

```bash
uv run python -m openlinktoken_cli.util.release_assets \
  --version 2.1.1 \
  --runner-os Linux \
  --dist-dir dist \
  --output-dir release-assets
```

## Cross-language changes

Open Link Token has Java and Python implementations. Shared behavior must stay
equivalent, including normalization, validation, token composition, and
cryptographic stages.

When adding a token or attribute:

1. Update the Java implementation and its ServiceLoader file:
   `lib/java/openlinktoken/src/main/resources/META-INF/services/`.
2. Update the matching Python implementation and loader or registry.
3. Add tests for both implementations.
4. Run the interoperability checks when the change affects token output:
   `tools/multi_language_syncer.py` and
   `tools/interoperability/`.

The Python CLI discovers token definitions from
`openlinktoken/tokens/definitions` and loads attributes through
`attribute_loader.py`. Custom token rules can also use
[`tokenize --config`](./tokenization-config-format.md).

## Extensions

The reference extension is
`lib/python/openlinktoken_ext_hello_world/`. For the extension interface,
entry-point registration, installation, frozen-binary compatibility, and
reporting custom progress metrics, see the
[Extension Author Reference](../pages/reference/extensions.md), its
[README](../lib/python/openlinktoken_ext_hello_world/README.md), and the
[extension quickstart](../pages/quickstarts/extension-quickstart.md).

Editable local install:

```bash
uv pip install -e lib/python/openlinktoken_ext_hello_world
uv run olt extension list
```

## Code and security guidance

Use the scoped repository instructions instead of copying their full rules
into this guide:

- [Java instructions](../.github/instructions/java.instructions.md)
- [Python instructions](../.github/instructions/python.instructions.md)
- [Architecture and parity](../.github/instructions/openlinktoken-architecture.instructions.md)
- [Security guidance](../.github/instructions/security-and-owasp.instructions.md)
- [Commenting guidance](../.github/instructions/self-explanatory-code-commenting.instructions.md)

Keep code self-explanatory. Comments should explain a non-obvious reason, not
repeat the statement next to them. Never place real secrets in examples,
tests, logs, or metadata.

## Versioning and contribution checklist

Normal development pull requests do not need a manual version change. Create a
release branch when preparing a release; `auto-version-bump.yml` updates the
configured version files.

Before opening a pull request:

- run the tests for the changed package;
- run Java and Python parity checks for shared behavior;
- update user-facing documentation when behavior changes;
- run `prek` for the changed files;
- use a `dev/<github-username>/<feature>` branch and target `develop`.

For release branches, use the process in
[Branch and release workflow](./branch-workflow-and-release-process.md).

## Troubleshooting

| Problem                        | Check                                                                                       |
| ------------------------------ | ------------------------------------------------------------------------------------------- |
| Java class is not discovered   | Check the matching ServiceLoader file and class name.                                       |
| Python attribute is not loaded | Check `attribute_loader.py` and its registration entry.                                     |
| Java and Python tokens differ  | Compare normalization, rule order, secrets, and the interoperability fixtures.              |
| Python import fails            | Run `uv sync --all-packages --dev` from the repository root and use the shared environment. |
| Java build fails on Checkstyle | Run `mvn -q checkstyle:check` locally and fix the reported warnings.                        |
