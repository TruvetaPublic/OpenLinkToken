---
applyTo: "**"
description: "Always run pre-commit hooks after making code changes"
---

# Pre-Commit Hook Enforcement

After making any code changes, always run pre-commit hooks before considering the task complete:

```bash
prek run --files <changed-files>
```

Or to run against all staged changes:

```bash
prek run
```

If prek reports any failures (formatting, linting, type errors), fix them and re-run until all hooks pass. Do not mark work as done while prek hooks are failing.
