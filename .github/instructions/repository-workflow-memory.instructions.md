---
description: "Repository-specific workflow reminders and verification habits"
applyTo: "**"
---

# Repository Workflow Memory

Keep repository-specific completion steps consistent.

## Pin exact versions of all dependencies

When adding or updating packages in `requirements.txt`, `setup.py` `install_requires`/`extras_require`, or `pyproject.toml` dependency lists, always use exact version pins (`==`) rather than ranges or unpinned names.

```text
# Good — reproducible, no surprise upgrades
pyarrow==24.0.0
packaging==24.2

# Avoid — allows unexpected version changes
pyarrow>=19.0.0
packaging
```

**Exception:** Use a minimum-version bound (`>=X.Y`) only when a strict pin would create a cross-package conflict within the same uv workspace (e.g., a shared transitive dependency like `packaging` that is also constrained by a dev tool). Document the reason inline when you do.

After changing any dependency file, run `uv lock` to verify the full workspace resolves without conflicts across all supported Python versions.

## Run prek after edits

After finishing changes to files in this repository, run `prek run --files <changed-files>` from the repository root before considering the task complete. Use the exact files changed for the current task rather than running prek across the whole repository. If it reports problems, address them or clearly report the blocker.
