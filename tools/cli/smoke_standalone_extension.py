#!/usr/bin/env python3
"""Install and run the repository's hello-world extension with a frozen CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import Version

from openlinktoken_cli.extension.extension_bundle import current_extension_target
from openlinktoken_cli.extension.extension_manifest import (
    CURRENT_CORE_VERSION,
    CURRENT_MANIFEST_SCHEMA_VERSION,
    STANDALONE_EXTENSION_RUNTIME_PROTOCOL,
)

EXTENSION_NAME = "hello-world"
EXTENSION_DISTRIBUTION = "openlinktoken-ext-hello-world"


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_smoke_manifest(wheel_path: Path, output_dir: Path) -> Path:
    """Create a local bootstrap manifest and locked bundle for the hello-world wheel."""
    wheel_path = wheel_path.resolve()
    if not wheel_path.is_file():
        raise FileNotFoundError(f"Smoke extension wheel not found: {wheel_path}")

    distribution, wheel_version, _, tags = parse_wheel_filename(wheel_path.name)
    distribution_name = canonicalize_name(str(distribution))
    if distribution_name != EXTENSION_DISTRIBUTION:
        raise ValueError(f"Expected wheel distribution '{EXTENSION_DISTRIBUTION}', got '{distribution_name}'.")

    version = str(wheel_version)
    target, python_abi = current_extension_target()
    wheel_sha256 = _sha256_file(wheel_path)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle_path = output_dir / f"{EXTENSION_NAME}-{version}.zip"
    bundle_manifest = {
        "schema_version": 1,
        "extension": {"name": EXTENSION_NAME, "version": version},
        "target": target,
        "python_abi": python_abi,
        "wheels": [
            {
                "filename": wheel_path.name,
                "name": distribution_name,
                "version": version,
                "tags": sorted(str(tag) for tag in tags),
                "sha256": wheel_sha256,
            }
        ],
    }
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("bundle-manifest.json", json.dumps(bundle_manifest, sort_keys=True))
        bundle.write(wheel_path, wheel_path.name)

    core_version = Version(CURRENT_CORE_VERSION)
    manifest = {
        "schema_version": CURRENT_MANIFEST_SCHEMA_VERSION,
        "extension": {"name": EXTENSION_NAME, "version": version},
        "core": {
            "min_version": str(core_version),
            "max_version": f"<{core_version.major + 1}.0.0",
        },
        "minimum_runtime_protocol": STANDALONE_EXTENSION_RUNTIME_PROTOCOL,
        "command_name": EXTENSION_NAME,
        "description": "Open Link Token hello-world smoke extension",
        "bundles": [
            {
                "target": target,
                "python_abi": python_abi,
                "url": bundle_path.as_uri(),
                "sha256": _sha256_file(bundle_path),
            }
        ],
    }
    manifest_path = output_dir / f"{EXTENSION_NAME}-{version}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def _run_cli(executable: Path, arguments: list[str], environment: dict[str, str]) -> str:
    """Run a frozen CLI command and return stdout, surfacing its output on failure."""
    command = [str(executable), *arguments]
    result = subprocess.run(command, capture_output=True, text=True, env=environment)
    if result.returncode != 0:
        output = "\n".join(part for part in (result.stdout, result.stderr) if part)
        raise RuntimeError(f"Frozen CLI command {command!r} exited with {result.returncode}.\n{output}")
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.stdout


def run_smoke(executable: Path, wheel_path: Path) -> None:
    """Install the local hello-world bundle and verify its command runs."""
    executable = executable.resolve()
    if not executable.is_file():
        raise FileNotFoundError(f"Frozen CLI executable not found: {executable}")

    with tempfile.TemporaryDirectory(prefix="olt-extension-smoke-") as temp_dir:
        temp_path = Path(temp_dir)
        environment = os.environ.copy()
        environment["OLT_EXTENSIONS_DIR"] = str(temp_path / "extensions")
        manifest_path = create_smoke_manifest(wheel_path, temp_path / "artifacts")

        _run_cli(executable, ["extension", "install", str(manifest_path), "--yes"], environment)
        greeting = _run_cli(executable, [EXTENSION_NAME, "hello", "--name", "CI"], environment)
        if greeting.strip() != "Hello, CI":
            raise RuntimeError(f"Expected hello-world command to print 'Hello, CI', got {greeting!r}.")


def main() -> int:
    """Parse smoke-test inputs and run the frozen extension installation check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", required=True, type=Path, help="Path to the frozen olt executable.")
    parser.add_argument("--wheel", required=True, type=Path, help="Built hello-world extension wheel.")
    args = parser.parse_args()
    try:
        run_smoke(args.executable, args.wheel)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
