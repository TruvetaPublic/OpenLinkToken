#!/bin/bash
set -e

VENV_DIR="/home/vscode/.local/share/opentoken/.venv"
REPO_ROOT="$(git rev-parse --show-toplevel)"

echo "(!) Installing apm CLI"
if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "(!) Shared virtual environment not found at $VENV_DIR, creating it"
    uv venv --allow-existing --seed "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install apm-cli

echo "(!) Setting up SSH known hosts for GitHub"
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/known_hosts
chmod 600 ~/.ssh/known_hosts
if ! ssh-keygen -F github.com -f ~/.ssh/known_hosts >/dev/null 2>&1; then
    ssh-keyscan github.com >> ~/.ssh/known_hosts
fi

echo "(!) Running apm install"
apm install

GITIGNORE="$REPO_ROOT/.gitignore"

# After install, scan known apm output dirs for untracked paths and add to .gitignore.
# This is idempotent: safe to run on fresh installs or re-runs.
echo "(!) Updating .gitignore with apm-installed paths"
ADDED=0
while IFS= read -r entry; do
    if ! grep -qxF "$entry" "$GITIGNORE"; then
        if [ "$ADDED" -eq 0 ]; then
            echo "" >> "$GITIGNORE"
            echo "# Added by apm install" >> "$GITIGNORE"
            ADDED=1
        fi
        echo "$entry" >> "$GITIGNORE"
        echo "(!) Added to .gitignore: $entry"
    fi
done < <(git -C "$REPO_ROOT" ls-files --others --directory --exclude-standard .github/skills/ .github/prompts/ 2>/dev/null)
