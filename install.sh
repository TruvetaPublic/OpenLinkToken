#!/usr/bin/env bash

set -euo pipefail

readonly REPOSITORY="TruvetaPublic/OpenLinkToken"
readonly RELEASES_URL="https://github.com/${REPOSITORY}/releases"
readonly API_URL="https://api.github.com/repos/${REPOSITORY}"

version=""
install_dir="${OLT_INSTALL_DIR:-$HOME/.local/bin}"
no_cuda=false

usage() {
    cat <<'EOF'
Install the Open Link Token CLI for Linux or macOS.

Usage:
  install.sh [--version VERSION] [--install-dir DIRECTORY] [--no-cuda]

Options:
  --version VERSION       Install a specific release (default: latest)
  --install-dir DIRECTORY Install into DIRECTORY (default: ~/.local/bin)
  --no-cuda               Skip CUDA runtime installation (Linux x86_64 only)
  -h, --help              Show this help
EOF
}

fail() {
    printf 'Error: %s\n' "$1" >&2
    exit 1
}

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        fail "shasum or sha256sum is required to verify downloads"
    fi
}

verify_sha256() {
    local expected actual file description
    expected="$1"
    file="$2"
    description="$3"
    [[ "$expected" =~ ^[[:xdigit:]]{64}$ ]] || fail "Invalid SHA-256 checksum for $description"
    actual=$(sha256_file "$file")
    expected=$(printf '%s' "$expected" | tr '[:upper:]' '[:lower:]')
    actual=$(printf '%s' "$actual" | tr '[:upper:]' '[:lower:]')
    [[ "$actual" == "$expected" ]] || fail "SHA-256 verification failed for $description"
}

install_model_asset() {
    local asset_id filename destination manifest manifest_url legacy_manifest
    local manifest_kind model_checksum manifest_extra part_prefix entry_kind expected_checksum legacy_manifest
    local model_asset extra part_number expected_part_number part_path model_data part_count

    asset_id="$1"
    filename="$2"
    destination="$staged_bundle/_internal/openlinktoken/core/ai/tokens/$filename"
    [[ -f "$destination" ]] && return

    manifest="$tmp_dir/olt-model-${version}-${model_platform}-${asset_id}.manifest"
    manifest_url="${RELEASES_URL}/download/${tag}/$(basename "$manifest")"
    legacy_manifest=false
    if ! curl -fL --retry 3 --output "$manifest" "$manifest_url"; then
        if [[ "$asset_id" == "model-data" && "$model_platform" == "linux-x64" ]]; then
            legacy_manifest="$tmp_dir/olt-model-${version}-linux-x64.manifest"
            curl -fL --retry 3 --output "$legacy_manifest" \
                "${RELEASES_URL}/download/${tag}/$(basename "$legacy_manifest")" ||
                fail "ML1 model asset manifest not found for $tag"
            manifest="$legacy_manifest"
            legacy_manifest=true
        else
            fail "ML1 model asset manifest not found for $tag"
        fi
    fi

    IFS=$'\t' read -r manifest_kind model_checksum manifest_extra < "$manifest" ||
        fail "Invalid ML1 model asset manifest"
    [[ "$manifest_kind" == "sha256" && "$model_checksum" =~ ^[[:xdigit:]]{64}$ && -z "${manifest_extra:-}" ]] ||
        fail "Invalid ML1 model asset manifest"

    if [[ "$legacy_manifest" == true ]]; then
        part_prefix="olt-model-${version}-linux-x64-part-"
    else
        part_prefix="olt-model-${version}-${model_platform}-${asset_id}-part-"
    fi
    model_data="$tmp_dir/$filename"
    : > "$model_data"
    part_count=0
    while IFS=$'\t' read -r entry_kind expected_checksum model_asset extra; do
        [[ "$entry_kind" == "part" && "$expected_checksum" =~ ^[[:xdigit:]]{64}$ &&
            -n "$model_asset" && -z "${extra:-}" ]] || fail "Invalid ML1 model asset manifest entry"
        [[ "$model_asset" == "$part_prefix"* && "$model_asset" == *.bin && "$model_asset" != */* ]] ||
            fail "Invalid ML1 model asset name in manifest"
        part_number="${model_asset#"$part_prefix"}"
        part_number="${part_number%.bin}"
        [[ "$part_number" =~ ^[0-9]{3}$ ]] || fail "Invalid ML1 model asset part number"
        expected_part_number=$(printf '%03d' "$((part_count + 1))")
        [[ "$part_number" == "$expected_part_number" ]] || fail "Unexpected ML1 model asset part order"

        part_path="$tmp_dir/$model_asset"
        curl -fL --retry 3 --output "$part_path" "${RELEASES_URL}/download/${tag}/${model_asset}" ||
            fail "ML1 model asset part not found: $model_asset"
        verify_sha256 "$expected_checksum" "$part_path" "$model_asset"
        cat "$part_path" >> "$model_data" || fail "Unable to assemble ML1 model asset"
        part_count=$((part_count + 1))
    done < <(tail -n +2 "$manifest")

    ((part_count > 0)) || fail "ML1 model asset manifest contains no parts"
    verify_sha256 "$model_checksum" "$model_data" "assembled $filename"
    mkdir -p "$(dirname "$destination")"
    mv "$model_data" "$destination"
}

while (($# > 0)); do
    case "$1" in
        --version|-v)
            (($# >= 2)) || fail "$1 requires a value"
            version="$2"
            shift 2
            ;;
        --install-dir)
            (($# >= 2)) || fail "$1 requires a value"
            install_dir="$2"
            shift 2
            ;;
        --no-cuda)
            no_cuda=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            fail "Unknown option: $1"
            ;;
    esac
done

command -v curl >/dev/null 2>&1 || fail "curl is required"
command -v unzip >/dev/null 2>&1 || fail "unzip is required"

if [[ -z "$version" ]]; then
    release_json=$(curl -fsSL -H "Accept: application/vnd.github+json" "${API_URL}/releases/latest") ||
        fail "Unable to resolve the latest release"
    version=$(printf '%s\n' "$release_json" |
        sed -nE 's/^[[:space:]]*"tag_name":[[:space:]]*"([^"]+)".*/\1/p' |
        head -n 1)
fi

[[ "$version" =~ ^v?[0-9]+(\.[0-9]+){2}([.-][0-9A-Za-z.-]+)?$ ]] ||
    fail "Invalid version: $version"
version="${version#v}"
version="${version#V}"
tag="v${version}"

case "$(uname -s)" in
    Darwin)
        case "$(uname -m)" in
            arm64|aarch64)
                asset="olt-cli-${version}-macos-arm64.zip"
                legacy_asset="olt-cli-${version}-macos-universal.zip"
                model_platform="macos-arm64"
                ;;
            x86_64|amd64)
                asset="olt-cli-${version}-macos-x86_64.zip"
                legacy_asset="olt-cli-${version}-macos-universal.zip"
                model_platform="macos-x86_64"
                ;;
            *)
                fail "No macOS CLI asset is available for architecture $(uname -m)"
                ;;
        esac
        ;;
    Linux)
        case "$(uname -m)" in
            x86_64|amd64)
                asset="olt-cli-${version}-linux-x64.zip"
                model_platform="linux-x64"
                ;;
            *)
                fail "No Linux CLI asset is available for architecture $(uname -m)"
                ;;
        esac
        install_cuda=true
        ;;
    *)
        install_cuda=false
        fail "This installer supports macOS and Linux only"
        ;;
