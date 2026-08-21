#!/usr/bin/env bash

set -euo pipefail

readonly REPOSITORY="TruvetaPublic/OpenLinkToken"
readonly RELEASES_URL="https://github.com/${REPOSITORY}/releases"
readonly API_URL="https://api.github.com/repos/${REPOSITORY}"

version=""
install_dir="${OLT_INSTALL_DIR:-$HOME/.local/bin}"

usage() {
    cat <<'EOF'
Install the Open Link Token CLI for Linux or macOS.

Usage:
  install.sh [--version VERSION] [--install-dir DIRECTORY]

Options:
  --version VERSION       Install a specific release (default: latest)
  --install-dir DIRECTORY Install into DIRECTORY (default: ~/.local/bin)
  -h, --help              Show this help
EOF
}

fail() {
    printf 'Error: %s\n' "$1" >&2
    exit 1
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
        asset="olt-cli-${version}-macos-universal.zip"
        ;;
    Linux)
        case "$(uname -m)" in
            x86_64|amd64)
                asset="olt-cli-${version}-linux-x64.zip"
                ;;
            *)
                fail "No Linux CLI asset is available for architecture $(uname -m)"
                ;;
        esac
        ;;
    *)
        fail "This installer supports macOS and Linux only"
        ;;
esac

tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/olt-install.XXXXXX")
trap 'rm -rf "$tmp_dir"' EXIT

archive="$tmp_dir/$asset"
checksum_file="${archive}.sha256"
download_url="${RELEASES_URL}/download/${tag}/${asset}"

printf 'Downloading Open Link Token %s...\n' "$tag"
curl -fL --retry 3 --output "$archive" "$download_url" ||
    fail "Release asset not found: $asset"
curl -fL --retry 3 --output "$checksum_file" "${download_url}.sha256" ||
    fail "Checksum asset not found for $asset"

expected_checksum=$(awk 'NF { print $1; exit }' "$checksum_file")
[[ "$expected_checksum" =~ ^[[:xdigit:]]{64}$ ]] ||
    fail "Invalid SHA-256 checksum file"

if command -v shasum >/dev/null 2>&1; then
    actual_checksum=$(shasum -a 256 "$archive" | awk '{print $1}')
elif command -v sha256sum >/dev/null 2>&1; then
    actual_checksum=$(sha256sum "$archive" | awk '{print $1}')
else
    fail "shasum or sha256sum is required to verify the download"
fi

actual_checksum=$(printf '%s' "$actual_checksum" | tr '[:upper:]' '[:lower:]')
expected_checksum=$(printf '%s' "$expected_checksum" | tr '[:upper:]' '[:lower:]')
[[ "$actual_checksum" == "$expected_checksum" ]] ||
    fail "SHA-256 verification failed"

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
