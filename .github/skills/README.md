# `.github/skills`

This folder contains reusable skill packages for common development workflows.

## Contents

| Path               | Purpose                                                                            |
| ------------------ | ---------------------------------------------------------------------------------- |
| `doc-coauthoring/` | Structured workflow for collaboratively writing and refining documentation.        |
| `gh-cli/`          | Reference material for GitHub CLI usage across repo, PR, issue, and Actions tasks. |
| `git-commit/`      | Conventional commit workflow guidance with staging and message support.            |
| `github-issues/`   | Issue creation and management guidance, including reusable templates.              |
| `refactor/`        | Behavior-preserving refactoring workflow guidance.                                 |

## Editing guidance

- Add or revise a skill when the repository repeatedly performs the same complex workflow.
- Keep each skill self-contained: triggers, expected outcomes, gotchas, and examples should live with the skill.
- When a skill relies on repo rules, point back to [`../instructions/`](../instructions/README.md) instead of duplicating those rules.

## Related files

- Agent definitions that consume skill outputs: [`../agents/`](../agents/README.md)
- Canonical repo rules that skills should follow: [`../instructions/`](../instructions/README.md)
