#!/usr/bin/env bash
set -euo pipefail

echo "=== Setting up Python environment ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/../.."

cd "$REPO_ROOT"

# Install UV if not already present
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing UV..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# Create venv at repo root (handles cases where mount exists but env not yet created)
mkdir -p .venv
if [ "$(id -u)" -eq 0 ]; then
  chown -R "$(id -u)":"$(id -g)" .venv 2>/dev/null || true
else
  if command -v sudo >/dev/null 2>&1; then
    sudo chown -R "$(id -u)":"$(id -g)" .venv 2>/dev/null || true
  fi
fi

if [ ! -f .venv/bin/activate ]; then
  echo "Creating virtual environment..."
  uv venv .venv
else
  echo "Virtual environment already exists"
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# Install all requirements in a single uv call to reduce file handle usage
echo "Installing Python packages..."
cd "$REPO_ROOT/lib/python"
uv pip install \
  -r opentoken/requirements.txt \
  -r opentoken-cli/requirements.txt \
  -r opentoken-pyspark/requirements.txt \
  -r dev-requirements.txt \
  -e opentoken \
  -e opentoken-cli \
  -e "opentoken-pyspark[spark40]" \
  prek \
  autoflake

cd "$REPO_ROOT"
echo "Installing prek git hooks..."
prek install

echo "✓ Python environment setup complete"
