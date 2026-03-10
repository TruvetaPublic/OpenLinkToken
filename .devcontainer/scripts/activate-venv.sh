#!/usr/bin/env bash

# Ensure virtual environment activation is added to shell rc files
grep -qF 'opentoken/.venv/bin/activate' ~/.bashrc 2>/dev/null || echo 'source /home/vscode/.local/share/opentoken/.venv/bin/activate 2>/dev/null || true' >> ~/.bashrc

grep -qF 'opentoken/.venv/bin/activate' ~/.zshrc 2>/dev/null || echo 'source /home/vscode/.local/share/opentoken/.venv/bin/activate 2>/dev/null || true' >> ~/.zshrc
