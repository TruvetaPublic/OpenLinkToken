# OpenLinkToken AI Coding Agent Instructions

This file is the runtime entrypoint. Keep it concise, and use the scoped instruction files in `.github/instructions/` for detailed guidance.

## Always-on repo rules

- **Java:** Never use fully qualified class names in Java code. Add imports and use short class names.
- **Python:** Use the shared Python virtual environment at `/home/vscode/.local/share/openlinktoken/.venv` (the workspace-root `.venv` is a symlink to it after setup). Never create or activate a nested venv under `lib/python/...`.
- **Dual implementation:** OpenLinkToken maintains Java and Python implementations. Preserve cross-language parity for shared behavior changes.
- **Registration:** When adding or changing attributes or tokens, update Java ServiceLoader entries and the matching Python loader/registry when required.
- **Branches:** For new work, branch from `develop` using `dev/<github-username>/<feature-description>`.
- **Pull requests:** Standard PRs target `develop`, and new PRs must be opened as **drafts**.

## Canonical detailed guidance

- **Java files:** `.github/instructions/java.instructions.md`
- **Python files:** `.github/instructions/python.instructions.md`
- **OpenLinkToken architecture and parity:** `.github/instructions/openlinktoken-architecture.instructions.md`
- **PR and branch workflow:** `.github/instructions/pull-request.instructions.md`
- **Security guidance:** `.github/instructions/security-and-owasp.instructions.md`
- **Commenting guidance:** `.github/instructions/self-explanatory-code-commenting.instructions.md`
- **Specialized task handling:** Prefer matching custom agents from `.github/agents/` when their scope fits the work.

## Code review

When performing a code review, focus only on findings that are medium severity or higher. Skip style preferences, minor nitpicks, and low-impact suggestions. Surface bugs, security vulnerabilities, logic errors, correctness issues, and significant maintainability or performance concerns. For each finding, clearly state the severity, the risk, and what the fix should achieve.

## Runtime usage notes

- Load only the smallest relevant instruction set for the files you are editing.
- Keep this file summary-only; move detailed guidance to scoped instruction modules instead of duplicating it here.
- For OpenLinkToken component layout, registration patterns, and parity-sensitive changes, use `.github/instructions/openlinktoken-architecture.instructions.md`.
