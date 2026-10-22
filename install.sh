#!/usr/bin/env bash

set -euo pipefail

readonly REPOSITORY="TruvetaPublic/OpenLinkToken"
readonly RELEASES_URL="https://github.com/${REPOSITORY}/releases"
readonly API_URL="https://api.github.com/repos/${REPOSITORY}"
readonly MODEL_PACKAGE="ghcr.io/truvetapublic/openlinktoken-ml1-assets"
readonly ORAS_VERSION="1.3.3"

version=""
install_dir="${OLT_INSTALL_DIR:-$HOME/.local/bin}"
model_tag="${OLT_ML1_MODEL_TAG:-v1}"
no_cuda=false

usage() {
    cat <<'EOF'
Install the Open Link Token CLI for Linux or macOS.

Usage:
  install.sh [--version VERSION] [--model-tag TAG] [--install-dir DIRECTORY] [--no-cuda]

Options:
  --version VERSION       Install a specific release (default: latest)
  --model-tag TAG         Install this ML1 model tag (default: v1 or OLT_ML1_MODEL_TAG)
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

install_ml1_assets() {
    local model_root oras_dir oras_archive oras_checksum oras_url oras_binary model_assets_dir
    local filename metadata expected_checksum expected_size actual_size
    model_root="$staged_bundle/_internal/openlinktoken/core/ai/tokens"
    if [[ -s "$model_root/model.onnx" && -s "$model_root/model.onnx.data" &&
        -s "$model_root/tokenizer.json" && -s "$model_root/asset-manifest.json" ]]; then
        printf 'ML1 model assets are already included in the CLI archive.\n'
        return
    fi

    case "$(uname -s):$(uname -m)" in
        Linux:x86_64|Linux:amd64)
            oras_archive="oras_${ORAS_VERSION}_linux_amd64.tar.gz"
            oras_checksum="9ce999f8d2de03fc03968b29d743077a58783e545e5eaa53917ca177352d0e59"
            ;;
        Darwin:x86_64|Darwin:amd64)
            oras_archive="oras_${ORAS_VERSION}_darwin_amd64.tar.gz"
            oras_checksum="aeb684d8c24c18dce28fd1f7326636e4782b573108e244a93d4b1c4a5ec50f48"
            ;;
        Darwin:arm64|Darwin:aarch64)
            oras_archive="oras_${ORAS_VERSION}_darwin_arm64.tar.gz"
            oras_checksum="f33fc12753c54172b0d0d19eaa0318d3f90fe9b094d96e8b259c881713c92e1c"
            ;;
        *)
            fail "No ORAS binary is available for $(uname -s) $(uname -m)"
            ;;
    esac

    oras_dir="$tmp_dir/oras"
    mkdir -p "$oras_dir"
    oras_url="https://github.com/oras-project/oras/releases/download/v${ORAS_VERSION}/${oras_archive}"
    oras_archive="$oras_dir/$oras_archive"
    printf 'Downloading ORAS %s...\n' "$ORAS_VERSION"
    curl -fL --retry 3 --output "$oras_archive" "$oras_url" || fail "Unable to download ORAS"
    verify_sha256 "$oras_checksum" "$oras_archive" "ORAS $ORAS_VERSION"
    tar -xzf "$oras_archive" -C "$oras_dir" oras || fail "Unable to extract ORAS"
    oras_binary="$oras_dir/oras"

    model_assets_dir="$tmp_dir/ml1-assets"
    mkdir -p "$model_assets_dir"
    printf 'Downloading ML1 model assets %s...\n' "$model_tag"
    "$oras_binary" pull "${MODEL_PACKAGE}:${model_tag}" --output "$model_assets_dir" ||
        fail "Unable to pull ML1 model assets ${MODEL_PACKAGE}:${model_tag}; ensure the GHCR package is public"
    for filename in model.onnx model.onnx.data tokenizer.json asset-manifest.json; do
        [[ -s "$model_assets_dir/$filename" ]] || fail "ML1 OCI artifact is missing $filename"
    done
    for filename in model.onnx model.onnx.data tokenizer.json; do
        metadata=$(awk -v asset="\"$filename\"" '
            index($0, asset) { in_asset = 1; next }
            in_asset && /"sha256"[[:space:]]*:/ {
                sub(/^.*"sha256"[[:space:]]*:[[:space:]]*"/, "")
                sub(/".*$/, "")
                checksum = $0
            }
            in_asset && /"size"[[:space:]]*:/ {
                sub(/^.*"size"[[:space:]]*:[[:space:]]*/, "")
                sub(/[,[:space:]]*$/, "")
                print checksum "\t" $0
                exit
            }
            in_asset && /}/ { in_asset = 0 }
        ' "$model_assets_dir/asset-manifest.json")
        IFS=$'\t' read -r expected_checksum expected_size <<< "$metadata"
        [[ "$expected_checksum" =~ ^[[:xdigit:]]{64}$ && "$expected_size" =~ ^[0-9]+$ ]] ||
            fail "Invalid ML1 asset manifest entry for $filename"
        verify_sha256 "$expected_checksum" "$model_assets_dir/$filename" "$filename"
        actual_size=$(wc -c < "$model_assets_dir/$filename" | tr -d '[:space:]')
        [[ "$actual_size" == "$expected_size" ]] || fail "Unexpected size for ML1 asset $filename"
    done
    mkdir -p "$model_root"
    cp "$model_assets_dir"/{model.onnx,model.onnx.data,tokenizer.json,asset-manifest.json} "$model_root/" ||
        fail "Unable to install ML1 model assets"
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
        --model-tag)
            (($# >= 2)) || fail "$1 requires a value"
            model_tag="$2"
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
[[ "$model_tag" =~ ^v[0-9]+$ ]] || fail "Invalid ML1 model tag: $model_tag (expected vN)"
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

install_ml1_assets

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
