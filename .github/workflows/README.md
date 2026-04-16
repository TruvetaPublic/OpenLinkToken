# `.github/workflows`

This folder contains the repository's GitHub Actions workflows for CI, releases, publishing, Pages deployment, and agentic automation.

## Contents

### CI, quality, and synchronization

- `ci.yml` - primary multi-language CI pipeline
- `codeql.yml` - security analysis
- `multi-language-sync.yml` - cross-language sync validation
- `validate-pr-target.yml` - PR target enforcement

### Release and publishing

- `auto-release.yml` - release automation
- `auto-version-bump.yml` - version bump automation
- `maven-publish.yml` - Java package publishing
- `python-publish.yml` - Python package publishing
- `docker-publish.yml` - container publishing
- `build-openlinktoken-cli.yml` - CLI build artifacts

### Documentation and repository maintenance

- `deploy-pages.yml` - GitHub Pages deployment
- `retarget-pr-to-develop.yml` - branch-target hygiene
- `release-context.yml` - release context support
- `copilot-setup-steps.yml` - Copilot setup wiring

### Agentic workflows

- `code-simplifier.md` - source definition for the code simplifier agentic workflow
- `code-simplifier.lock.yml` - compiled/locked output for the agentic workflow
- `agentics-maintenance.yml` - scheduled maintenance workflow for agentic tooling

## Editing guidance

- Prefer reusable setup from [`../actions/`](../actions/README.md) instead of duplicating toolchain setup in every workflow.
- Treat lock/generated agentic workflow outputs carefully; edit the source definition when possible.
- Review permissions, triggers, and branch targeting whenever you change a workflow.
- Keep workflow behavior aligned with repo standards from [`../instructions/`](../instructions/README.md).

## Related files

- Shared composite actions: [`../actions/`](../actions/README.md)
- gh-aw support files: [`../aw/`](../aw/README.md)
- Agent guidance for workflow work: [`../agents/agentic-workflows.agent.md`](../agents/agentic-workflows.agent.md)
