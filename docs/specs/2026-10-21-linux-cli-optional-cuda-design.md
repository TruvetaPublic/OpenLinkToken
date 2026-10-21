# Linux CLI optional CUDA packaging design

## Purpose and constraints

The standalone Linux CLI currently ships NVIDIA CUDA runtime libraries inside
its default PyInstaller bundle. The resulting release ZIP is about 4.45 GB,
which exceeds GitHub's release-asset limit and the current upload step's
in-memory file limit. Release v2.2.0 and v2.2.1 both exhibit this failure.

The default Linux install should include the CUDA runtime while keeping each
asset small enough to publish as a GitHub release asset. Linux x86_64 users who
do not need GPU inference should be able to skip the runtime. The change
targets `release/2.2.1`; it must not update `main` or rewrite an existing tag.

## Design

Keep the existing PyInstaller build and divide its Linux output at release asset
preparation:

- The default Linux ZIP contains the executable and all non-NVIDIA runtime
  files. The existing ONNX Runtime CPU provider and CPU fallback remain
  available.
- NVIDIA runtime libraries currently collected under the PyInstaller
  `_internal/nvidia` tree are omitted from the default ZIP. Package them into
  deterministic, independently extractable ZIP parts. Preserve their paths
  relative to `_internal` so extraction overlays the same paths used by the
  current frozen runtime.
- Target 500 MiB of uncompressed input per CUDA part, with a hard 512 MiB cap,
  and fail asset generation if one file cannot fit. Generate a manifest listing
  each part and its SHA-256 digest. Reject any generated release asset above a 1.5 GiB upload
  guard, leaving margin below GitHub's 2 GiB asset limit and avoiding large
  Node.js buffers.
- Keep non-Linux release assets unchanged. The existing Linux standalone
  executable asset and its checksum remain unchanged.

The uploader continues to use the existing GitHub API flow, but checks each
asset's size before reading it. CUDA parts are bounded at 512 MiB; an oversized
asset fails with a clear error before memory buffering or upload.

## Installer behavior

Extend `install.sh` so Linux x86_64 installs CUDA by default. `--no-cuda` skips
the runtime download and installs only the CPU-capable default ZIP. Otherwise,
the installer downloads every CUDA part listed in the versioned release
manifest, verifies each part's SHA-256 before extracting it, and overlays its
files into the staged bundle's `_internal` directory.

The installer must finish all downloads, integrity checks, and extraction
before swapping the staged bundle into the install location. A missing
manifest/part, checksum mismatch, unsupported platform, or extraction error
fails explicitly and leaves the previously installed bundle intact. The
installer does not require Python or `jq`; use shell utilities already required
by the script. macOS remains CPU-only, and `--no-cuda` is accepted there as a
harmless no-op. CUDA execution still requires a compatible host NVIDIA driver;
runtime provider selection and CPU fallback behavior remain unchanged.

## Documentation and compatibility

Update the README's one-line install examples and hardware-acceleration note to
explain that Linux installs the NVIDIA runtime by default and `--no-cuda`
selects CPU-only inference. Keep the Windows installer and non-Linux packages
unchanged.

This changes only future release packaging and installer behavior. It does not
retroactively change already-published release assets or tags. Rebuilding
v2.2.1 requires a separate approved release-recovery action after this change
is merged into the release branch.

## Validation

- Unit-test asset preparation: default Linux ZIP excludes NVIDIA runtime files,
  CUDA parts preserve their original relative destinations, parts stay within
  the configured bound, and the manifest checksums match their contents.
- Unit-test installer behavior for default CUDA install, CPU-only opt-out,
  checksum/missing-part failures, non-Linux behavior, and preservation of an
  existing installation on failure.
- Verify the upload step rejects any file above its guard before reading it.
- Run the relevant Python CLI tests and shell syntax/install-script tests.
- Run the Linux PyInstaller build and smoke test; on a CUDA-capable runner,
  verify CUDA provider activation by default and CPU fallback with `--no-cuda`.
- Confirm each release asset is below GitHub's per-asset limit.

No new runtime dependency is planned.
