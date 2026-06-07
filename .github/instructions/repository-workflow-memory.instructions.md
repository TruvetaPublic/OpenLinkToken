---
description: "Repository-specific workflow reminders and verification habits"
applyTo: "**"
---

# Repository Workflow Memory

Keep repository-specific completion steps consistent.

## Run prek after edits

After finishing changes to files in this repository, run `prek run --files <changed-files>` from the repository root before considering the task complete. Use the exact files changed for the current task rather than running prek across the whole repository. If it reports problems, address them or clearly report the blocker.
