---
description: "OpenToken branch and pull request workflow"
applyTo: "**"
---

# Pull Request and Branch Workflow

## Required Defaults

- All new pull requests MUST be created in **draft** mode.
- Standard feature branch format: `dev/<github-username>/<feature-description>`
- Standard base branch for feature, docs, test, and refactor work: `develop`
- Do not target `main` unless handling an approved release or emergency hotfix

## Branching Guidance

- If you are starting new work from `main`, switch to `develop` first.
- If you are already on the correct task branch, continue there.
- If you are on an unrelated feature branch, stash or commit as needed, then create a new correctly named branch from `develop`.
- Use kebab-case for the feature description portion of the branch name.

### Branch Creation Example

```bash
git checkout develop
git pull origin develop
git checkout -b "dev/<github-username>/<feature-description>"
git push -u origin "dev/<github-username>/<feature-description>"
```

## Creating Pull Requests

- Prefer repository-integrated PR tooling when available instead of `gh pr create`.
- Always set `draft: true` when opening a PR.
- If a PR is accidentally opened as ready for review, move it back to draft immediately.
- Do not convert a PR out of draft automatically; wait for explicit user direction or confirmed readiness.

## PR Targeting Guidance

- Normal work targets `develop`.
- Release or hotfix work may target `main` when explicitly intended.
- If a hotfix is merged to `main`, follow up with a sync PR from `main` back into `develop`.

## PR Readiness Checklist

Before converting a PR from draft to ready for review, ensure:

- [ ] All CI checks passing
- [ ] Code coverage ≥80% for new code
- [ ] Both Java and Python implementations updated (if applicable)
- [ ] Tests added/updated for changes
- [ ] Documentation updated (README, JavaDoc, docstrings)
- [ ] Service registration files updated (if adding attributes/tokens)
- [ ] No secrets or sensitive data committed
- [ ] Jupyter notebook outputs cleared

## Standard PR Structure

**Title Format:** `<type>: <short summary>`

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

**Body Template:**

```markdown
## Summary

Brief overview of changes and motivation

## Changes

- Detailed change 1
- Detailed change 2

## Testing

- [ ] Test item 1
- [ ] Test item 2

## Files Changed

- `path/to/file1` (X lines)
- `path/to/file2` (Y lines)
```
