"""Integration tests for the POSIX CLI installer."""

import hashlib
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[6]
INSTALL_SCRIPT = REPOSITORY_ROOT / "install.sh"
MODEL_FILES = {
    "model.onnx": b"required model",
    "model.onnx.data": b"required model data",
    "tokenizer.json": b'{"fixture": true}',
}
ORAS_CHECKSUMS = {
    "oras_1.3.3_linux_amd64.tar.gz": "9ce999f8d2de03fc03968b29d743077a58783e545e5eaa53917ca177352d0e59",
    "oras_1.3.3_darwin_amd64.tar.gz": "aeb684d8c24c18dce28fd1f7326636e4782b573108e244a93d4b1c4a5ec50f48",
    "oras_1.3.3_darwin_arm64.tar.gz": "f33fc12753c54172b0d0d19eaa0318d3f90fe9b094d96e8b259c881713c92e1c",
    "oras_1.3.3_windows_amd64.zip": "30ca213a565a450de33001dae83053db53c221e6674c5233dc3406b686657969",
}


def _write_archive(path: Path, entries: dict[str, bytes]) -> None:
    """Write a ZIP fixture containing the supplied files."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)


def _write_checksum(path: Path) -> str:
    """Return the SHA-256 checksum for a fixture file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_oci_assets(assets_dir: Path) -> Path:
    """Create the ML1 files served by the fake ORAS command."""
    oci_dir = assets_dir / "oci"
    oci_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "assets": {
            filename: {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
            for filename, content in MODEL_FILES.items()
        }
    }
    for filename, content in MODEL_FILES.items():
        (oci_dir / filename).write_bytes(content)
    (oci_dir / "asset-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return oci_dir


def _installer_environment(tmp_path: Path, assets_dir: Path, model_assets_dir: Path) -> dict[str, str]:
    """Create isolated fake curl, ORAS, tar, and uname commands for installer tests."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "curl").write_text(
        """#!/bin/bash
set -euo pipefail
output=""
url=""
while (($# > 0)); do
    case "$1" in
        -o|--output|-H|--retry)
            if [[ "$1" == "-o" || "$1" == "--output" ]]; then
                output="$2"
            fi
            shift 2
            ;;
        -*)
            shift
            ;;
        *)
            url="$1"
            shift
            ;;
    esac
done
if [[ "$url" == */releases/latest ]]; then
    printf '{"tag_name":"v1.0.0"}'
    exit 0
fi
asset="${url##*/}"
source_file="$TEST_ASSETS/$asset"
[[ -f "$source_file" ]] || exit 22
if [[ -n "$output" ]]; then
    cp "$source_file" "$output"
else
    cat "$source_file"
fi
""",
        encoding="utf-8",
    )
    (bin_dir / "uname").write_text(
        """#!/bin/bash
set -euo pipefail
case "$1" in
    -s) printf '%s\\n' "${TEST_UNAME_S:-Linux}" ;;
    -m) printf '%s\\n' "${TEST_UNAME_M:-x86_64}" ;;
    *) exit 1 ;;
esac
""",
        encoding="utf-8",
    )
    (bin_dir / "tar").write_text(
        """#!/bin/bash
