# Publishing OpenLinkToken to Maven Central and PyPI

This guide documents the configuration required to publish OpenLinkToken artifacts to Maven Central (via the Sonatype Central Publisher Portal) and PyPI. It covers prerequisite accounts, repository secrets, Maven settings, and the automated GitHub Actions workflows that perform the actual publishing.

---

## Table of Contents

1. [Publishing Overview](#publishing-overview)
2. [Maven Central (Sonatype Central Publisher Portal)](#maven-central-sonatype-central-publisher-portal)
3. [PyPI — Python Package Index](#pypi--python-package-index)
4. [Publishing Triggers](#publishing-triggers)
5. [Manual Publishing](#manual-publishing)
6. [Troubleshooting](#troubleshooting)

---

## Publishing Overview

OpenLinkToken artifacts are published to two primary registries via GitHub Actions:

| Artifact                                     | Registry                                                   | Workflow                                                        |
| -------------------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------- |
| `openlinktoken` Java JAR + POM               | Maven Central (Central Publisher Portal) + GitHub Packages | [`maven-publish.yml`](../.github/workflows/maven-publish.yml)   |
| `openlinktoken` Python wheel + sdist         | PyPI                                                       | [`python-publish.yml`](../.github/workflows/python-publish.yml) |
| `openlinktoken-pyspark` Python wheel + sdist | PyPI                                                       | [`python-publish.yml`](../.github/workflows/python-publish.yml) |

Both registries use **short-lived, workload-identity-based authentication** rather than long-lived static API tokens wherever the platform supports it:

- **PyPI** uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) — GitHub Actions authenticates via OpenID Connect (OIDC); there is no PyPI API token stored as a secret.
- **Maven Central** (via the Central Publisher Portal) still requires a Portal **user token** (username/password pair) plus a **GPG signing key**, since the Portal does not yet support OIDC. These are stored as repository secrets.

### Prerequisites Checklist

| Item                                                  | Required For                                                     | How to Configure                                                                                                                                                                                                                                                                       |
| ----------------------------------------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PyPI Trusted Publisher entry                          | PyPI publishing (`openlinktoken`, `openlinktoken-pyspark`)       | Configure on [pypi.org](https://pypi.org) per-project — **no GitHub secret needed**. See [PyPI section](#pypi--python-package-index) below.                                                                                                                                            |
| `CENTRAL_PORTAL_USERNAME` / `CENTRAL_PORTAL_PASSWORD` | Maven Central publishing                                         | Generate a [Central Portal user token](https://central.sonatype.com/account) and add both values as [repository secrets](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enforcing-secure-settings/managing-secrets-for-your-dependency-stack) |
| `GPG_PRIVATE_KEY` / `GPG_PASSPHRASE`                  | Maven Central publishing (artifact signing, required by Central) | Generate a GPG key pair and add the base64-encoded armored private key and its passphrase as repository secrets. See [Maven Central section](#maven-central-sonatype-central-publisher-portal) below.                                                                                  |

---

## Maven Central (Sonatype Central Publisher Portal)

### 1. Create a Central Publisher Portal Account and Namespace

1. Register at [central.sonatype.com](https://central.sonatype.com/) (if you do not already have an account — existing OSSRH/JIRA accounts can sign in with the same credentials).
2. Go to **Namespaces** and verify ownership of the `org.openlinktoken` namespace (via a DNS TXT record or GitHub repository verification, per the Portal's instructions).
3. Once verified, you can publish any artifact under the `org.openlinktoken` group ID.

### 2. Generate a Portal User Token

1. Go to [central.sonatype.com/account](https://central.sonatype.com/account).
2. Click **Generate User Token**.
3. **Copy the username and password immediately** — the password is only shown once.

> Legacy OSSRH JIRA credentials (`issues.sonatype.org`) **do not work** against the Portal — publishing with them returns `401 Unauthorized`. You must generate a new Portal user token.

### 3. Generate a GPG Signing Key

Maven Central requires every release artifact (JAR, POM, sources jar, javadoc jar) to be signed with GPG.

```bash
# Generate a new key (use a real name/email; a passphrase is strongly recommended)
gpg --full-generate-key

# List keys to get the key ID
gpg --list-secret-keys --keyid-format LONG

# Publish the public key so Central can verify signatures
gpg --keyserver keyserver.ubuntu.com --send-keys <KEY_ID>

# Export the private key for use in CI (base64-encode so it survives as a GitHub secret)
gpg --export-secret-keys --armor <KEY_ID> | base64 -w0 > gpg-private-key.b64
```

### 4. Add Repository Secrets

Navigate to **Settings → Secrets and variables → Actions** in your GitHub repository. Add:

| Secret Name               | Value                                              |
| ------------------------- | -------------------------------------------------- |
| `CENTRAL_PORTAL_USERNAME` | The Portal user token **username** from step 2     |
| `CENTRAL_PORTAL_PASSWORD` | The Portal user token **password** from step 2     |
| `GPG_PRIVATE_KEY`         | Contents of `gpg-private-key.b64` from step 3      |
| `GPG_PASSPHRASE`          | The passphrase you set when generating the GPG key |

### 5. How Authentication Is Wired Up in CI

[`setup-toolchain/action.yml`](../.github/actions/setup-toolchain/action.yml) accepts `central-username`, `central-password`, `gpg-private-key`, and `gpg-passphrase` inputs. When Maven publishing needs them, `maven-publish.yml` passes the secrets in as inputs:

```yaml
- name: Setup toolchain (Java)
  uses: ./.github/actions/setup-toolchain
  with:
    enable-java: true
    enable-python: false
    central-username: ${{ secrets.CENTRAL_PORTAL_USERNAME }}
    central-password: ${{ secrets.CENTRAL_PORTAL_PASSWORD }}
    gpg-private-key: ${{ secrets.GPG_PRIVATE_KEY }}
    gpg-passphrase: ${{ secrets.GPG_PASSPHRASE }}
```

The composite action then:

1. Lets `actions/setup-java@v4` generate `settings.xml` with the `github` server entry (for GitHub Packages).
2. Inserts a `central` server entry (Portal user token) and a `gpg.passphrase` server entry into that same `settings.xml`, referencing environment variables that are supplied at `mvn deploy` time (never written to disk in plaintext).
3. Imports the GPG private key into the runner's keyring with `gpg --batch --import` and records its full fingerprint as `MAVEN_GPG_KEYNAME`, so Maven signs with the imported key explicitly instead of relying on GPG's default-key selection.

The publish step in `maven-publish.yml` then runs:

```yaml
- name: Publish to Maven Central
  run: |
    cd lib/java
    mvn deploy -s "$GITHUB_WORKSPACE/settings.xml" -Pcentral-release -Dmaven.test.skip=true -B --file pom.xml
  env:
    CENTRAL_PORTAL_USERNAME: ${{ secrets.CENTRAL_PORTAL_USERNAME }}
    CENTRAL_PORTAL_PASSWORD: ${{ secrets.CENTRAL_PORTAL_PASSWORD }}
    GPG_PASSPHRASE: ${{ secrets.GPG_PASSPHRASE }}
```

The `-Pcentral-release` profile (defined in [`lib/java/pom.xml`](../lib/java/pom.xml)) activates the `central-publishing-maven-plugin`, attaches sources/javadoc jars, and signs all artifacts with `maven-gpg-plugin` — all scoped to this profile so a normal `mvn package`/`mvn deploy` (e.g. the separate "Publish to GitHub Packages Apache Maven" step) never requires a GPG key or Portal credentials.

### 6. POM Configuration

```xml
<distributionManagement>
    <repository>
        <id>github</id>
        <name>GitHub Packages</name>
        <url>https://maven.pkg.github.com/TruvetaPublic/OpenLinkToken</url>
    </repository>
    <snapshotRepository>
        <id>central</id>
        <name>Central Portal Snapshot Repository</name>
        <url>https://central.sonatype.com/repository/maven-snapshots/</url>
    </snapshotRepository>
</distributionManagement>
```

Note that Maven Central **releases** are not deployed via `distributionManagement` at all — the `central-publishing-maven-plugin` bundles and uploads artifacts directly to the Portal API when the `central-release` profile is active.

---

## PyPI — Python Package Index

OpenLinkToken publishes to PyPI using **Trusted Publishing (OIDC)** — there is no PyPI API token stored anywhere in this repository. GitHub Actions presents a short-lived OIDC identity token scoped to this repository and workflow, and PyPI exchanges it for a temporary upload credential.

### 1. Register a Trusted Publisher on PyPI

This must be configured **once per PyPI project** (`openlinktoken` and `openlinktoken-pyspark` each need their own entry):

1. Sign in at [pypi.org](https://pypi.org/) and go to the project's **Settings → Publishing** page (for a brand-new project that hasn't been published yet, use [pypi.org/manage/account/publishing](https://pypi.org/manage/account/publishing/) to pre-register a "pending" trusted publisher instead).
2. Click **Add a new publisher** and choose **GitHub**.
3. Fill in:

   | Field             | Value                                                |
   | ----------------- | ---------------------------------------------------- |
   | PyPI Project Name | `openlinktoken` (repeat for `openlinktoken-pyspark`) |
   | Owner             | `TruvetaPublic`                                      |
   | Repository name   | `OpenLinkToken`                                      |
   | Workflow name     | `python-publish.yml`                                 |
   | Environment name  | `pypi`                                               |

4. Save. No secret or token is generated or copied — PyPI now trusts OIDC tokens minted by this repository's `python-publish.yml` workflow when it runs under the `pypi` GitHub Environment.

### 2. How Authentication Is Wired Up in CI

The `publish_to_pypi` job in [`python-publish.yml`](../.github/workflows/python-publish.yml) declares:

```yaml
publish_to_pypi:
  needs: [release-info, build_and_test]
  runs-on: ubuntu-latest
  environment: pypi
  permissions:
    id-token: write # required for PyPI Trusted Publishing (OIDC) — no API token needed
    contents: read
  steps:
    - name: Download Python artifacts
      uses: actions/download-artifact@v4
      with:
        name: python-packages-${{ needs.release-info.outputs['tag'] }}
        path: dist_temp

    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        packages-dir: dist_temp
```

`permissions: id-token: write` is what allows the job to request an OIDC token from GitHub's OIDC provider; `pypa/gh-action-pypi-publish` handles exchanging that token with PyPI automatically. There is no `password`, `user`, or token input to configure — adding one would be a sign something has regressed back to token-based auth.

### 3. Verify on PyPI

After publishing, verify the packages appear on PyPI:

- <https://pypi.org/project/openlinktoken/>
- <https://pypi.org/project/openlinktoken-pyspark/>

---

## Publishing Triggers

Both `maven-publish.yml` and `python-publish.yml` are triggered by any of the following events:

| Trigger                                 | Description                                                                        | Example                                                                                                                             |
| --------------------------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `release.created` / `release.published` | A GitHub Release is created or published                                           | After `auto-release.yml` creates tag `v2.0.0` and its release                                                                       |
| `workflow_run` (completed)              | The "Create Release on Merge" workflow (`auto-release.yml`) completes successfully | Merging a `release/2.0.0` → `main` PR triggers `auto-release.yml`, which in turn fires `maven-publish.yml` and `python-publish.yml` |
| `workflow_dispatch` (manual)            | A workflow manually triggered via the GitHub UI with a `version` input             | Clicking **Run workflow** in Actions tab                                                                                            |

### Trigger Chain

```
release/2.x.x BRANCH PR MERGED -> main
          |
          v
auto-release.yml (Create Release on Merge)
          v
    Creates GitHub Release tag v2.x.x
          v
maven-publish.yml + python-publish.yml (AUTOMATICALLY TRIGGERED)
          v
    Build -> Deploy -> Attach to Release
```

There is intentionally only **one** workflow per ecosystem watching for releases (`maven-publish.yml`, `python-publish.yml`). A tag-push-triggered `release.yml` workflow previously existed alongside `python-publish.yml` and would have double-published the same version to PyPI for every release; it has been removed in favor of this single trigger chain.

---

## Manual Publishing

To publish a specific version manually:

1. Navigate to **Actions → Maven Package** (or **Python Package**) in the GitHub UI.
2. Click **Run workflow**.
3. Select the `main` branch.
4. Enter the version string (e.g., `2.0.0`).
5. Click **Run workflow**.

The workflow will:

1. Check out the `main` branch.
2. Read the version from the `release-context.yml` shared workflow.
3. Build the package (`mvn package` for Maven; `uv build` for Python).
4. Deploy to Maven Central + GitHub Packages, or to PyPI.
5. Attach artifacts to the named release (Maven) or the workflow run (Python).

---

## Troubleshooting

### Maven deploy fails with "401 Unauthorized"

- Confirm `CENTRAL_PORTAL_USERNAME` / `CENTRAL_PORTAL_PASSWORD` are a **Central Portal user token** (from [central.sonatype.com/account](https://central.sonatype.com/account)), not a legacy OSSRH JIRA username/password — the old credentials are rejected by the Portal.
- Verify `settings.xml` contains a `<server><id>central</id>...</server>` block (added by `setup-toolchain/action.yml`).

### Maven deploy fails with "no signature" / "artifact not signed"

- Confirm `GPG_PRIVATE_KEY` (base64-encoded, armored) and `GPG_PASSPHRASE` are set — the Central Publisher Portal rejects unsigned releases.
- Confirm the `-Pcentral-release` profile is active on the deploy command; GPG signing only runs inside that profile.

### Maven deploy fails with "Namespace not verified"

- Verify the `org.openlinktoken` namespace ownership at [central.sonatype.com/publishing/namespaces](https://central.sonatype.com/publishing/namespaces).

### PyPI upload fails with "invalid-publisher" or "no matching trusted publisher"

- Re-check the Trusted Publisher entry on pypi.org: Owner (`TruvetaPublic`), Repository (`OpenLinkToken`), Workflow filename (`python-publish.yml`), and Environment name (`pypi`) must match exactly, including the environment the `publish_to_pypi` job declares.
- Confirm the job has `permissions: id-token: write` — without it, no OIDC token is requested and the publish step fails before it even reaches PyPI.

### PyPI upload returns `403 Forbidden`

- This is expected if a Trusted Publisher has not been registered for the project yet, or was registered with mismatched repository/workflow/environment values — see above.
- OpenLinkToken does not use a `PYPI_TOKEN` secret; if you see references to one, treat it as stale/incorrect documentation.

### Artifacts not appearing in Maven Central after `mvn deploy -Pcentral-release`

With `autoPublish: true` configured on `central-publishing-maven-plugin`, a successful `mvn deploy` publishes automatically once validation passes. If it doesn't appear:

1. Navigate to [central.sonatype.com/publishing/deployments](https://central.sonatype.com/publishing/deployments).
2. Check the deployment's validation status — failed validation (e.g., missing sources/javadoc jar, missing signature, invalid POM metadata) blocks publishing.
3. The artifact typically appears on Maven Central within 10–30 minutes after a successful publish.

### Artifacts not appearing in GitHub Packages

- Check that the workflow ran successfully (`Actions → Maven Package`).
- Verify the `GITHUB_TOKEN` permission includes `packages: write`.
- Browse to <https://github.com/TruvetaPublic/OpenLinkToken/packages> to verify.
