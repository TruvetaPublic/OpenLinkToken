"""Integration tests for the POSIX CLI installer."""

import hashlib
import os
import subprocess
import zipfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[6]
INSTALL_SCRIPT = REPOSITORY_ROOT / "install.sh"


def _write_archive(path: Path, entries: dict[str, bytes]) -> None:
    """Write a ZIP fixture containing the supplied files."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)


def _write_checksum(path: Path) -> str:
    """Return the SHA-256 checksum for a fixture file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _installer_environment(tmp_path: Path, assets_dir: Path) -> dict[str, str]:
    """Create isolated fake curl and uname commands for installer tests."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl = bin_dir / "curl"
    curl.write_text(
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
    curl.chmod(0o755)
    uname = bin_dir / "uname"
    uname.write_text(
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
    uname.chmod(0o755)
    return {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "HOME": str(tmp_path / "home"),
        "TEST_ASSETS": str(assets_dir),
    }


def _create_release_assets(assets_dir: Path, include_cuda: bool, include_legacy_payloads: bool = False) -> None:
    """Create a minimal Linux release with model data and an optional CUDA part."""
    asset_name = "olt-cli-1.0.0-linux-x64.zip"
    bundle_prefix = "olt-cli-1.0.0-linux-x64"
    base_archive = assets_dir / asset_name
    entries = {f"{bundle_prefix}/olt": b"executable", f"{bundle_prefix}/_internal/runtime": b"cpu"}
    if include_legacy_payloads:
        entries.update(
            {
                f"{bundle_prefix}/_internal/openlinktoken/core/ai/tokens/model.onnx.data": b"required model data",
                f"{bundle_prefix}/_internal/nvidia/cublas/lib/libcuda.so": b"cuda",
            }
        )
    _write_archive(base_archive, entries)
    (assets_dir / f"{asset_name}.sha256").write_text(
        f"{_write_checksum(base_archive)}  {asset_name}\n",
        encoding="utf-8",
    )
    if not include_legacy_payloads:
        model_data = b"required model data"
        model_part_name = "olt-model-1.0.0-linux-x64-part-001.bin"
        (assets_dir / model_part_name).write_bytes(model_data)
        model_manifest = assets_dir / "olt-model-1.0.0-linux-x64.manifest"
        model_manifest.write_text(
            f"sha256\t{hashlib.sha256(model_data).hexdigest()}\n"
            f"part\t{_write_checksum(assets_dir / model_part_name)}\t{model_part_name}\n",
            encoding="utf-8",
        )
    if include_cuda:
        part_name = "olt-cuda-1.0.0-linux-x64-part-001.zip"
        part = assets_dir / part_name
        _write_archive(part, {"nvidia/cublas/lib/libcuda.so": b"cuda"})
        manifest = assets_dir / "olt-cuda-1.0.0-linux-x64.manifest"
        manifest.write_text(f"{_write_checksum(part)}\t{part_name}\n", encoding="utf-8")


def test_install_script_installs_cuda_bundle_by_default(tmp_path):
    """Default Linux installation should include the NVIDIA runtime."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _create_release_assets(assets_dir, include_cuda=True)
    install_dir = tmp_path / "home" / ".local" / "bin"
    environment = _installer_environment(tmp_path, assets_dir)

    result = subprocess.run(
        ["bash", str(INSTALL_SCRIPT), "--version", "1.0.0", "--install-dir", str(install_dir)],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (install_dir / ".olt" / "_internal" / "runtime").read_bytes() == b"cpu"
    assert (
        install_dir / ".olt" / "_internal" / "openlinktoken" / "core" / "ai" / "tokens" / "model.onnx.data"
    ).read_bytes() == b"required model data"
    assert (install_dir / ".olt" / "_internal" / "nvidia" / "cublas" / "lib" / "libcuda.so").read_bytes() == b"cuda"
    assert "Installing the NVIDIA CUDA runtime by default" in result.stdout


def test_install_script_no_cuda_skips_optional_libraries(tmp_path):
    """The no-cuda flag should install only the CPU-capable bundle."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _create_release_assets(assets_dir, include_cuda=True)
    install_dir = tmp_path / "home" / ".local" / "bin"
    environment = _installer_environment(tmp_path, assets_dir)

    result = subprocess.run(
        ["bash", str(INSTALL_SCRIPT), "--version", "1.0.0", "--install-dir", str(install_dir), "--no-cuda"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (
        install_dir / ".olt" / "_internal" / "openlinktoken" / "core" / "ai" / "tokens" / "model.onnx.data"
    ).read_bytes() == b"required model data"
    assert not (install_dir / ".olt" / "_internal" / "nvidia").exists()
    assert "Installing the CPU-only runtime." in result.stdout


def test_install_script_supports_legacy_linux_archives(tmp_path):
    """Older Linux archives with embedded model and CUDA files need no split assets."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _create_release_assets(assets_dir, include_cuda=False, include_legacy_payloads=True)
    install_dir = tmp_path / "home" / ".local" / "bin"
    environment = _installer_environment(tmp_path, assets_dir)

    result = subprocess.run(
        ["bash", str(INSTALL_SCRIPT), "--version", "1.0.0", "--install-dir", str(install_dir)],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    installed_bundle = install_dir / ".olt" / "_internal"
    assert (installed_bundle / "openlinktoken/core/ai/tokens/model.onnx.data").read_bytes() == b"required model data"
    assert (installed_bundle / "nvidia/cublas/lib/libcuda.so").read_bytes() == b"cuda"
    assert "already included in the CLI archive" in result.stdout


def test_install_script_keeps_existing_bundle_when_cuda_download_fails(tmp_path):
    """A failed optional download must not replace a previously installed bundle."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _create_release_assets(assets_dir, include_cuda=False)
    part_name = "olt-cuda-1.0.0-linux-x64-part-001.zip"
    manifest = assets_dir / "olt-cuda-1.0.0-linux-x64.manifest"
    manifest.write_text(f"{'a' * 64}\t{part_name}\n", encoding="utf-8")
    install_dir = tmp_path / "home" / ".local" / "bin"
    existing_bundle = install_dir / ".olt"
    existing_bundle.mkdir(parents=True)
    (existing_bundle / "marker").write_text("old", encoding="utf-8")
    environment = _installer_environment(tmp_path, assets_dir)

    result = subprocess.run(
        ["bash", str(INSTALL_SCRIPT), "--version", "1.0.0", "--install-dir", str(install_dir)],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert (existing_bundle / "marker").read_text(encoding="utf-8") == "old"


def test_install_script_keeps_existing_bundle_when_cuda_checksum_fails(tmp_path):
    """A checksum mismatch must fail before replacing the installed bundle."""
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
    environment = _installer_environment(tmp_path, assets_dir)

    result = subprocess.run(
        ["bash", str(INSTALL_SCRIPT), "--version", "1.0.0", "--install-dir", str(install_dir)],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "SHA-256 verification failed" in result.stderr
    assert (existing_bundle / "marker").read_text(encoding="utf-8") == "old"


def test_install_script_keeps_existing_bundle_when_model_checksum_fails(tmp_path):
    """Invalid model data must fail before replacing a previously installed bundle."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    _create_release_assets(assets_dir, include_cuda=False)
    model_manifest = assets_dir / "olt-model-1.0.0-linux-x64.manifest"
    model_part_name = "olt-model-1.0.0-linux-x64-part-001.bin"
    model_manifest.write_text(
        f"sha256\t{'0' * 64}\npart\t{'0' * 64}\t{model_part_name}\n",
        encoding="utf-8",
    )
    install_dir = tmp_path / "home" / ".local" / "bin"
    existing_bundle = install_dir / ".olt"
    existing_bundle.mkdir(parents=True)
    (existing_bundle / "marker").write_text("old", encoding="utf-8")
    environment = _installer_environment(tmp_path, assets_dir)

    result = subprocess.run(
        ["bash", str(INSTALL_SCRIPT), "--version", "1.0.0", "--install-dir", str(install_dir), "--no-cuda"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "SHA-256 verification failed" in result.stderr
    assert (existing_bundle / "marker").read_text(encoding="utf-8") == "old"


def test_install_script_no_cuda_is_harmless_on_macos(tmp_path):
    """The Linux-specific no-cuda option should be harmless on macOS."""
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    asset_name = "olt-cli-1.0.0-macos-x86_64.zip"
    archive = assets_dir / asset_name
    _write_archive(
        archive,
        {"olt-cli-1.0.0-macos-x86_64/olt": b"executable", "olt-cli-1.0.0-macos-x86_64/_internal/runtime": b"cpu"},
    )
    (assets_dir / f"{asset_name}.sha256").write_text(
        f"{_write_checksum(archive)}  {asset_name}\n",
        encoding="utf-8",
    )
    environment = _installer_environment(tmp_path, assets_dir)
    environment["TEST_UNAME_S"] = "Darwin"

    result = subprocess.run(
        ["bash", str(INSTALL_SCRIPT), "--version", "1.0.0", "--no-cuda"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Installing the CPU-only runtime." in result.stdout