esac

if [[ "$no_cuda" == true ]]; then
    install_cuda=false
fi
if [[ "$(uname -s)" == "Darwin" ]]; then
    install_cuda=false
fi

tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/olt-install.XXXXXX")
trap 'rm -rf "$tmp_dir"' EXIT

archive="$tmp_dir/$asset"
checksum_file="${archive}.sha256"
download_url="${RELEASES_URL}/download/${tag}/${asset}"

printf 'Downloading Open Link Token %s...\n' "$tag"
if ! curl -fL --retry 3 --output "$archive" "$download_url"; then
    if [[ -n "${legacy_asset:-}" ]]; then
        asset="$legacy_asset"
        archive="$tmp_dir/$asset"
        checksum_file="${archive}.sha256"
        download_url="${RELEASES_URL}/download/${tag}/${asset}"
        printf 'Architecture-specific asset unavailable; trying legacy %s...\n' "$asset"
        curl -fL --retry 3 --output "$archive" "$download_url" ||
            fail "Release asset not found: $asset"
    else
        fail "Release asset not found: $asset"
    fi
fi
curl -fL --retry 3 --output "$checksum_file" "${download_url}.sha256" ||
    fail "Checksum asset not found for $asset"

expected_checksum=$(awk 'NF { print $1; exit }' "$checksum_file")
verify_sha256 "$expected_checksum" "$archive" "$asset"

extract_dir="$tmp_dir/extracted"
mkdir -p "$extract_dir"
unzip -q "$archive" -d "$extract_dir"
binary=$(find "$extract_dir" -type f -name olt -print -quit)
[[ -n "$binary" ]] || fail "Release archive does not contain the olt executable"
bundle_source=$(dirname "$binary")

