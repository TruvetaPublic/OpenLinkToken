---
applyTo: "**"
description: "Always run pre-commit hooks after making code changes"
---

# Pre-Commit Hook Enforcement

After making any code changes, always run pre-commit hooks before considering the task complete:

```bash
prek run --files <changed-files>
```

In this repository, prefer `--files` with the exact changed paths for the current task. Do not run `prek run` across all files unless the user explicitly asks for repo-wide verification.

If prek reports any failures (formatting, linting, type errors), fix them and re-run against the changed files until all hooks pass. Do not mark work as done while prek hooks are failing.
