#!/usr/bin/env bash
set -euo pipefail

echo "=== Open Link Token Unified Setup ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_DIR="${UV_PROJECT_ENVIRONMENT:-/home/vscode/.local/share/openlinktoken/.venv}"
WORKSPACE_VENV_DIR="$REPO_ROOT/.venv"
STATE_DIR="${VENV_DIR}/.setup-state"
PHASE="${1:-full}"  # Options: full, post-create, post-start, post-attach

mkdir -p "$STATE_DIR"

# Marker functions for tracking completed steps
mark_complete() {
  local step="$1"
  touch "$STATE_DIR/$step"
}

is_complete() {
  local step="$1"
  [ -f "$STATE_DIR/$step" ]
}

skip_if_complete() {
  local step="$1"
  local msg="$2"
  if is_complete "$step"; then
    echo "⊘ Skipping $msg (already completed)"
    return 0
  fi
  return 1
}

# ============================================================================
# Core setup steps (always needed, idempotent)
# ============================================================================

step_install_uv() {
  skip_if_complete "uv-installed" "UV installation" && return 0

  if ! command -v uv >/dev/null 2>&1; then
    echo "→ Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
  fi
  mark_complete "uv-installed"
}

step_setup_cache_dir() {
  skip_if_complete "cache-setup" "cache directory setup" && return 0

  echo "→ Setting up UV cache directory"
  DEFAULT_UV_CACHE_DIR="/home/vscode/.cache/uv"
  if mkdir -p "$DEFAULT_UV_CACHE_DIR" 2>/dev/null && [ -w "$DEFAULT_UV_CACHE_DIR" ]; then
    export UV_CACHE_DIR="$DEFAULT_UV_CACHE_DIR"
  else
    export UV_CACHE_DIR="$REPO_ROOT/.cache/uv"
    mkdir -p "$UV_CACHE_DIR"
  fi
  mark_complete "cache-setup"
}

step_create_venv() {
  skip_if_complete "venv-created" "virtual environment creation" && return 0

  echo "→ Creating virtual environment at $VENV_DIR"
  mkdir -p "$VENV_DIR"
  if [ "$(id -u)" -eq 0 ]; then
    chown -R "$(id -u)":"$(id -g)" "$VENV_DIR" 2>/dev/null || true
  else
    if command -v sudo >/dev/null 2>&1; then
      sudo chown -R "$(id -u)":"$(id -g)" "$VENV_DIR" 2>/dev/null || true
    fi
  fi

  uv venv --allow-existing --seed "$VENV_DIR"
  mark_complete "venv-created"
}

step_symlink_venv() {
  skip_if_complete "venv-symlink" "workspace .venv symlink" && return 0

  if [ "$WORKSPACE_VENV_DIR" != "$VENV_DIR" ]; then
    if [ -e "$WORKSPACE_VENV_DIR" ] && [ ! -L "$WORKSPACE_VENV_DIR" ]; then
      echo "→ Replacing workspace-local .venv with symlink to shared environment..."
      rm -rf "$WORKSPACE_VENV_DIR"
    fi

    if [ ! -L "$WORKSPACE_VENV_DIR" ] || [ "$(readlink "$WORKSPACE_VENV_DIR" 2>/dev/null || true)" != "$VENV_DIR" ]; then
      ln -sfn "$VENV_DIR" "$WORKSPACE_VENV_DIR"
    fi
  fi
  mark_complete "venv-symlink"
}

step_activate_venv() {
  export UV_PROJECT_ENVIRONMENT="$VENV_DIR"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
}

step_install_packages() {
  echo "→ Installing all workspace packages and dependencies"
  cd "$REPO_ROOT"
  uv sync --all-packages --dev

  echo "→ Installing default PySpark bridge runtime (Spark 4.0)"
  uv pip install -e "lib/python/openlinktoken-pyspark[spark40]"
}

step_activate_shell_init() {
  echo "→ Adding venv activation to shell rc files"
  local activation_line="source $VENV_DIR/bin/activate 2>/dev/null || true"

  grep -qF "$activation_line" ~/.bashrc 2>/dev/null || echo "$activation_line" >> ~/.bashrc

  grep -qF "$activation_line" ~/.zshrc 2>/dev/null || echo "$activation_line" >> ~/.zshrc
}

# ============================================================================
# Full setup: prek installation (expensive, only on first creation)
# ============================================================================

