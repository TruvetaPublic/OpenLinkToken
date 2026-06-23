#!/usr/bin/env bash
set -euo pipefail

echo ">>> prek hook: agentStop fired"

CHANGED=$(git diff --name-only HEAD 2>/dev/null)

if [ -z "$CHANGED" ]; then
  echo ">>> prek hook: no modified tracked files, skipping"
  exit 0
fi

echo ">>> prek hook: running on: $CHANGED"
prek run --files $CHANGED
