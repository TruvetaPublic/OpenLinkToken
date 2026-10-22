# OCI ML1 Model Distribution Design

## Goal

Keep the large ML1 model files out of standalone CLI release ZIPs and distribute
them through the repository's existing OCI artifact in GitHub Container Registry.
The Linux, macOS, and Windows installers will retrieve and verify those assets
while installing the CLI. The model version remains independent of the CLI
version.

The existing OCI artifact is published by
`.github/workflows/publish-ml1-assets.yml` with ORAS. Its documented reference is
`ghcr.io/truvetapublic/openlinktoken-ml1-assets:v1`. The registry currently
returns 404 for that package, so the first `v1` artifact must be published and
made public before installer pulls can succeed without authentication.

## Artifact Contents and Versioning

The OCI artifact is the single source of truth for these files:

- `model.onnx`
- `model.onnx.data`
- `tokenizer.json`
- `asset-manifest.json`

CLI ZIPs omit all four files on Linux, macOS, and Windows. Release asset
preparation no longer emits model parts or model manifests; CUDA remains a
separate Linux-only optional runtime distributed as it is today.

The installer reference defaults to the existing documented model tag `v1`.
`install.sh` accepts `--model-tag TAG`; `install.ps1` accepts `-ModelTag TAG`.
Model tags must match `vN`, are independent of the CLI release version, and are
immutable: the publish workflow must refuse to overwrite an existing model tag.
Publishing changed model assets requires a new `vN` tag.

## Installer Flow

1. Download, verify, and extract the CLI ZIP into a temporary staging area.
2. If all four ML1 files are already present in the ZIP, keep them. This
   preserves installation of older self-contained CLI releases.
3. Otherwise bootstrap ORAS 1.3.3 into the temporary directory, pull
   `ghcr.io/truvetapublic/openlinktoken-ml1-assets:<model-tag>`, and require all
   four expected files in the pull output.
4. Copy the OCI files beside the Python package's ML1 resources in the staged
   bundle.
5. Complete the existing staged installation swap only after the model pull
   succeeds. A failed ORAS download, OCI pull, or incomplete artifact must fail
   explicitly and leave any existing installation untouched.

The installers use platform-specific ORAS 1.3.3 archives from the official
`oras-project/oras` GitHub release and verify the binary archive against these
SHA-256 values before executing it:

| Platform            | ORAS archive                     | SHA-256                                                            |
| ------------------- | -------------------------------- | ------------------------------------------------------------------ |
| Linux x86_64        | `oras_1.3.3_linux_amd64.tar.gz`  | `9ce999f8d2de03fc03968b29d743077a58783e545e5eaa53917ca177352d0e59` |
| macOS Intel         | `oras_1.3.3_darwin_amd64.tar.gz` | `aeb684d8c24c18dce28fd1f7326636e4782b573108e244a93d4b1c4a5ec50f48` |
| macOS Apple Silicon | `oras_1.3.3_darwin_arm64.tar.gz` | `f33fc12753c54172b0d0d19eaa0318d3f90fe9b094d96e8b259c881713c92e1c` |
| Windows x86_64      | `oras_1.3.3_windows_amd64.zip`   | `30ca213a565a450de33001dae83053db53c221e6674c5233dc3406b686657969` |

Public GHCR pulls do not require credentials. Installers do not prompt for or
collect registry credentials; private OCI packages are unsupported by this
installer flow.

## Publishing and Visibility

Use the existing `Publish ML1 Assets` workflow to publish tag `v1`. The package
must be public for unauthenticated end-user installs. Update the publishing
guide to describe the installer-driven OCI pull, the optional model-tag
override, and the public-package requirement. Do not publish model files as
GitHub Release assets.

## Verification

- Release asset unit tests verify that all supported OS ZIPs omit all four ML1
  files and that no model parts/manifests are emitted.
- Installer tests use a fake ORAS executable/pull output to verify the default
  and overridden OCI reference, expected files copied into the staged bundle,
  checksum/OCI-pull failure behavior, and preservation of an existing install.
- Test legacy archives containing all four ML1 files to ensure no OCI pull is
  needed for those releases.
- The CLI build workflow checks the ZIP contents, validates the model assets
  from the OCI artifact, and runs the existing Linux CPU-only ML1 smoke test
  against the assembled bundle.
- Before final end-to-end validation, publish `v1`, set the GHCR package
  visibility to public, and run the release-artifact workflow across Linux,
  macOS, and Windows.
