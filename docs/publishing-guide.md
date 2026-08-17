# Publishing guide

GitHub Actions publishes Open Link Token artifacts after a release:

| Artifact                          | Workflow                                                        | Destination                       |
| --------------------------------- | --------------------------------------------------------------- | --------------------------------- |
| Java JARs and POMs                | [`maven-publish.yml`](../.github/workflows/maven-publish.yml)   | GitHub Packages and Maven Central |
| Python wheels and source archives | [`python-publish.yml`](../.github/workflows/python-publish.yml) | PyPI                              |
| Docker image                      | [`docker-publish.yml`](../.github/workflows/docker-publish.yml) | GitHub Container Registry         |
| CLI binaries                      | [`build-olt-cli.yml`](../.github/workflows/build-olt-cli.yml)   | GitHub release assets             |

## Required setup

### Maven Central

1. Create or sign in to a Central Publisher Portal account.
2. Verify the `org.openlinktoken` namespace.
3. Generate a Central Portal user token at
   <https://central.sonatype.com/account>.
4. Create a GPG signing key and publish its public key to a supported key
   server.
5. Add these repository Actions secrets:

   | Secret                    | Value                              |
   | ------------------------- | ---------------------------------- |
   | `CENTRAL_PORTAL_USERNAME` | Central Portal token username      |
   | `CENTRAL_PORTAL_PASSWORD` | Central Portal token password      |
   | `GPG_PRIVATE_KEY`         | Base64-encoded armored private key |
   | `GPG_PASSPHRASE`          | GPG key passphrase                 |

The Maven workflow activates the `central-release` profile. That profile signs
the artifacts and uploads them to the Central Publisher Portal. Normal Maven
builds do not need these secrets.

### PyPI

Configure a Trusted Publisher for each project (`openlinktoken` and
`openlinktoken-pyspark`) on PyPI:

| PyPI field  | Value                |
| ----------- | -------------------- |
| Owner       | `TruvetaPublic`      |
| Repository  | `OpenLinkToken`      |
| Workflow    | `python-publish.yml` |
| Environment | `pypi`               |

The workflow uses GitHub OIDC with `id-token: write`. Do not add a `PYPI_TOKEN`
secret; this repository uses Trusted Publishing.

### Docker and CLI

The Docker workflow pushes signed images to `ghcr.io/TruvetaPublic/OpenLinkToken`
and uses GitHub's token plus Sigstore. The CLI workflow uploads platform
archives and SHA-256 sidecars to the GitHub release. Neither workflow needs a
long-lived publishing token.

## Release triggers

The Maven, Python, and Docker workflows run for:

- a GitHub release `created` or `published` event;
- a successful `Create Release on Merge` workflow run;
- a manual `workflow_dispatch` run with an optional version input.

The CLI build workflow also runs on pushes to `main`. A pull request triggers a
Docker validation build without publishing.

The release process that creates the tag and GitHub release is documented in
[Branch and release workflow](./branch-workflow-and-release-process.md).

## Manual publishing

1. Open the repository's **Actions** tab.
2. Select **Maven Package**, **Python Package**, **Docker Publish**, or
   **Build Open Link Token CLI**.
3. Choose **Run workflow** and provide the version when the workflow asks for
   it.

The reusable `release-context.yml` workflow resolves the version and `vX.Y.Z`
tag. Release assets are attached only when the matching GitHub release exists;
Maven, PyPI, and GHCR publication still follows the selected workflow.

## Troubleshooting

### Maven Central returns `401 Unauthorized`

Use a Central Portal user token, not legacy OSSRH credentials. Confirm the
`CENTRAL_PORTAL_USERNAME` and `CENTRAL_PORTAL_PASSWORD` secrets are present.

### Maven Central rejects an artifact as unsigned

Confirm `GPG_PRIVATE_KEY`, `GPG_PASSPHRASE`, and the `central-release` profile.
The public key must also be available to Central.

### Maven namespace verification fails

Verify `org.openlinktoken` at
<https://central.sonatype.com/publishing/namespaces>.

### PyPI reports `invalid-publisher` or `403 Forbidden`

Check the owner, repository, workflow filename, and `pypi` environment name.
The publishing job must retain `id-token: write`.

### A release asset is missing

Check the workflow run and the release's **Assets** section. The Maven and CLI
workflows upload assets only when `release-context.yml` finds the matching
release.

### A Docker image is missing

Check the **Packages** section for the repository and confirm that the release
workflow completed successfully. The image is published to GHCR, not Docker
Hub.
