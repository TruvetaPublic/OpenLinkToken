---
layout: default
---

# Branch Workflow and Release Process

This page summarizes the repository's expected branch flow and the behavior
implemented by the GitHub Actions workflows. Repository branch-protection
settings and review requirements are maintained separately.

## Branch flow

```text
dev/* → develop → release/x.y.z → main
```

- `dev/*` branches contain feature and bug-fix work. Open their pull requests
  against `develop`.
- `develop` is the integration branch.
- `release/x.y.z` branches prepare a specific three-part version and open a
  pull request against `main`.
- `main` receives merged release pull requests and is the source of published
  tags and releases.

The branch names and pull-request targets above are repository conventions.
The workflows described below enforce the release path and help route
accidental pull requests.

## Feature pull requests

Create a `dev/<github-username>/<feature-name>` branch from `develop` and open
the pull request against `develop`.

If a same-repository, non-release pull request is opened or reopened against
`main`, `retarget-pr-to-develop.yml` changes its base branch to `develop`.
`validate-pr-target.yml` separately fails non-release pull requests that target
`main`; it does not perform the retargeting itself. Pull requests from forks
are not automatically retargeted by the retargeting workflow.

## Release process

1. Create and push `release/x.y.z` from the release-ready `develop` state.
2. Open a pull request from that branch to `main`.
3. Review the changes and wait for the version workflow to complete.
4. Merge the pull request after the repository's required checks and approvals
   pass.
5. The release workflow creates the tag and GitHub release.

### Version bump workflow

[`auto-version-bump.yml`](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/.github/workflows/auto-version-bump.yml)
runs for opened, synchronized, or reopened pull requests targeting `main`.
Its job runs only when the head branch starts with `release/`.

The workflow:

1. Requires an exact `release/x.y.z` name, where each component is numeric.
2. Reads the current Python package version.
3. When the target differs, runs the configured `bump2version` replacements,
   commits the changes, and pushes them to the release branch.
4. Comments on the pull request with the result.

If the version already matches, it posts a successful version-check comment
without creating a commit.

### Release creation workflow

[`auto-release.yml`](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/.github/workflows/auto-release.yml)
runs only after a `release/*` pull request is merged into `main`. It reads the
version from `.bumpversion.cfg`, skips work when the tag or release already
exists, and otherwise:

1. Creates the `vX.Y.Z` tag at the merged commit.
2. Generates release notes.
3. Creates a non-draft, non-prerelease GitHub release.

This workflow does **not** create or auto-merge a `main` → `develop`
synchronization pull request. Keep `develop` current through the repository's
normal pull-request process.

## Examples

### Feature work

```bash
git checkout develop
git pull origin develop
git checkout -b dev/<github-username>/<feature-name>
# Make and test changes
git push origin dev/<github-username>/<feature-name>
# Open a pull request to develop
```

### Release

```bash
git checkout develop
git pull origin develop
git checkout -b release/2.2.0
git push origin release/2.2.0
# Open a pull request from release/2.2.0 to main
```

### Hotfix

A hotfix still uses a new, valid `release/x.y.z` branch and a pull request to
`main`. The workflows do not define a separate hotfix branch name or an
automatic back-merge to `develop`; coordinate that follow-up through the usual
pull-request process.

## FAQ

**Why should feature pull requests target `develop`?**

`develop` is the integration branch. The release workflows reserve `main` for
release pull requests.

**What happens if I target `main` from a feature branch?**

Same-repository non-release pull requests are automatically retargeted to
`develop` when opened or reopened. The validation workflow also rejects
non-release pull requests that remain targeted at `main`.

**Do I need to bump versions manually?**

No. Use the exact version in the `release/x.y.z` branch name and let
`auto-version-bump.yml` update configured version references.

## Related documentation

- [Community and contribution guidance](community/index.md)
- [Developer Guide](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/docs/dev-guide-development.md)
- [`retarget-pr-to-develop.yml`](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/.github/workflows/retarget-pr-to-develop.yml)
- [`validate-pr-target.yml`](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/.github/workflows/validate-pr-target.yml)
