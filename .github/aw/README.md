# `.github/aw`

This folder supports GitHub Agentic Workflows (gh-aw) in this repository.

## Contents

| Path                | Purpose                                                                                       |
| ------------------- | --------------------------------------------------------------------------------------------- |
| `actions-lock.json` | Version lock file for actions used by gh-aw-managed workflows. Treat this as generated state. |
| `imports/`          | Imported gh-aw assets and shared workflow resources used by agentic workflow definitions.     |

## Editing guidance

- Avoid hand-editing generated or imported files unless you are intentionally updating the gh-aw setup.
- If a gh-aw workflow changes, review both this folder and the workflow definitions under [`../workflows/`](../workflows/README.md).
- Use this folder as supporting infrastructure for agentic workflows, not as the main authoring surface.

## Related files

- gh-aw agent definition: [`../agents/agentic-workflows.agent.md`](../agents/agentic-workflows.agent.md)
- Workflow definitions: [`../workflows/`](../workflows/README.md)
