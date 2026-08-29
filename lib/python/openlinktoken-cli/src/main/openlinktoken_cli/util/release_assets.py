# SPDX-License-Identifier: MIT
"""
Helpers for preparing CLI release assets in the GitHub Actions build workflow.
"""

import argparse
import hashlib
import platform
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class ReleaseAssetSpec:
    """Naming details for a platform-specific CLI release build."""

    executable_name: str
    package_name: str
    binary_asset_name: str


_RELEASE_ASSET_SPECS = {
    "linux": ReleaseAssetSpec(
        executable_name="olt",
        package_name="olt-cli-{version}-linux-x64",
        binary_asset_name="olt-v{version}-linux-x86_64",
    ),
    "macos": ReleaseAssetSpec(
        executable_name="olt",
        package_name="olt-cli-{version}-macos-{architecture}",
        binary_asset_name="olt-v{version}-macos-{architecture}",
    ),
    "windows": ReleaseAssetSpec(
        executable_name="olt.exe",
        package_name="olt-cli-{version}-windows-x64",
        binary_asset_name="olt-v{version}-windows-x86_64.exe",
    ),
}


def create_release_assets(
    version: str,
    runner_os: str,
    dist_dir: Path,
    output_dir: Path,
    architecture: str | None = None,
) -> list[Path]:
    """Create updater-ready CLI binaries, packaged ZIPs, and SHA-256 sidecars."""
    spec = _resolve_release_asset_spec(version, runner_os, architecture)
    output_dir.mkdir(parents=True, exist_ok=True)

    built_executable = dist_dir / spec.executable_name
    bundle_root = dist_dir
    if not built_executable.is_file():
        bundle_root = dist_dir / "olt"
        built_executable = bundle_root / spec.executable_name
    if not built_executable.is_file():
        raise FileNotFoundError(f"Expected built executable at {built_executable}")

    raw_binary_path = output_dir / spec.binary_asset_name
    shutil.copy2(built_executable, raw_binary_path)

    zip_path = output_dir / f"{spec.package_name}.zip"
    _create_zip_archive(bundle_root, spec.package_name, zip_path)

    binary_checksum_path = _write_checksum_file(raw_binary_path)
    zip_checksum_path = _write_checksum_file(zip_path)

    return [raw_binary_path, binary_checksum_path, zip_path, zip_checksum_path]


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for GitHub Actions release asset preparation."""
    parser = argparse.ArgumentParser(description="Prepare CLI release assets and checksum files.")
    parser.add_argument(
        "--version",
        required=True,
        help="CLI version, with or without the leading v prefix.",
    )
    parser.add_argument(
        "--runner-os",
        required=True,
        help="GitHub Actions runner OS name (Linux, macOS, Windows).",
    )
    parser.add_argument(
        "--architecture",
        default=None,
        help="Target architecture (for example, arm64 or x86_64; defaults to the host architecture on macOS).",
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=Path("dist"),
        help="Directory containing the built executable.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("release-assets"),
        help="Directory where release assets and checksum files are written.",
    )
    args = parser.parse_args(argv)

    created_paths = create_release_assets(
        args.version,
        args.runner_os,
        args.dist_dir,
        args.output_dir,
        args.architecture,
    )
    for path in created_paths:
        print(path)
    return 0


def _resolve_release_asset_spec(
    version: str,
    runner_os: str,
    architecture: str | None = None,
) -> ReleaseAssetSpec:
    """Resolve the asset naming convention for the requested runner OS."""
    normalized_version = _normalize_version(version)
    normalized_runner = runner_os.strip().lower()

    try:
        template = _RELEASE_ASSET_SPECS[normalized_runner]
    except KeyError as exc:
        raise ValueError(f"Unsupported runner OS: {runner_os}") from exc

    normalized_architecture = (
        _normalize_macos_architecture(architecture or platform.machine()) if normalized_runner == "macos" else None
    )
    return ReleaseAssetSpec(
        executable_name=template.executable_name,
        package_name=template.package_name.format(version=normalized_version, architecture=normalized_architecture),
        binary_asset_name=template.binary_asset_name.format(
            version=normalized_version,
            architecture=normalized_architecture,
        ),
    )


def _normalize_version(version: str) -> str:
    """Drop the optional leading v prefix and validate the remaining version."""
    normalized_version = version.strip().lstrip("v")
    if not normalized_version:
        raise ValueError("Version cannot be empty")
    return normalized_version


def _normalize_macos_architecture(architecture: str) -> str:
    """Normalize supported macOS architecture names for release assets."""
    normalized_architecture = architecture.strip().lower()
    if normalized_architecture in {"arm64", "aarch64"}:
        return "arm64"
    if normalized_architecture in {"x86_64", "amd64", "x64"}:
        return "x86_64"
    raise ValueError(f"Unsupported macOS architecture: {architecture}")


def _create_zip_archive(bundle_root: Path, package_name: str, zip_path: Path) -> None:
    """Create a ZIP containing the complete one-folder bundle."""
    with tempfile.TemporaryDirectory() as temp_dir:
        package_root = Path(temp_dir) / package_name
        package_root.mkdir(parents=True, exist_ok=True)
        for source_path in bundle_root.rglob("*"):
            if source_path.is_file():
                relative_path = source_path.relative_to(bundle_root)
                packaged_path = package_root / relative_path
                packaged_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, packaged_path)

        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for packaged_path in sorted(package_root.rglob("*")):
                if packaged_path.is_file():
                    archive.write(packaged_path, arcname=packaged_path.relative_to(Path(temp_dir)))


def _write_checksum_file(asset_path: Path) -> Path:
    """Create the .sha256 sidecar file for a release asset."""
    checksum_path = asset_path.parent / f"{asset_path.name}.sha256"
    checksum_path.write_text(f"{_sha256_file(asset_path)}  {asset_path.name}\n")
    return checksum_path


def _sha256_file(path: Path) -> str:
    """Compute the SHA-256 digest for the provided file."""
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