step_install_prek() {
  skip_if_complete "prek-installed" "prek installation" && return 0

  echo "→ Installing prek (this may take a few minutes)"
  "$VENV_DIR/bin/pip" install prek

  echo "→ Installing prek hooks and environments (long-running operation)"
  "$VENV_DIR/bin/prek" install --install-hooks || \
    echo "⚠ Warning: Could not install prek hooks (this is normal if git is not initialized)"

  mark_complete "prek-installed"
}

# ============================================================================
# APM setup
# ============================================================================

step_install_rtk() {
  skip_if_complete "rtk-installed" "rtk installation" && return 0

  if command -v rtk >/dev/null 2>&1; then
    echo "⊘ Skipping rtk installation (already installed)"
    mark_complete "rtk-installed"
    return 0
  fi

  echo "→ Installing rtk (Rust Token Killer) for token optimization"
  curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"

  mark_complete "rtk-installed"
}

step_install_bun() {
  skip_if_complete "bun-installed" "bun installation" && return 0

  echo "→ Installing bun"
  curl -fsSL https://bun.sh/install | bash
  export PATH="$HOME/.local/share/bun/bin:$PATH"
  mark_complete "bun-installed"
}

step_install_opencode_auto_resume() {
  skip_if_complete "opencode-auto-resume-installed" "opencode-auto-resume installation" && return 0

  echo "→ Installing opencode-auto-resume"
  npm install -g opencode-auto-resume
  mark_complete "opencode-auto-resume-installed"
}

step_install_apm_cli() {
  echo "→ Installing apm CLI"
  uv pip install apm-cli
}

step_setup_apm() {
  echo "→ Setting up SSH known hosts for GitHub"
  mkdir -p ~/.ssh
  chmod 700 ~/.ssh
  touch ~/.ssh/known_hosts
  chmod 600 ~/.ssh/known_hosts
  if ! ssh-keygen -F github.com -f ~/.ssh/known_hosts >/dev/null 2>&1; then
    ssh-keyscan github.com >> ~/.ssh/known_hosts 2>/dev/null || true
  fi

  git config --global --add safe.directory "$REPO_ROOT" 2>/dev/null || true

  if git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    echo "→ Running apm install"
    cd "$REPO_ROOT"
    apm install --target copilot || echo "⚠ Warning: apm install failed (continuing anyway)"

    # Update .gitignore with apm-installed paths
    GITIGNORE="$REPO_ROOT/.gitignore"
    if [ -f "$GITIGNORE" ]; then
      echo "→ Updating .gitignore with apm-installed paths"
      ADDED=0
      while IFS= read -r entry; do
        if ! grep -qxF "$entry" "$GITIGNORE"; then
          if [ "$ADDED" -eq 0 ]; then
            echo "" >> "$GITIGNORE"
            echo "# Added by apm install" >> "$GITIGNORE"
            ADDED=1
          fi
          echo "$entry" >> "$GITIGNORE"
          echo "  Added to .gitignore: $entry"
        fi
      done < <(git -C "$REPO_ROOT" ls-files --others --directory --exclude-standard .github/skills/ .github/prompts/ 2>/dev/null || true)
    fi
  fi
}

# ============================================================================
# Refresh workspace packages (lightweight update)
# ============================================================================

step_refresh_packages() {
  echo "→ Refreshing workspace packages"
  cd "$REPO_ROOT"
  uv sync --all-packages --dev
  echo "✓ Workspace packages refreshed"
}

# ============================================================================
# Main execution logic
# ============================================================================

run_core_setup() {
  step_install_uv
  step_setup_cache_dir
  step_create_venv
  step_symlink_venv
  step_activate_venv
}

run_full_setup() {
  run_core_setup
  step_install_packages
  step_activate_shell_init
  step_install_prek
  step_install_apm_cli
  step_setup_apm
  step_install_rtk
  step_install_bun
  step_install_opencode_auto_resume
}

run_refresh_setup() {
  run_core_setup
  step_refresh_packages
  step_activate_shell_init
  step_install_apm_cli
  step_setup_apm
}

main() {
  cd "$REPO_ROOT"

  echo "Phase: $PHASE"
  case "$PHASE" in
    full|post-create)
      run_full_setup
      ;;
    post-start)
      run_core_setup
      step_install_apm_cli
      step_setup_apm
      ;;
    post-attach)
      run_refresh_setup
      ;;
    *)
      echo "Unknown setup phase: $PHASE" >&2
      exit 1
      ;;
  esac

  echo ""
  echo "✓ Setup complete (phase: $PHASE)"
  echo "To activate manually, run: source $VENV_DIR/bin/activate"
}

main "$@"
