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
matching the PySpark development extra and the existing lockfile state.
Regenerate `uv.lock` from the aligned manifests.

Add a pull-request dependency-resolution guard to the existing CI workflow.
The guard runs uv’s universal lock validation so supported Python versions,
platform markers, workspace packages, and declared extras are resolved before
merge. It should validate the lockfile rather than silently rewrite it.

Keep the existing package-specific test installation paths unchanged. Those
jobs deliberately install only the Spark extra under test and the shared test
requirements; the new guard covers the separate workspace-resolution path used
by release builds.

## Validation

- The root dev group and `openlinktoken-pyspark[dev]` resolve to the same
  notebook version.
- `uv lock --check` passes against the committed manifests and lockfile.
- The new CI guard fails if a future dependency update creates an unsatisfiable
  workspace.
- Existing Python, PySpark, CLI, and release build workflows continue to use
  their current installation and test commands.
