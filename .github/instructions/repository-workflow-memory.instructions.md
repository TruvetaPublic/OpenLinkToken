---
description: "Repository-specific workflow reminders and verification habits"
applyTo: "**"
---

# Repository Workflow Memory

Keep repository-specific completion steps consistent.

## Run prek after edits

After finishing changes to files in this repository, run `prek run --files <changed-files>` from the repository root before considering the task complete. Use the exact files changed for the current task rather than running prek across the whole repository. If it reports problems, address them or clearly report the blocker.

## launch.json coverage for CLI commands

Every CLI command must have a corresponding entry in `.vscode/launch.json`. When adding or updating any command in `lib/python/opentoken-cli/src/main/opentoken_cli/commands/`, add or update the matching debug configuration.

Requirements for each configuration:
- `PYTHONPATH` must include all three source roots: `lib/python/opentoken-cli/src/main:lib/python/opentoken/src/main:lib/python/opentoken-core-ai/src/main`
- Use `${input:*}` variables for runtime-variable values (file paths, exchange config paths)
- For commands with potentially destructive side effects, prefer safe defaults (e.g., `--dry-run`, `--demo-mode`)
- Add any new required `inputs` entries to the shared `inputs` array at the bottom of the file
