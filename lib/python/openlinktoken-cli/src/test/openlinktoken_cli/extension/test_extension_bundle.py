# SPDX-License-Identifier: MIT
"""Tests for locked standalone extension dependency bundles."""

import base64
import csv
import hashlib
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from packaging.utils import canonicalize_name, parse_wheel_filename

from openlinktoken_cli.extension import extension_bundle
from openlinktoken_cli.extension.extension_bundle import (
    BundleValidationError,
    extract_and_validate_bundle,
    install_wheel_file,
)


@pytest.fixture(autouse=True)
def _use_supported_bundle_target(monkeypatch):
    """Keep target-validation tests independent of the host running pytest."""
    monkeypatch.setattr(extension_bundle, "current_extension_target", lambda: ("linux-x64", "cp312"))


def _make_wheel(
    directory: Path,
    distribution: str,
    version: str,
    *,
    requirements: tuple[str, ...] = (),
    entry_point: str | None = None,
    files: dict[str, bytes] | None = None,
    data_file: tuple[str, bytes] | None = None,
) -> Path:
    """Create a small standards-compliant pure-Python wheel for a bundle test."""
    normalized_name = canonicalize_name(distribution)
    filename_name = normalized_name.replace("-", "_")
    filename_version = version.replace("-", "_").replace(".", "_")
    dist_info = f"{filename_name}-{filename_version}.dist-info"
    wheel_filename = f"{filename_name}-{version}-py3-none-any.whl"
    content = {
        f"{dist_info}/METADATA": (
            "Metadata-Version: 2.1\n"
            f"Name: {distribution}\n"
            f"Version: {version}\n" + "".join(f"Requires-Dist: {requirement}\n" for requirement in requirements)
        ).encode(),
        f"{dist_info}/WHEEL": (
            "Wheel-Version: 1.0\nGenerator: extension-bundle-tests\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        ).encode(),
    }
    if entry_point is not None:
        content[f"{dist_info}/entry_points.txt"] = (f"[openlinktoken.extensions]\n{entry_point}\n").encode()
    content.update(files or {})
    if data_file is not None:
        data_name, data_content = data_file
        content[f"{filename_name}-{version}.data/data/{data_name}"] = data_content

    record = io.StringIO()
    writer = csv.writer(record, lineterminator="\n")
    for name, data in content.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")
        writer.writerow((name, f"sha256={digest}", len(data)))
    writer.writerow((f"{dist_info}/RECORD", "", ""))
    content[f"{dist_info}/RECORD"] = record.getvalue().encode()

    wheel_path = directory / wheel_filename
    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as wheel:
        for name, data in content.items():
            wheel.writestr(name, data)
    return wheel_path


def _locked_wheel(path: Path, distribution: str, version: str, *, sha256: str | None = None) -> dict:
    """Create a bundle lock entry for a test wheel."""
    _, _, _, tags = parse_wheel_filename(path.name)
    return {
        "filename": path.name,
        "name": canonicalize_name(distribution),
        "version": version,
        "tags": sorted(str(tag) for tag in tags),
        "sha256": sha256 or hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _make_bundle(
    directory: Path,
    extension_name: str,
    version: str,
    wheels: list[tuple[Path, str, str]],
    *,
    target: str | None = None,
    python_abi: str | None = None,
    schema_version: int | bool = 1,
    sha256_overrides: dict[str, str] | None = None,
) -> Path:
    """Create a flat bundle ZIP and its lock manifest."""
    current_target, current_abi = extension_bundle.current_extension_target()
    records = [
        _locked_wheel(
            path,
            distribution,
            wheel_version,
            sha256=(sha256_overrides or {}).get(path.name),
        )
        for path, distribution, wheel_version in wheels
    ]
    payload = {
        "schema_version": schema_version,
        "extension": {"name": extension_name, "version": version},
        "target": target or current_target,
        "python_abi": python_abi or current_abi,
        "wheels": records,
    }
    bundle_path = directory / f"{extension_name}-{version}.zip"
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("bundle-manifest.json", json.dumps(payload))
        for path, _, _ in wheels:
            bundle.write(path, path.name)
    return bundle_path


def _make_extension_and_dependency(
    directory: Path,
    extension_name: str = "demo",
    dependency_version: str = "1.0.0",
) -> tuple[Path, Path]:
    """Create an extension wheel and its single pinned dependency."""
    extension = _make_wheel(
        directory,
        f"openlinktoken-ext-{extension_name}",
        "1.0.0",
        requirements=(f"demo-dependency=={dependency_version}",),
        entry_point=f"{extension_name} = demo_extension:DemoExtension",
        files={"demo_extension.py": b"EXTENSION = True\n"},
    )
    dependency = _make_wheel(
        directory,
        "demo-dependency",
        dependency_version,
        files={"demo_dependency.py": b"VERSION = 'pinned'\n"},
    )
    return extension, dependency


def test_extract_and_validate_bundle_checks_complete_lock(tmp_path):
    extension, dependency = _make_extension_and_dependency(tmp_path)
    bundle = _make_bundle(
        tmp_path,
        "demo",
        "1.0.0",
        [
            (extension, "openlinktoken-ext-demo", "1.0.0"),
            (dependency, "demo-dependency", "1.0.0"),
        ],
    )

    wheels = extract_and_validate_bundle(
        bundle,
        tmp_path / "verified",
        expected_name="demo",
        expected_version="1.0.0",
        core_inventory={"openlinktoken": "2.2.1"},
    )

    assert {wheel.name for wheel in wheels} == {"openlinktoken-ext-demo", "demo-dependency"}
    assert all(wheel.path.is_file() for wheel in wheels)


def test_extract_and_validate_bundle_rejects_missing_transitive_wheel(tmp_path):
    extension, _ = _make_extension_and_dependency(tmp_path)
    bundle = _make_bundle(
        tmp_path,
        "demo",
        "1.0.0",
        [(extension, "openlinktoken-ext-demo", "1.0.0")],
    )

    with pytest.raises(BundleValidationError, match="missing 'demo-dependency'"):
        extract_and_validate_bundle(
            bundle,
            tmp_path / "verified",
            expected_name="demo",
            expected_version="1.0.0",
            core_inventory={},
        )


def test_extract_and_validate_bundle_rejects_core_version_conflict(tmp_path):
    extension = _make_wheel(
        tmp_path,
        "openlinktoken-ext-demo",
        "1.0.0",
        requirements=("openlinktoken>=9",),
        entry_point="demo = demo_extension:DemoExtension",
    )
    bundle = _make_bundle(
        tmp_path,
        "demo",
        "1.0.0",
        [(extension, "openlinktoken-ext-demo", "1.0.0")],
    )

    with pytest.raises(BundleValidationError, match="core dependency conflict"):
        extract_and_validate_bundle(
            bundle,
            tmp_path / "verified",
            expected_name="demo",
            expected_version="1.0.0",
            core_inventory={"openlinktoken": "2.2.1"},
        )


def test_extract_and_validate_bundle_rejects_boolean_schema_version(tmp_path):
    extension, dependency = _make_extension_and_dependency(tmp_path)
    bundle = _make_bundle(
        tmp_path,
        "demo",
        "1.0.0",
        [
            (extension, "openlinktoken-ext-demo", "1.0.0"),
            (dependency, "demo-dependency", "1.0.0"),
        ],
        schema_version=True,
    )

    with pytest.raises(BundleValidationError, match="manifest schema"):
        extract_and_validate_bundle(
            bundle,
            tmp_path / "verified",
            expected_name="demo",
            expected_version="1.0.0",
            core_inventory={},
        )


def test_extract_and_validate_bundle_rejects_digest_and_target_mismatches(tmp_path):
    extension, dependency = _make_extension_and_dependency(tmp_path)
    bad_digest_bundle = _make_bundle(
        tmp_path,
        "demo",
        "1.0.0",
        [
            (extension, "openlinktoken-ext-demo", "1.0.0"),
            (dependency, "demo-dependency", "1.0.0"),
        ],
        sha256_overrides={dependency.name: "0" * 64},
    )
    with pytest.raises(BundleValidationError, match="SHA-256 mismatch"):
        extract_and_validate_bundle(
            bad_digest_bundle,
            tmp_path / "bad-digest",
            expected_name="demo",
            expected_version="1.0.0",
            core_inventory={},
        )

    wrong_target_bundle = _make_bundle(
        tmp_path,
        "demo",
        "1.0.0",
        [
            (extension, "openlinktoken-ext-demo", "1.0.0"),
            (dependency, "demo-dependency", "1.0.0"),
        ],
        target="unsupported-target",
    )
    with pytest.raises(BundleValidationError, match="does not match this runtime"):
        extract_and_validate_bundle(
            wrong_target_bundle,
            tmp_path / "wrong-target",
            expected_name="demo",
            expected_version="1.0.0",
            core_inventory={},
        )


def test_installer_handles_wheel_data_scheme_members(tmp_path):
    wheel = _make_wheel(
        tmp_path,
        "demo-package",
        "1.0.0",
        files={"demo_package.py": b"VALUE = 1\n"},
        data_file=("shared.txt", b"installed through the data scheme"),
    )
    destination = tmp_path / "installed"

    install_wheel_file(wheel, destination)

    assert (destination / "site-packages" / "demo_package.py").is_file()
    assert (destination / "data" / "shared.txt").read_bytes() == b"installed through the data scheme"


def test_private_dependency_versions_work_in_separate_processes(tmp_path):
    versions = ("1.0.0", "2.0.0")
    installed = []
    for extension_name, dependency_version in zip(("extension-one", "extension-two"), versions):
        extension = _make_wheel(
            tmp_path,
            f"openlinktoken-{extension_name}",
            "1.0.0",
            requirements=(f"shared-dependency=={dependency_version}",),
            entry_point=f"{extension_name} = extension_module:Extension",
            files={"extension_module.py": b"EXTENSION = True\n"},
        )
        dependency = _make_wheel(
            tmp_path,
            "shared-dependency",
            dependency_version,
            files={"shared_dependency.py": f"VERSION = '{dependency_version}'\n".encode()},
        )
        bundle = _make_bundle(
            tmp_path,
            extension_name,
            "1.0.0",
            [
                (extension, f"openlinktoken-{extension_name}", "1.0.0"),
                (dependency, "shared-dependency", dependency_version),
            ],
        )
        wheels = extract_and_validate_bundle(
            bundle,
            tmp_path / f"verified-{extension_name}",
            expected_name=extension_name,
            expected_version="1.0.0",
            core_inventory={},
        )
        extension_root = tmp_path / extension_name / "extension"
        dependency_root = tmp_path / extension_name / "dependencies"
        install_wheel_file(next(wheel.path for wheel in wheels if wheel.name != "shared-dependency"), extension_root)
        install_wheel_file(next(wheel.path for wheel in wheels if wheel.name == "shared-dependency"), dependency_root)
        installed.append((extension_root / "site-packages", dependency_root / "site-packages"))

    observed_versions = []
    for extension_path, dependency_path in installed:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.extend(sys.argv[1:]); import shared_dependency; print(shared_dependency.VERSION)",
                str(extension_path),
                str(dependency_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        observed_versions.append(result.stdout.strip())

    assert observed_versions == list(versions)
