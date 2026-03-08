# `.github/instructions`

This folder contains the canonical supplemental instruction modules for Copilot and custom agents.

## Contents

| File                                               | Purpose                                                                                           |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `java.instructions.md`                             | Java-specific rules, including import usage, build checks, and code review expectations.          |
| `python.instructions.md`                           | Python-specific rules, including the repo-root `.venv`, typing, formatting, and testing guidance. |
| `opentoken-architecture.instructions.md`           | OpenToken architecture, parity-sensitive changes, and cross-language registration guidance.       |
| `pull-request.instructions.md`                     | Branch naming, draft PR defaults, and PR readiness expectations.                                  |
| `security-and-owasp.instructions.md`               | Security-first coding guidance based on OWASP-style concerns.                                     |
| `self-explanatory-code-commenting.instructions.md` | Commenting guidance focused on explaining why, not what.                                          |

## Editing guidance

- Keep detailed, durable rules here rather than expanding [`../copilot-instructions.md`](../copilot-instructions.md).
- Use `applyTo` front matter to keep each instruction scoped to the smallest useful surface.
- Update examples and commands whenever repo practices change so agent guidance stays accurate.
- When a rule changes here, review the affected agent definitions under [`../agents/`](../agents/README.md) for stale references.

## Related files

- Runtime entrypoint: [`../copilot-instructions.md`](../copilot-instructions.md)
- Agent registry: [`../../AGENT.md`](../../AGENT.md)
- Specialist agents that rely on these rules: [`../agents/`](../agents/README.md)
