"""
Copyright (c) Truveta. All rights reserved.

Helpers for preparing CLI release assets in the GitHub Actions build workflow.
"""

import argparse
import hashlib
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
        executable_name="opentoken",
        package_name="opentoken-cli-{version}-linux-x64",
        binary_asset_name="opentoken-v{version}-linux-x86_64",
    ),
    "macos": ReleaseAssetSpec(
        executable_name="opentoken",
        package_name="opentoken-cli-{version}-macos-universal",
        binary_asset_name="opentoken-v{version}-macos-universal",
    ),
    "windows": ReleaseAssetSpec(
        executable_name="opentoken.exe",
        package_name="opentoken-cli-{version}-windows-x64",
        binary_asset_name="opentoken-v{version}-windows-x86_64.exe",
    ),
}


def create_release_assets(version: str, runner_os: str, dist_dir: Path, output_dir: Path) -> list[Path]:
    """Create updater-ready CLI binaries, packaged ZIPs, and SHA-256 sidecars."""
    spec = _resolve_release_asset_spec(version, runner_os)
    output_dir.mkdir(parents=True, exist_ok=True)

    built_executable = dist_dir / spec.executable_name
    if not built_executable.is_file():
        raise FileNotFoundError(f"Expected built executable at {built_executable}")

    raw_binary_path = output_dir / spec.binary_asset_name
    shutil.copy2(built_executable, raw_binary_path)

    zip_path = output_dir / f"{spec.package_name}.zip"
    _create_zip_archive(built_executable, spec.executable_name, spec.package_name, zip_path)

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

    created_paths = create_release_assets(args.version, args.runner_os, args.dist_dir, args.output_dir)
    for path in created_paths:
        print(path)
    return 0


def _resolve_release_asset_spec(version: str, runner_os: str) -> ReleaseAssetSpec:
    """Resolve the asset naming convention for the requested runner OS."""
    normalized_version = _normalize_version(version)
    normalized_runner = runner_os.strip().lower()

    try:
        template = _RELEASE_ASSET_SPECS[normalized_runner]
    except KeyError as exc:
        raise ValueError(f"Unsupported runner OS: {runner_os}") from exc

    return ReleaseAssetSpec(
        executable_name=template.executable_name,
        package_name=template.package_name.format(version=normalized_version),
        binary_asset_name=template.binary_asset_name.format(version=normalized_version),
    )


def _normalize_version(version: str) -> str:
    """Drop the optional leading v prefix and validate the remaining version."""
    normalized_version = version.strip().lstrip("v")
    if not normalized_version:
        raise ValueError("Version cannot be empty")
    return normalized_version


def _create_zip_archive(binary_path: Path, executable_name: str, package_name: str, zip_path: Path) -> None:
    """Create the downloadable ZIP bundle for manual installation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        package_root = Path(temp_dir) / package_name
        package_root.mkdir(parents=True, exist_ok=True)
        packaged_binary = package_root / executable_name
        shutil.copy2(binary_path, packaged_binary)

        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(packaged_binary, arcname=f"{package_name}/{executable_name}")


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
