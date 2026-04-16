# `.github/agents`

This folder holds the repository's custom Copilot agent definitions.

## Contents

| File                             | Purpose                                                                                          |
| -------------------------------- | ------------------------------------------------------------------------------------------------ |
| `orchestrator.agent.md`          | Routes work to the right specialist by surface and task type.                                    |
| `java-coder.agent.md`            | Owns Java implementation work under `lib/java/**`, including tests and ServiceLoader updates.    |
| `python-coder.agent.md`          | Owns Python implementation work under `lib/python/**` and `tools/**/*.py`.                       |
| `code-reviewer.agent.md`         | Reviews changes for Open Link Token-specific risks, verification gaps, and documentation impact. |
| `documentation-creator.agent.md` | Owns repo-root project markdown such as `README.md` and contributor-facing docs.                 |
| `docs-maintainer.agent.md`       | Owns `docs/**` and keeps durable reference/spec content aligned.                                 |
| `github-pages-content.agent.md`  | Owns `pages/**`, including GitHub Pages navigation and front matter.                             |
| `agentic-workflows.agent.md`     | Handles gh-aw workflow authoring, debugging, and upgrade tasks.                                  |

## Editing guidance

- Keep agent files concise, explicit, and scoped to a clear surface or responsibility.
- Update routing expectations in `orchestrator.agent.md` whenever ownership boundaries change.
- Use language agents for implementation ownership and keep review readiness in `code-reviewer.agent.md`.
- Keep durable repo rules in [`../instructions/`](../instructions/README.md) or [`../copilot-instructions.md`](../copilot-instructions.md), not duplicated inside every agent.
- Update the repo-level registry in [`../../AGENT.md`](../../AGENT.md) when you add, remove, or rename an agent.

## Related files

- Repo agent registry: [`../../AGENT.md`](../../AGENT.md)
- Canonical rules: [`../instructions/`](../instructions/README.md)
- Reusable process guidance: [`../skills/`](../skills/README.md)
