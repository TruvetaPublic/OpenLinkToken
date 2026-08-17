# Branch and release workflow

Standard development work targets `develop`. Production releases use a
`release/x.y.z` branch and merge to `main`.

## Branches

| Branch                            | Use                                       | Normal target   |
| --------------------------------- | ----------------------------------------- | --------------- |
| `develop`                         | Integration branch                        | `release/x.y.z` |
| `dev/<github-username>/<feature>` | Feature, fix, documentation, or test work | `develop`       |
| `release/x.y.z`                   | Version bump and release review           | `main`          |
| `main`                            | Released code                             | None            |

Create development branches from the current `develop` branch:

```bash
git switch develop
git pull origin develop
git switch -c dev/<github-username>/<feature>
```

Use a valid semantic version in release branch names, for example
`release/2.2.0`.

## Pull request routing

- Open normal pull requests against `develop`.
- Pull requests to `main` must come from `release/*`.
- `retarget-pr-to-develop.yml` changes a same-repository, non-release pull
  request from `main` to `develop` when it is opened or reopened.
- `validate-pr-target.yml` rejects a `main` pull request whose source branch is
  not `release/*`.

The retarget workflow does not change pull requests from forks.

## Release flow

1. Create `release/x.y.z` from `develop`.
2. Open a pull request from that branch to `main`.
3. `auto-version-bump.yml` validates the version and runs `bump2version` on
   pull-request open, synchronize, and reopen events. It commits the configured
   version-file changes to the release branch.
4. Review and merge the release pull request.
5. `auto-release.yml` reads the version from `.bumpversion.cfg`, creates
   `vX.Y.Z`, and creates the GitHub release when the tag and release do not
   already exist.
6. The Maven, Python, Docker, and CLI release workflows build and publish the
   release artifacts.

`auto-release.yml` does not create a `main` to `develop` sync pull request. If
the release changes must be copied to `develop`, open that pull request
separately.

## Hotfix flow

Create a new `release/x.y.z` branch from `main`, apply the fix, and open the
pull request to `main`. Use a new valid version, such as `release/2.1.2`.
After the release, copy the hotfix to `develop` with a separate pull request.

## Manual release commands

```bash
git switch develop
git pull origin develop
git switch -c release/2.2.0
git push --set-upstream origin release/2.2.0
```

Then open the pull request to `main`. Do not edit version files manually; the
version-bump workflow updates the files listed in `.bumpversion.cfg`.

## Related files

- [Development guide](./dev-guide-development.md)
- [Publishing guide](./publishing-guide.md)
- [`auto-version-bump.yml`](../.github/workflows/auto-version-bump.yml)
- [`auto-release.yml`](../.github/workflows/auto-release.yml)
- [`retarget-pr-to-develop.yml`](../.github/workflows/retarget-pr-to-develop.yml)
- [`validate-pr-target.yml`](../.github/workflows/validate-pr-target.yml)
