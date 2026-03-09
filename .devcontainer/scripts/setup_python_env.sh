#!/usr/bin/env bash
set -euo pipefail

echo "=== Setting up Python environment ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR/../.."
REFRESH_WORKSPACE_ONLY=0

if [ "${1:-}" = "--refresh-workspace" ]; then
  REFRESH_WORKSPACE_ONLY=1
fi

SHARED_VENV_DIR="${UV_PROJECT_ENVIRONMENT:-/home/vscode/.local/share/opentoken/.venv}"
WORKSPACE_VENV_DIR="$REPO_ROOT/.venv"

cd "$REPO_ROOT"

# Install UV if not already present
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing UV..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# Create the shared venv at a stable container path so the clone folder name does not matter.
mkdir -p "$SHARED_VENV_DIR"
if [ "$(id -u)" -eq 0 ]; then
  chown -R "$(id -u)":"$(id -g)" "$SHARED_VENV_DIR" 2>/dev/null || true
else
  if command -v sudo >/dev/null 2>&1; then
    sudo chown -R "$(id -u)":"$(id -g)" "$SHARED_VENV_DIR" 2>/dev/null || true
  fi
fi

if [ ! -f "$SHARED_VENV_DIR/bin/activate" ]; then
  echo "Creating virtual environment..."
  uv venv "$SHARED_VENV_DIR"
else
  echo "Virtual environment already exists"
fi

if [ "$WORKSPACE_VENV_DIR" != "$SHARED_VENV_DIR" ]; then
  if [ -e "$WORKSPACE_VENV_DIR" ] && [ ! -L "$WORKSPACE_VENV_DIR" ]; then
    echo "Replacing workspace-local .venv with symlink to shared environment..."
    rm -rf "$WORKSPACE_VENV_DIR"
  fi

  if [ ! -L "$WORKSPACE_VENV_DIR" ] || [ "$(readlink -f "$WORKSPACE_VENV_DIR")" != "$SHARED_VENV_DIR" ]; then
    ln -sfn "$SHARED_VENV_DIR" "$WORKSPACE_VENV_DIR"
  fi
fi

export UV_PROJECT_ENVIRONMENT="$SHARED_VENV_DIR"

# shellcheck disable=SC1091
source "$SHARED_VENV_DIR/bin/activate"

cd "$REPO_ROOT/lib/python"

if [ "$REFRESH_WORKSPACE_ONLY" -eq 1 ]; then
  echo "Refreshing editable installs for the current workspace..."
  uv pip install \
    -e opentoken \
    -e opentoken-cli \
    -e "opentoken-pyspark[spark40]"
else
  echo "Installing Python packages..."
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
fi

cd "$REPO_ROOT"

if [ "$REFRESH_WORKSPACE_ONLY" -eq 0 ]; then
  echo "Installing prek git hooks..."
  prek install
fi

echo "✓ Python environment setup complete"