set -euo pipefail
destination=""
while (($# > 0)); do
    if [[ "$1" == "-C" ]]; then
        destination="$2"
        shift 2
    else
        shift
    fi
done
mkdir -p "$destination"
cat > "$destination/oras" <<'ORAS'
#!/bin/bash
set -euo pipefail
[[ "$1" == "pull" ]] || exit 2
reference="$2"
[[ "${TEST_ORAS_FAIL:-}" != "1" ]] || exit 1
destination=""
while (($# > 0)); do
    if [[ "$1" == "--output" ]]; then
        destination="$2"
        shift 2
    else
        shift
    fi
done
cp "$TEST_MODEL_ASSETS"/* "$destination/"
if [[ "${TEST_ORAS_CORRUPT:-}" == "1" ]]; then
    printf 'corrupt model' > "$destination/model.onnx"
fi
printf '%s' "$reference" > "$TEST_ORAS_REFERENCE_FILE"
ORAS
chmod +x "$destination/oras"
""",
        encoding="utf-8",
    )
    (bin_dir / "sha256sum").write_text(
        """#!/usr/bin/env python3
import hashlib
import os
import sys

path = sys.argv[1]
name = os.path.basename(path)
checksums = {
"""
        + "".join(f'    "{name}": "{digest}",\n' for name, digest in ORAS_CHECKSUMS.items())
        + """}
if name in checksums:
    print(f"{checksums[name]}  {path}")
else:
    digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
    print(f"{digest}  {path}")
""",
        encoding="utf-8",
    )
    for command in ("curl", "uname", "tar", "sha256sum"):
        (bin_dir / command).chmod(0o755)

    for archive_name in ORAS_CHECKSUMS:
        (assets_dir / archive_name).write_bytes(b"fake ORAS archive")
    return {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "HOME": str(tmp_path / "home"),
        "TEST_ASSETS": str(assets_dir),
        "TEST_MODEL_ASSETS": str(model_assets_dir),
        "TEST_ORAS_REFERENCE_FILE": str(tmp_path / "oras-reference"),
    }


def _create_release_assets(
    assets_dir: Path,
    include_cuda: bool,
    include_legacy_payloads: bool = False,
    platform: str = "linux-x64",
) -> None:
    """Create a minimal CLI release with optional legacy and CUDA assets."""
    asset_name = f"olt-cli-1.0.0-{platform}.zip"
    bundle_prefix = asset_name.removesuffix(".zip")
    executable = "olt.exe" if platform == "windows-x64" else "olt"
    entries = {f"{bundle_prefix}/{executable}": b"executable", f"{bundle_prefix}/_internal/runtime": b"cpu"}
    if include_legacy_payloads:
        entries.update(
            {
                f"{bundle_prefix}/_internal/openlinktoken/core/ai/tokens/{name}": content
                for name, content in _write_fixture_model_files().items()
            }
        )
        entries[f"{bundle_prefix}/_internal/nvidia/cublas/lib/libcuda.so"] = b"cuda"
    archive = assets_dir / asset_name
    _write_archive(archive, entries)
    (assets_dir / f"{asset_name}.sha256").write_text(
        f"{_write_checksum(archive)}  {asset_name}\n",
        encoding="utf-8",
    )
    if include_cuda:
        part_name = "olt-cuda-1.0.0-linux-x64-part-001.zip"
        part = assets_dir / part_name
        _write_archive(part, {"nvidia/cublas/lib/libcuda.so": b"cuda"})
        (assets_dir / "olt-cuda-1.0.0-linux-x64.manifest").write_text(
            f"{_write_checksum(part)}\t{part_name}\n",
            encoding="utf-8",
        )


def _write_fixture_model_files() -> dict[str, bytes]:
    """Return all files needed by a self-contained CLI archive."""
    model_files = dict(MODEL_FILES)
    model_files["asset-manifest.json"] = json.dumps(
        {
            "assets": {
                filename: {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
                for filename, content in MODEL_FILES.items()
            }
        },
        indent=2,
    ).encode()
    return model_files


def _run_installer(tmp_path: Path, assets_dir: Path, *arguments: str, **environment_updates: str):
    """Run install.sh with deterministic fake downloads and platform details."""
    model_assets_dir = _write_oci_assets(assets_dir)
    environment = _installer_environment(tmp_path, assets_dir, model_assets_dir)
    environment.update(environment_updates)
    return subprocess.run(
        ["bash", str(INSTALL_SCRIPT), "--version", "1.0.0", *arguments],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    ), environment


def test_installs_oci_model_assets_and_cuda_by_default(tmp_path):
    """Linux installation pulls the default model tag and includes CUDA."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _create_release_assets(assets_dir, include_cuda=True)
    install_dir = tmp_path / "home" / ".local" / "bin"
    result, environment = _run_installer(tmp_path, assets_dir, "--install-dir", str(install_dir))

    assert result.returncode == 0, result.stderr
    model_dir = install_dir / ".olt" / "_internal" / "openlinktoken" / "core" / "ai" / "tokens"
    for filename, content in _write_fixture_model_files().items():
        assert (model_dir / filename).read_bytes() == content
    assert (
        Path(environment["TEST_ORAS_REFERENCE_FILE"]).read_text() == "ghcr.io/truvetapublic/openlinktoken-ml1-assets:v1"
    )
    assert (install_dir / ".olt" / "_internal" / "nvidia" / "cublas" / "lib" / "libcuda.so").read_bytes() == b"cuda"
    assert "Installing the NVIDIA CUDA runtime by default" in result.stdout


def test_model_tag_can_be_overridden_and_cuda_can_be_skipped(tmp_path):
    """The installer honors the requested model tag independently of the CLI version."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _create_release_assets(assets_dir, include_cuda=True)
    install_dir = tmp_path / "home" / ".local" / "bin"
    result, environment = _run_installer(
        tmp_path, assets_dir, "--install-dir", str(install_dir), "--model-tag", "v7", "--no-cuda"
    )

    assert result.returncode == 0, result.stderr
    assert Path(environment["TEST_ORAS_REFERENCE_FILE"]).read_text().endswith(":v7")
    assert not (install_dir / ".olt" / "_internal" / "nvidia").exists()
    assert "Installing the CPU-only runtime." in result.stdout


def test_rejects_invalid_model_tag(tmp_path):
    """Invalid model tags must be rejected before downloads or installation."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    model_assets_dir = _write_oci_assets(assets_dir)
    environment = _installer_environment(tmp_path, assets_dir, model_assets_dir)

    result = subprocess.run(
        ["bash", str(INSTALL_SCRIPT), "--version", "1.0.0", "--model-tag", "../latest"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Invalid ML1 model tag" in result.stderr


def test_keeps_existing_bundle_when_oci_pull_fails(tmp_path):
    """An unavailable OCI artifact must not replace an existing installation."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _create_release_assets(assets_dir, include_cuda=False)
    install_dir = tmp_path / "home" / ".local" / "bin"
    existing_bundle = install_dir / ".olt"
    existing_bundle.mkdir(parents=True)
    (existing_bundle / "marker").write_text("old", encoding="utf-8")
    result, _ = _run_installer(tmp_path, assets_dir, "--install-dir", str(install_dir), TEST_ORAS_FAIL="1")

    assert result.returncode != 0
    assert "Unable to pull ML1 model assets" in result.stderr
    assert (existing_bundle / "marker").read_text(encoding="utf-8") == "old"


def test_keeps_existing_bundle_when_oci_asset_checksum_fails(tmp_path):
    """Model assets that disagree with the OCI manifest must not be installed."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _create_release_assets(assets_dir, include_cuda=False)
    install_dir = tmp_path / "home" / ".local" / "bin"
    existing_bundle = install_dir / ".olt"
    existing_bundle.mkdir(parents=True)
    (existing_bundle / "marker").write_text("old", encoding="utf-8")
    result, _ = _run_installer(tmp_path, assets_dir, "--install-dir", str(install_dir), TEST_ORAS_CORRUPT="1")

    assert result.returncode != 0
    assert "SHA-256 verification failed" in result.stderr
    assert (existing_bundle / "marker").read_text(encoding="utf-8") == "old"


def test_legacy_self_contained_archive_does_not_require_oci(tmp_path):
    """Older ZIPs with all four model files remain installable without an OCI pull."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _create_release_assets(assets_dir, include_cuda=False, include_legacy_payloads=True)
    install_dir = tmp_path / "home" / ".local" / "bin"
    result, environment = _run_installer(tmp_path, assets_dir, "--install-dir", str(install_dir), "--no-cuda")

    assert result.returncode == 0, result.stderr
    installed_bundle = install_dir / ".olt" / "_internal"
    for filename, content in _write_fixture_model_files().items():
        assert (installed_bundle / "openlinktoken/core/ai/tokens" / filename).read_bytes() == content
    assert not Path(environment["TEST_ORAS_REFERENCE_FILE"]).exists()
    assert "already included in the CLI archive" in result.stdout


def test_keeps_existing_bundle_when_cuda_download_fails(tmp_path):
    """A failed CUDA download must not replace a previously installed bundle."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _create_release_assets(assets_dir, include_cuda=False)
    install_dir = tmp_path / "home" / ".local" / "bin"
    existing_bundle = install_dir / ".olt"
    existing_bundle.mkdir(parents=True)
    (existing_bundle / "marker").write_text("old", encoding="utf-8")
    result, _ = _run_installer(tmp_path, assets_dir, "--install-dir", str(install_dir))

    assert result.returncode != 0
    assert (existing_bundle / "marker").read_text(encoding="utf-8") == "old"


def test_keeps_existing_bundle_when_cuda_checksum_fails(tmp_path):
    """A CUDA checksum mismatch must fail before replacing the installed bundle."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _create_release_assets(assets_dir, include_cuda=True)
    manifest = assets_dir / "olt-cuda-1.0.0-linux-x64.manifest"
    part_name = "olt-cuda-1.0.0-linux-x64-part-001.zip"
    manifest.write_text(f"{'0' * 64}\t{part_name}\n", encoding="utf-8")
    install_dir = tmp_path / "home" / ".local" / "bin"
    existing_bundle = install_dir / ".olt"
    existing_bundle.mkdir(parents=True)
    (existing_bundle / "marker").write_text("old", encoding="utf-8")
    result, _ = _run_installer(tmp_path, assets_dir, "--install-dir", str(install_dir))

    assert result.returncode != 0
    assert "SHA-256 verification failed" in result.stderr
    assert (existing_bundle / "marker").read_text(encoding="utf-8") == "old"


@pytest.mark.parametrize(
    ("system", "machine", "archive_name"),
    [
        ("Darwin", "x86_64", "oras_1.3.3_darwin_amd64.tar.gz"),
        ("Darwin", "arm64", "oras_1.3.3_darwin_arm64.tar.gz"),
    ],
)
def test_selects_the_matching_macos_oras_archive(tmp_path, system, machine, archive_name):
    """macOS installer selects the pinned ORAS archive for the host architecture."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _create_release_assets(assets_dir, include_cuda=False, platform=f"macos-{machine}")
    result, environment = _run_installer(
        tmp_path,
        assets_dir,
        "--install-dir",
        str(tmp_path / "installed"),
        TEST_UNAME_S=system,
        TEST_UNAME_M=machine,
    )

    assert result.returncode == 0, result.stderr
    assert Path(environment["TEST_ORAS_REFERENCE_FILE"]).read_text().endswith(":v1")
    assert (assets_dir / archive_name).exists()


def test_windows_installer_keeps_legacy_self_contained_archives(tmp_path):
    """Windows installer continues to install older archives with embedded ML1 files."""
    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell is not installed")

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _create_release_assets(
        assets_dir,
        include_cuda=False,
        include_legacy_payloads=True,
        platform="windows-x64",
    )
    install_dir = tmp_path / "installed"
    environment = {
        **os.environ,
        "TEST_ASSETS": str(assets_dir),
        "TEST_INSTALLER": str(REPOSITORY_ROOT / "install.ps1"),
        "TEST_INSTALL_DIR": str(install_dir),
        "PROCESSOR_ARCHITECTURE": "AMD64",
    }
    command = r"""
function Invoke-WebRequest {
    param([string]$Uri, [string]$OutFile, [hashtable]$Headers)
    $asset = [System.IO.Path]::GetFileName(([System.Uri]$Uri).AbsolutePath)
    Copy-Item -LiteralPath (Join-Path $env:TEST_ASSETS $asset) -Destination $OutFile
}
& $env:TEST_INSTALLER -Version 1.0.0 -InstallDir $env:TEST_INSTALL_DIR
"""

    result = subprocess.run(
        [pwsh, "-NoProfile", "-Command", command],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    model_dir = install_dir / "_internal" / "openlinktoken" / "core" / "ai" / "tokens"
    for filename, content in _write_fixture_model_files().items():
        assert (model_dir / filename).read_bytes() == content
