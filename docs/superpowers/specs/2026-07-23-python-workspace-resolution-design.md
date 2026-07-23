# Python Workspace Dependency Resolution Design

## Problem

The root uv workspace pins `notebook==7.5.7`, while the
`openlinktoken-pyspark[dev]` extra pins `notebook==7.6.0`. Resolving the
workspace with all packages and development dependencies is therefore
unsatisfiable.

The pull-request CI runs package-specific `uv pip install` commands and does
not resolve the uv workspace. The release CLI workflow runs `uv sync
--all-packages`, so it exposed the conflict only after the 2.1.0 merge.

## Design

Use `notebook==7.6.0` as the canonical exact pin in the root workspace,
matching the PySpark development extra. The repository intentionally ignores
`uv.lock`, so regenerate it locally to verify the full workspace but do not
commit it.

Add a pull-request dependency-resolution guard to the existing CI workflow.
The guard runs `uv lock`, which performs uv’s universal resolution so supported
Python versions, platform markers, workspace packages, and declared extras are
resolved before merge. Since no lockfile is committed, the CI job validates
resolution rather than checking a committed lockfile.

Keep the existing package-specific test installation paths unchanged. Those
jobs deliberately install only the Spark extra under test and the shared test
requirements; the new guard covers the separate workspace-resolution path used
by release builds.

## Validation

- The root dev group and `openlinktoken-pyspark[dev]` resolve to the same
  notebook version.
- `uv lock` passes against the committed manifests.
- The new CI guard fails if a future dependency update creates an unsatisfiable
  workspace.
- Existing Python, PySpark, CLI, and release build workflows continue to use
  their current installation and test commands.
