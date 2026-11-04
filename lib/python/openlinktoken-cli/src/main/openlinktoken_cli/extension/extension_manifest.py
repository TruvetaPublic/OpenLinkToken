# SPDX-License-Identifier: MIT
"""Data-only validation for extension bootstrap and update manifests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional
from urllib.parse import urlparse

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from openlinktoken.metadata import Metadata

MANIFEST_SCHEMA_VERSION = 1
CURRENT_MANIFEST_SCHEMA_VERSION = 2
STANDALONE_EXTENSION_RUNTIME_PROTOCOL = 2
SUPPORTED_MANIFEST_SCHEMA_VERSIONS = frozenset({1, CURRENT_MANIFEST_SCHEMA_VERSION})
CURRENT_CORE_VERSION = Metadata.DEFAULT_VERSION
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_EXTENSION_COMMAND_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_PYTHON_ABI_RE = re.compile(r"^cp\d{2,3}$")
_SIGNATURE_ALGORITHMS = frozenset({"ed25519", "ecdsa-sha256", "rsa-sha256"})
_SIGNATURE_KEYS = frozenset({"algorithm", "value", "key_id"})


class ManifestValidationError(ValueError):
    """Raised when an extension manifest violates the bootstrap contract."""


@dataclass(frozen=True)
class ArtifactRecord:
    """A validated wheel artifact record from a manifest."""

    url: str
    sha256: Optional[str]
    signature: Optional[dict[str, str]]
    version: Optional[str] = None


@dataclass(frozen=True)
class BundleRecord:
    """A target-specific, checksum-verified standalone dependency bundle."""

    target: str
    python_abi: str
    url: str
    sha256: str


@dataclass(frozen=True)
class ExtensionManifest:
    """Normalized representation of a bootstrap or update manifest."""

    name: str
    version: str
    core_specifier: str
    artifacts: tuple[ArtifactRecord, ...]
    schema_version: int = MANIFEST_SCHEMA_VERSION
    update_manifest_url: Optional[str] = None
    distribution_name: Optional[str] = None
    source_url: Optional[str] = None
    minimum_runtime_protocol: Optional[int] = None
    command_name: Optional[str] = None
    description: Optional[str] = None
    bundles: tuple[BundleRecord, ...] = ()


def parse_manifest(
    payload: Mapping[str, Any],
    *,
    expected_name: Optional[str] = None,
    allow_local: bool = False,
) -> ExtensionManifest:
    """
    Validate and normalize a bootstrap or vendor update manifest.

    The function only examines JSON-compatible data. It never imports or loads
    extension modules, which keeps update checks safe before installation.

    Args:
        payload: Structured payload to parse, validate, or encrypt.
        expected_name: Expected name used to check the actual result.
        allow_local: Whether to allow local.

    Returns:
        Validated and normalize a bootstrap or vendor update manifest.
    """
    if not isinstance(payload, Mapping):
        raise ManifestValidationError("Manifest must be a JSON object.")
    schema_version = payload.get("schema_version")
    if (
        isinstance(schema_version, int)
        and not isinstance(schema_version, bool)
        and schema_version == CURRENT_MANIFEST_SCHEMA_VERSION
    ):
        return _parse_bundle_manifest(payload, expected_name=expected_name, allow_local=allow_local)
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version not in SUPPORTED_MANIFEST_SCHEMA_VERSIONS
    ):
        supported = ", ".join(str(version) for version in sorted(SUPPORTED_MANIFEST_SCHEMA_VERSIONS))
        raise ManifestValidationError(f"Unsupported or missing schema_version; expected one of {supported}.")

    extension = payload.get("extension")
    if isinstance(extension, Mapping):
        name = _required_string(extension, "name")
        version = _required_version(extension, "version")
        artifact_payloads = [extension]
        update_manifest_url = _optional_url(extension.get("update_manifest_url"), allow_local=allow_local)
        distribution_name = _optional_string(extension.get("distribution_name"))
        source_url = _optional_url(extension.get("artifact_url"), allow_local=allow_local)
        core_specifier = _bootstrap_core_specifier(payload.get("core"))
    elif isinstance(extension, str):
        name = extension.strip()
        if not name:
            raise ManifestValidationError("extension identity must not be empty.")
        version = _required_version(payload, "latest_version")
        artifact_payloads = payload.get("artifacts")
        if not isinstance(artifact_payloads, list) or not artifact_payloads:
            raise ManifestValidationError("Update manifests require a non-empty artifacts list.")
        update_manifest_url = None
        distribution_name = None
        source_url = None
        core_specifier = _required_core_specifier(payload.get("requires_core"))
    else:
        raise ManifestValidationError("extension must be an object or extension name string.")

    if expected_name is not None and name != expected_name:
        raise ManifestValidationError(
            f"Manifest extension '{name}' does not match requested extension '{expected_name}'."
        )
    artifacts = tuple(
        _parse_artifact(
            artifact,
            default_version=version,
            allow_local=allow_local,
        )
        for artifact in artifact_payloads
    )
    return ExtensionManifest(
        name=name,
        version=version,
        core_specifier=core_specifier,
        artifacts=artifacts,
        schema_version=MANIFEST_SCHEMA_VERSION,
        update_manifest_url=update_manifest_url,
        distribution_name=distribution_name,
        source_url=source_url,
    )


def _parse_bundle_manifest(
    payload: Mapping[str, Any],
    *,
    expected_name: Optional[str],
    allow_local: bool,
) -> ExtensionManifest:
    """
    Validate a schema-version-2 manifest that points to locked wheel bundles.

    Args:
        payload: Structured schema-version-2 manifest.
        expected_name: Expected extension identity, when supplied by an update.
        allow_local: Whether local bundle URLs are permitted.

    Returns:
        Normalized standalone extension manifest.

    Raises:
        ManifestValidationError: If the manifest violates the bundle contract.
    """
    extension = payload.get("extension")
    if isinstance(extension, Mapping):
        name = _required_string(extension, "name")
        version = _required_version(extension, "version")
        update_manifest_url = _optional_url(extension.get("update_manifest_url"), allow_local=allow_local)
        core_specifier = _bootstrap_core_specifier(payload.get("core"))
    elif isinstance(extension, str):
        name = extension.strip()
        if not name:
            raise ManifestValidationError("extension identity must not be empty.")
        version = _required_version(payload, "latest_version")
        update_manifest_url = None
        core_specifier = _required_core_specifier(payload.get("requires_core"))
    else:
        raise ManifestValidationError("extension must be an object or extension name string.")

    if expected_name is not None and name != expected_name:
        raise ManifestValidationError(
            f"Manifest extension '{name}' does not match requested extension '{expected_name}'."
        )
    command_name = _required_string(payload, "command_name")
    if not _EXTENSION_COMMAND_RE.fullmatch(command_name):
        raise ManifestValidationError("command_name contains unsupported characters.")
    if command_name != name:
        raise ManifestValidationError("command_name must match the extension identity.")
    description = _required_string(payload, "description")
    protocol = payload.get("minimum_runtime_protocol")
    if isinstance(protocol, bool) or not isinstance(protocol, int) or protocol < 1:
        raise ManifestValidationError("minimum_runtime_protocol must be a positive integer.")

    raw_bundles = payload.get("bundles")
    if not isinstance(raw_bundles, list) or not raw_bundles:
        raise ManifestValidationError("Schema-version-2 manifests require a non-empty bundles list.")
    bundles = tuple(_parse_bundle(bundle, allow_local=allow_local) for bundle in raw_bundles)
    targets = {(bundle.target, bundle.python_abi) for bundle in bundles}
    if len(targets) != len(bundles):
        raise ManifestValidationError("Bundle target and Python ABI pairs must be unique.")

    return ExtensionManifest(
        name=name,
        version=version,
        core_specifier=core_specifier,
        artifacts=(),
        schema_version=CURRENT_MANIFEST_SCHEMA_VERSION,
        update_manifest_url=update_manifest_url,
        minimum_runtime_protocol=protocol,
        command_name=command_name,
        description=description,
        bundles=bundles,
    )


def _parse_bundle(payload: Any, *, allow_local: bool) -> BundleRecord:
    """
    Parse one target-specific bundle locator.

    Args:
        payload: Bundle object from a schema-version-2 manifest.
        allow_local: Whether local bundle URLs are permitted.

    Returns:
        Validated target, ABI, URL, and SHA-256 metadata.

    Raises:
        ManifestValidationError: If a bundle field is invalid.
    """
    if not isinstance(payload, Mapping):
        raise ManifestValidationError("Each bundle must be a JSON object.")
    target = _required_string(payload, "target")
    python_abi = _required_string(payload, "python_abi")
    if not _PYTHON_ABI_RE.fullmatch(python_abi):
        raise ManifestValidationError("python_abi must be a CPython ABI such as 'cp312'.")
    url = _required_url(payload.get("url"), allow_local=allow_local)
    sha256 = payload.get("sha256")
    if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
        raise ManifestValidationError("Each bundle requires a 64-character hexadecimal sha256.")
    return BundleRecord(target, python_abi, url, sha256.lower())


def is_core_compatible(core_version: str, core_specifier: str) -> bool:
    """
    Return whether *core_version* satisfies a validated core range.

    Args:
        core_version: String containing the core version used to check.
        core_specifier: String containing the core specifier used to check.

    Returns:
        Whether *core_version* satisfies a validated core range.
    """
    try:
        return Version(core_version) in SpecifierSet(core_specifier)
    except (InvalidVersion, InvalidSpecifier, TypeError):
        return False


def _parse_artifact(
    payload: Any,
    *,
    default_version: str,
    allow_local: bool,
) -> ArtifactRecord:
    """
    Parse artifact.

    Args:
        payload: Structured payload to parse, validate, or encrypt.
        default_version: Fallback version used when no explicit value is supplied.
        allow_local: Whether to allow local.

    Returns:
        Parsed artifact.
    """
    if not isinstance(payload, Mapping):
        raise ManifestValidationError("Each artifact must be a JSON object.")
    url_value = payload.get("artifact_url", payload.get("url"))
    url = _required_url(url_value, allow_local=allow_local)
    sha256 = payload.get("sha256")
    if sha256 is not None:
        if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
            raise ManifestValidationError("sha256 must be a 64-character hexadecimal string.")
        sha256 = sha256.lower()
    if sha256 is None and urlparse(url).scheme != "file":
        raise ManifestValidationError("Remote artifacts require sha256.")
    signature = _parse_signature(payload.get("signature"))
    if sha256 is None and signature is not None:
        raise ManifestValidationError("Signature-only artifacts are not supported; sha256 is required.")
    artifact_version = payload.get("version", default_version)
    if not isinstance(artifact_version, str):
        raise ManifestValidationError("Artifact version must be a string.")
    try:
        Version(artifact_version)
    except InvalidVersion as exc:
        raise ManifestValidationError(f"Invalid artifact version '{artifact_version}'.") from exc
    return ArtifactRecord(url, sha256, signature, artifact_version)


def _parse_signature(value: Any) -> Optional[dict[str, str]]:
    """
    Parse signature.

    Args:
        value: Signature object from the extension manifest.

    Returns:
        Parsed signature.
    """
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ManifestValidationError("signature must be an object.")
    unknown = set(value) - _SIGNATURE_KEYS
    if unknown:
        raise ManifestValidationError(f"Unsupported signature fields: {', '.join(sorted(unknown))}.")
    algorithm = value.get("algorithm")
    signature_value = value.get("value")
    if algorithm not in _SIGNATURE_ALGORITHMS or not isinstance(signature_value, str) or not signature_value:
        raise ManifestValidationError("signature must contain a supported algorithm and non-empty value.")
    key_id = value.get("key_id")
    if key_id is not None and (not isinstance(key_id, str) or not key_id):
        raise ManifestValidationError("signature.key_id must be a non-empty string.")
    result = {"algorithm": algorithm, "value": signature_value}
    if key_id is not None:
        result["key_id"] = key_id
    return result


def _bootstrap_core_specifier(core: Any) -> str:
    """
    Build a validated core-version specifier from a bootstrap manifest.

    Args:
        core: Core version bounds from the bootstrap manifest.

    Returns:
        Comma-separated core-version specifier built from the manifest minimum and maximum.
    """
    if not isinstance(core, Mapping):
        raise ManifestValidationError("Bootstrap manifests require a core object.")
    minimum = core.get("min_version")
    maximum = core.get("max_version")
    parts = []
    if minimum is not None:
        parts.append(f">={_valid_version(minimum, 'core.min_version')}")
    if maximum is not None:
        if not isinstance(maximum, str) or not maximum.strip():
            raise ManifestValidationError("core.max_version must be a non-empty version or specifier.")
        maximum = maximum.strip()
        parts.append(maximum if maximum[0] in "<=>" else f"<={_valid_version(maximum, 'core.max_version')}")
    if not parts:
        raise ManifestValidationError("Bootstrap manifests require a core version range.")
    return _required_core_specifier(",".join(parts))


def _required_core_specifier(value: Any) -> str:
    """
    Validate and normalize a non-empty core-version compatibility range.

    Args:
        value: Core-version compatibility range to parse and normalize.

    Returns:
        Normalized non-empty core-version compatibility specifier.
    """
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError("A non-empty core compatibility range is required.")
    try:
        specifier = SpecifierSet(value)
    except InvalidSpecifier as exc:
        raise ManifestValidationError(f"Invalid core compatibility range '{value}'.") from exc
    return str(specifier)


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    """
    Extract and validate a required non-empty string from a manifest mapping.

    Args:
        payload: Manifest mapping containing the required string field.
        key: Manifest field name whose non-empty string value is required.

    Returns:
        Stripped non-empty string stored under the requested manifest key.
    """
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{key} must be a non-empty string.")
    return value.strip()


def _optional_string(value: Any) -> Optional[str]:
    """
    Validate an optional string and return its stripped value when present.

    Args:
        value: Optional value to validate and normalize as a string.

    Returns:
        Stripped optional string, or None when the field is absent.
    """
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError("Optional string fields must be non-empty strings.")
    return value.strip()


def _required_version(payload: Mapping[str, Any], key: str) -> str:
    """
    Extract and validate a required version string from a manifest mapping.

    Args:
        payload: Manifest mapping containing the required version field.
        key: Manifest field name whose version string is required.

    Returns:
        Validated version string stored under the requested manifest key.
    """
    value = _required_string(payload, key)
    try:
        Version(value)
    except InvalidVersion as exc:
        raise ManifestValidationError(f"Invalid version '{value}'.") from exc
    return value


def _valid_version(value: Any, field: str) -> str:
    """
    Validate and strip a version value associated with a manifest field.

    Args:
        value: Version value to validate and strip.
        field: Manifest field name used in validation errors.

    Returns:
        Stripped version string after successful version validation.
    """
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError(f"{field} must be a non-empty version.")
    try:
        Version(value.strip())
    except InvalidVersion as exc:
        raise ManifestValidationError(f"{field} contains an invalid version.") from exc
    return value.strip()


def _required_url(value: Any, *, allow_local: bool) -> str:
    """
    Validate a required artifact URL under the configured local-file policy.

    Args:
        value: Artifact URL value to validate and normalize.
        allow_local: Whether local file URLs are permitted.

    Returns:
        Validated artifact URL accepted by the configured URL policy.
    """
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError("Artifact URL must be a non-empty string.")
    return _validate_url(value.strip(), allow_local=allow_local)


def _optional_url(value: Any, *, allow_local: bool) -> Optional[str]:
    """
    Validate an optional URL, returning None when it is omitted.

    Args:
        value: Optional URL value to validate and normalize.
        allow_local: Whether local file URLs are permitted.

    Returns:
        Validated URL, or None when the optional URL is absent.
    """
    if value is None:
        return None
    return _validate_url(value, allow_local=allow_local)


def _validate_url(value: Any, *, allow_local: bool) -> str:
    """
    Validate url.

    Args:
        value: URL value from the extension manifest.
        allow_local: Whether to allow local.

    Returns:
        Validated url.
    """
    if not isinstance(value, str) or not value.strip():
        raise ManifestValidationError("URL fields must be non-empty strings.")
    parsed = urlparse(value.strip())
    if parsed.scheme == "https" and parsed.netloc:
        return value.strip()
    if allow_local and parsed.scheme == "file" and parsed.path:
        return value.strip()
    raise ManifestValidationError("URLs must use HTTPS; file URLs require an explicit local install.")
