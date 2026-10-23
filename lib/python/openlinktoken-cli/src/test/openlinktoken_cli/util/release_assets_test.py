# SPDX-License-Identifier: MIT

import hashlib
import zipfile
from pathlib import Path

import pytest

from openlinktoken_cli.util import release_assets
from openlinktoken_cli.util.release_assets import create_release_assets


def _write_binary(dist_dir: Path, name: str, content: bytes) -> None:
    """Create a fake built CLI executable for release asset tests."""
    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / name).write_bytes(content)


def _write_model_assets(bundle_dir: Path, model_data: bytes) -> tuple[Path, Path]:
    """Create the ML1 files in the bundle location used by CLI builds."""
    model_root = bundle_dir / "openlinktoken" / "core" / "ai" / "tokens"
    model_root.mkdir(parents=True, exist_ok=True)
    model_path = model_root / "model.onnx"
    model_data_path = model_root / "model.onnx.data"
    model_path.write_bytes(b"onnx model")
    model_data_path.write_bytes(model_data)
    (model_root / "tokenizer.json").write_text('{"version":"fixture"}', encoding="utf-8")
    (model_root / "asset-manifest.json").write_text("{}", encoding="utf-8")
    internal_model_root = bundle_dir / "_internal" / "openlinktoken" / "core" / "ai" / "tokens"
    internal_model_root.mkdir(parents=True, exist_ok=True)
    for filename in ("asset-manifest.json", "model.onnx", "model.onnx.data", "tokenizer.json"):
        (internal_model_root / filename).write_bytes(b"duplicate fixture")
    return model_path, model_data_path


def _expected_checksum(content: bytes, file_name: str) -> str:
    """Return the checksum file contents for an asset."""
    digest = hashlib.sha256(content).hexdigest()
    return f"{digest}  {file_name}\n"


