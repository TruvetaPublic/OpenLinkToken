#!/usr/bin/env bash
set -euo pipefail

echo "=== Setting up Python environment ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REFRESH_WORKSPACE_ONLY=0
VENV_DIR="${UV_PROJECT_ENVIRONMENT:-/home/vscode/.local/share/opentoken/.venv}"

if [ "${1:-}" = "--refresh-workspace" ]; then
  REFRESH_WORKSPACE_ONLY=1
fi

WORKSPACE_VENV_DIR="$REPO_ROOT/.venv"

cd "$REPO_ROOT"

# Install UV if not already present
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing UV..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

DEFAULT_UV_CACHE_DIR="/home/vscode/.cache/uv"
if mkdir -p "$DEFAULT_UV_CACHE_DIR" 2>/dev/null && [ -w "$DEFAULT_UV_CACHE_DIR" ]; then
  export UV_CACHE_DIR="$DEFAULT_UV_CACHE_DIR"
else
  export UV_CACHE_DIR="$REPO_ROOT/.cache/uv"
  mkdir -p "$UV_CACHE_DIR"
fi

mkdir -p "$VENV_DIR"
if [ "$(id -u)" -eq 0 ]; then
  chown -R "$(id -u)":"$(id -g)" "$VENV_DIR" 2>/dev/null || true
else
  if command -v sudo >/dev/null 2>&1; then
    sudo chown -R "$(id -u)":"$(id -g)" "$VENV_DIR" 2>/dev/null || true
  fi
fi

echo "Creating virtual environment at $VENV_DIR"
uv venv --allow-existing --seed "$VENV_DIR"

if [ "$WORKSPACE_VENV_DIR" != "$VENV_DIR" ]; then
  if [ -e "$WORKSPACE_VENV_DIR" ] && [ ! -L "$WORKSPACE_VENV_DIR" ]; then
    echo "Replacing workspace-local .venv with symlink to shared environment..."
    rm -rf "$WORKSPACE_VENV_DIR"
  fi

  if [ ! -L "$WORKSPACE_VENV_DIR" ] || [ "$(readlink -f "$WORKSPACE_VENV_DIR")" != "$VENV_DIR" ]; then
    ln -sfn "$VENV_DIR" "$WORKSPACE_VENV_DIR"
  fi
fi

export UV_PROJECT_ENVIRONMENT="$VENV_DIR"

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "Installing all workspace packages and dependencies"
cd "$REPO_ROOT"
uv sync --all-packages --dev

if [ "$REFRESH_WORKSPACE_ONLY" -eq 1 ]; then
  echo "Refreshing workspace packages complete"
else
  echo "Installing prek (this may take a few minutes)"
  "$VENV_DIR/bin/pip" install prek

  echo "Installing prek hooks and environments (long-running operation)"
  "$VENV_DIR/bin/prek" install --install-hooks || echo "Warning: Could not install prek hooks (this is normal if git is not initialized)"
fi

echo "✓ Python environment setup complete at $VENV_DIR"
echo "To activate manually, run: source $VENV_DIR/bin/activate"
