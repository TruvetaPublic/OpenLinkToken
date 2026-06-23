# `.github/instructions`

This folder contains the canonical supplemental instruction modules for Copilot and custom agents.

## Contents

| File                                               | Purpose                                                                                                                            |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `java.instructions.md`                             | Java-specific rules, including import usage, build checks, and code review expectations.                                           |
| `python.instructions.md`                           | Python-specific rules, including the shared venv and workspace `.venv` symlink guidance, typing, formatting, and testing guidance. |
| `openlinktoken-architecture.instructions.md`       | Open Link Token architecture, parity-sensitive changes, and cross-language registration guidance.                                  |
| `issue.instructions.md`                            | Conventions for creating and routing GitHub issues using the repository issue templates.                                           |
| `pull-request.instructions.md`                     | Branch naming, draft PR defaults, and PR readiness expectations.                                                                   |
| `pre-commit.instructions.md`                       | Pre-commit enforcement guidance, including required `prek run --files` checks on changed files.                                    |
| `repository-workflow-memory.instructions.md`       | Repository workflow reminders for dependency pinning, `uv lock` after dependency edits, and targeted `prek` verification habits.   |
| `security-and-owasp.instructions.md`               | Security-first coding guidance based on OWASP-style concerns.                                                                      |
| `self-explanatory-code-commenting.instructions.md` | Commenting guidance focused on explaining why, not what.                                                                           |

## Editing guidance

- Keep detailed, durable rules here rather than expanding [`../copilot-instructions.md`](../copilot-instructions.md).
- Use `applyTo` front matter to keep each instruction scoped to the smallest useful surface.
- Update examples and commands whenever repo practices change so agent guidance stays accurate.
- When a rule changes here, review the affected agent definitions under [`../agents/`](../agents/README.md) for stale references.

## Related files

- Runtime entrypoint: [`../copilot-instructions.md`](../copilot-instructions.md)
- Agent registry: [`../../AGENT.md`](../../AGENT.md)
- Specialist agents that rely on these rules: [`../agents/`](../agents/README.md)