mkdir -p "$install_dir"
bundle_dir="$install_dir/.olt"
staged_bundle="$tmp_dir/staged-bundle"
cp -R "$bundle_source/." "$staged_bundle"
chmod 0755 "$staged_bundle/olt"

printf 'Downloading required ML1 model assets when missing...\n'
install_model_asset "model" "model.onnx"
install_model_asset "model-data" "model.onnx.data"

if [[ "$install_cuda" == true ]]; then
    if [[ -n "$(find "$staged_bundle/_internal/nvidia" -type f -print -quit 2>/dev/null)" ]]; then
        printf 'NVIDIA runtime already included in the CLI archive.\n'
    else
        printf 'Installing the NVIDIA CUDA runtime by default (use --no-cuda to skip)...\n'
        cuda_manifest="$tmp_dir/olt-cuda-${version}-linux-x64.manifest"
        cuda_manifest_url="${RELEASES_URL}/download/${tag}/olt-cuda-${version}-linux-x64.manifest"
        curl -fL --retry 3 --output "$cuda_manifest" "$cuda_manifest_url" ||
            fail "CUDA runtime manifest not found for $tag"

        cuda_part_prefix="olt-cuda-${version}-linux-x64-part-"
        cuda_part_count=0
        while IFS=$'\t' read -r expected_checksum cuda_asset extra; do
            [[ -n "$expected_checksum" && -n "$cuda_asset" && -z "${extra:-}" ]] ||
                fail "Invalid CUDA runtime manifest entry"
            [[ "$cuda_asset" == "$cuda_part_prefix"* && "$cuda_asset" == *.zip ]] ||
                fail "Invalid CUDA runtime asset name in manifest"
            part_number="${cuda_asset#"$cuda_part_prefix"}"
            part_number="${part_number%.zip}"
            [[ "$part_number" =~ ^[0-9]{3}$ ]] || fail "Invalid CUDA runtime part number"

            cuda_archive="$tmp_dir/$cuda_asset"
            cuda_url="${RELEASES_URL}/download/${tag}/${cuda_asset}"
            printf 'Downloading CUDA runtime part %s...\n' "$part_number"
            curl -fL --retry 3 --output "$cuda_archive" "$cuda_url" ||
                fail "CUDA runtime part not found: $cuda_asset"
            verify_sha256 "$expected_checksum" "$cuda_archive" "$cuda_asset"

            cuda_entries="$tmp_dir/${cuda_asset}.entries"
            unzip -Z1 "$cuda_archive" > "$cuda_entries" ||
                fail "Unable to list CUDA runtime part: $cuda_asset"
            while IFS= read -r cuda_entry; do
                [[ "$cuda_entry" == nvidia/* ]] || fail "Invalid path in CUDA runtime part: $cuda_entry"
                case "/$cuda_entry/" in
                    *"/../"*|*"/./"*) fail "Invalid path in CUDA runtime part: $cuda_entry" ;;
                esac
            done < "$cuda_entries"
            unzip -o -q "$cuda_archive" -d "$staged_bundle/_internal" ||
                fail "Unable to extract CUDA runtime part: $cuda_asset"
            cuda_part_count=$((cuda_part_count + 1))
        done < "$cuda_manifest"

        ((cuda_part_count > 0)) || fail "CUDA runtime manifest contains no parts"
        [[ -n "$(find "$staged_bundle/_internal/nvidia" -type f -print -quit 2>/dev/null)" ]] ||
            fail "CUDA runtime parts contain no NVIDIA libraries"
    fi
elif [[ -d "$staged_bundle/_internal/nvidia" ]]; then
    rm -rf -- "$staged_bundle/_internal/nvidia"
    printf 'Installing the CPU-only runtime.\n'
else
    printf 'Installing the CPU-only runtime.\n'
fi

old_bundle="$install_dir/.olt.previous.$$"
if [[ -e "$bundle_dir" || -L "$bundle_dir" ]]; then
    mv "$bundle_dir" "$old_bundle"
fi
if ! mv "$staged_bundle" "$bundle_dir"; then
    [[ -e "$old_bundle" ]] && mv "$old_bundle" "$bundle_dir"
    fail "Unable to install the CLI bundle into $bundle_dir"
fi
rm -rf "$old_bundle"

launcher_tmp="$install_dir/.olt-launcher.$$"
ln -s "$bundle_dir/olt" "$launcher_tmp"
mv -f "$launcher_tmp" "$install_dir/olt"

printf 'Installed olt %s to %s/olt\n' "$tag" "$install_dir"
case ":${PATH:-}:" in
    *":${install_dir}:"*) ;;
    *) printf 'Add %s to PATH to run olt from any shell.\n' "$install_dir" ;;
esac