class TestCreateReleaseAssets:
    """Unit tests for release asset preparation."""

    def test_zips_complete_one_folder_bundle(self, tmp_path):
        """One-folder builds should include the executable and its dependency files."""
        bundle_dir = tmp_path / "dist" / "olt"
        bundle_dir.mkdir(parents=True)
        (bundle_dir / "olt").write_bytes(b"bundle executable")
        (bundle_dir / "_internal").mkdir()
        (bundle_dir / "_internal" / "runtime.dat").write_bytes(b"runtime")
        model_path, model_data = _write_model_assets(bundle_dir, b"model data")
        cuda_lib = bundle_dir / "_internal" / "nvidia" / "cublas" / "lib" / "libcuda.so"
        cuda_lib.parent.mkdir(parents=True)
        cuda_lib.write_bytes(b"cuda")

        create_release_assets("2.1.0", "Linux", tmp_path / "dist", tmp_path / "release-assets")

        with zipfile.ZipFile(tmp_path / "release-assets" / "olt-cli-2.1.0-linux-x64.zip") as archive:
            assert archive.namelist() == [
                "olt-cli-2.1.0-linux-x64/_internal/runtime.dat",
                "olt-cli-2.1.0-linux-x64/olt",
            ]
            assert not any(
                name.endswith(("asset-manifest.json", "model.onnx", "model.onnx.data", "tokenizer.json"))
                for name in archive.namelist()
            )
        with zipfile.ZipFile(tmp_path / "release-assets/olt-cuda-2.1.0-linux-x64-part-001.zip") as archive:
            assert archive.namelist() == ["nvidia/cublas/lib/libcuda.so"]
            assert archive.read("nvidia/cublas/lib/libcuda.so") == b"cuda"
        assert model_path.is_file()
        assert model_data.is_file()

    def test_creates_linux_release_assets_and_checksums(self, tmp_path):
        """Linux builds should emit updater binary, zip package, and checksum sidecars."""
        dist_dir = tmp_path / "dist"
        output_dir = tmp_path / "release-assets"
        binary_content = b"linux binary"
        _write_binary(dist_dir, "olt", binary_content)
        _write_model_assets(dist_dir, b"model data")
        cuda_lib = dist_dir / "_internal" / "nvidia" / "cublas" / "lib" / "libcuda.so"
        cuda_lib.parent.mkdir(parents=True)
        cuda_lib.write_bytes(b"cuda")

        generated_paths = create_release_assets("2.1.0", "Linux", dist_dir, output_dir)

        generated_names = {path.name for path in generated_paths}
        assert generated_names == {
            "olt-v2.1.0-linux-x86_64",
            "olt-v2.1.0-linux-x86_64.sha256",
            "olt-cli-2.1.0-linux-x64.zip",
            "olt-cli-2.1.0-linux-x64.zip.sha256",
            "olt-cuda-2.1.0-linux-x64-part-001.zip",
            "olt-cuda-2.1.0-linux-x64.manifest",
        }

        binary_path = output_dir / "olt-v2.1.0-linux-x86_64"
        assert binary_path.read_bytes() == binary_content
        assert (output_dir / f"{binary_path.name}.sha256").read_text() == _expected_checksum(
            binary_content, binary_path.name
        )

        zip_path = output_dir / "olt-cli-2.1.0-linux-x64.zip"
        with zipfile.ZipFile(zip_path) as archive:
            archived_binary_name = "olt-cli-2.1.0-linux-x64/olt"
            assert archive.namelist() == [archived_binary_name]
            assert archive.read(archived_binary_name) == binary_content
            assert not any(
                name.endswith(("asset-manifest.json", "model.onnx", "model.onnx.data", "tokenizer.json"))
                for name in archive.namelist()
            )

        assert (output_dir / f"{zip_path.name}.sha256").read_text() == _expected_checksum(
            zip_path.read_bytes(), zip_path.name
        )
        manifest = output_dir / "olt-cuda-2.1.0-linux-x64.manifest"
        checksum, part_name = manifest.read_text().strip().split("\t")
        assert part_name == "olt-cuda-2.1.0-linux-x64-part-001.zip"
        assert checksum == hashlib.sha256((output_dir / part_name).read_bytes()).hexdigest()

    def test_splits_cuda_runtime_files_under_part_target(self, tmp_path, monkeypatch):
        """CUDA assets should split deterministically without changing member paths."""
        monkeypatch.setattr(release_assets, "_CUDA_PART_TARGET_BYTES", 4)
        dist_dir = tmp_path / "dist"
        cuda_root = dist_dir / "_internal" / "nvidia"
        for name, content in (("a.so", b"aaa"), ("b.so", b"bbb")):
            file_path = cuda_root / "cublas" / "lib" / name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)
        _write_binary(dist_dir, "olt", b"linux binary")
        _write_model_assets(dist_dir, b"model data")

        create_release_assets("2.1.0", "Linux", dist_dir, tmp_path / "release-assets")

        for index, expected_name in enumerate(("a.so", "b.so"), start=1):
            part = tmp_path / f"release-assets/olt-cuda-2.1.0-linux-x64-part-{index:03}.zip"
            with zipfile.ZipFile(part) as archive:
                assert archive.namelist() == [f"nvidia/cublas/lib/{expected_name}"]

    def test_places_large_cuda_library_in_own_bounded_part(self, tmp_path, monkeypatch):
        """A library larger than the normal part target should be packaged alone."""
        monkeypatch.setattr(release_assets, "_CUDA_PART_TARGET_BYTES", 3)
        dist_dir = tmp_path / "dist"
        cuda_lib = dist_dir / "_internal" / "nvidia" / "libcuda.so"
        cuda_lib.parent.mkdir(parents=True)
        cuda_lib.write_bytes(b"four")
        _write_binary(dist_dir, "olt", b"linux binary")
        _write_model_assets(dist_dir, b"model data")

        generated_paths = create_release_assets("2.1.0", "Linux", dist_dir, tmp_path / "release-assets")

        part = tmp_path / "release-assets/olt-cuda-2.1.0-linux-x64-part-001.zip"
        assert part in generated_paths
        with zipfile.ZipFile(part) as archive:
            assert archive.namelist() == ["nvidia/libcuda.so"]
            assert archive.read("nvidia/libcuda.so") == b"four"

    def test_creates_macos_arm64_release_assets(self, tmp_path):
        """macOS arm64 builds should use an architecture-specific asset name."""
        dist_dir = tmp_path / "dist"
        output_dir = tmp_path / "release-assets"
        binary_content = b"macOS arm64 binary"
        _write_binary(dist_dir, "olt", binary_content)
        _write_model_assets(dist_dir, b"macOS model data")

        generated_paths = create_release_assets("2.1.0", "macOS", dist_dir, output_dir, architecture="arm64")

        generated_names = {path.name for path in generated_paths}
        assert generated_names == {
            "olt-v2.1.0-macos-arm64",
            "olt-v2.1.0-macos-arm64.sha256",
            "olt-cli-2.1.0-macos-arm64.zip",
            "olt-cli-2.1.0-macos-arm64.zip.sha256",
        }
        with zipfile.ZipFile(output_dir / "olt-cli-2.1.0-macos-arm64.zip") as archive:
            assert not any(
                name.endswith(("asset-manifest.json", "model.onnx", "model.onnx.data", "tokenizer.json"))
                for name in archive.namelist()
            )

    @pytest.mark.parametrize("architecture", ["x86_64", "amd64", "x64", "ppc64"])
    def test_rejects_unsupported_macos_architecture(self, tmp_path, architecture):
        """Unsupported macOS architectures should fail before creating assets."""
        with pytest.raises(ValueError, match="Unsupported macOS architecture"):
            create_release_assets(
                "2.1.0", "macOS", tmp_path / "dist", tmp_path / "release-assets", architecture=architecture
            )

    def test_normalizes_v_prefixed_versions_for_windows_assets(self, tmp_path):
        """Windows builds should keep the .exe binary name while normalizing the version string."""
        dist_dir = tmp_path / "dist"
        output_dir = tmp_path / "release-assets"
        binary_content = b"windows binary"
        _write_binary(dist_dir, "olt.exe", binary_content)
        _write_model_assets(dist_dir, b"Windows model data")

        generated_paths = create_release_assets("v2.1.0", "windows", dist_dir, output_dir)

        binary_path = output_dir / "olt-v2.1.0-windows-x86_64.exe"
        assert binary_path.read_bytes() == binary_content

        with zipfile.ZipFile(output_dir / "olt-cli-2.1.0-windows-x64.zip") as archive:
            assert archive.namelist() == ["olt-cli-2.1.0-windows-x64/olt.exe"]
            assert not any(
                name.endswith(("asset-manifest.json", "model.onnx", "model.onnx.data", "tokenizer.json"))
                for name in archive.namelist()
            )
        assert len(generated_paths) == 4

    def test_rejects_unsupported_runner_os(self, tmp_path):
        """Unsupported runner names should fail fast with a clear error."""
        with pytest.raises(ValueError, match="Unsupported runner OS"):
            create_release_assets("2.1.0", "Solaris", tmp_path / "dist", tmp_path / "release-assets")

    def test_requires_built_executable_to_exist(self, tmp_path):
        """Preparing release assets should fail if PyInstaller output is missing."""
        with pytest.raises(FileNotFoundError, match="Expected built executable"):
            create_release_assets("2.1.0", "Linux", tmp_path / "dist", tmp_path / "release-assets")
