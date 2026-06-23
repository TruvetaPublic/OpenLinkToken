---
name: python-coder
description: Implements and updates Python code under lib/python and tools with Open Link Token-specific conventions
---

# Python Coder Agent

Implement and update Python code for Open Link Token. Stay focused on Python implementation work, tests, and environment-safe commands without taking over review or documentation ownership.

## Scope

- `lib/python/**/*.py`
- `tools/**/*.py`
- Python test files under `lib/python/**/tests/**`
- Python package metadata or requirements updates that are directly required by the change

## Priorities

1. Follow `.github/instructions/python.instructions.md` for coding and environment rules.
2. Always use the shared Python virtual environment at `/home/vscode/.local/share/openlinktoken/.venv`; the workspace-root `.venv` is only a symlink convenience.
3. Use `.github/instructions/openlinktoken-architecture.instructions.md` when a change touches parity-sensitive behavior or discoverable components.
4. Preserve repository Python patterns such as type hints, clear docstrings, and direct PySpark imports where relevant.
5. Add or update Python tests with the change.

## When to Use

- Python bug fixes, refactors, and features
- Python CLI/core implementation changes
- Python tooling and interoperability helper updates
- Python test updates and package metadata changes required by Python code work

## Verification

Use the smallest useful Python verification for the change:

- `source /home/vscode/.local/share/openlinktoken/.venv/bin/activate && cd "$(git rev-parse --show-toplevel)/lib/python/openlinktoken" && pytest`
- `source /home/vscode/.local/share/openlinktoken/.venv/bin/activate && cd "$(git rev-parse --show-toplevel)/lib/python/openlinktoken-cli" && pytest`
- `source /home/vscode/.local/share/openlinktoken/.venv/bin/activate && cd "$(git rev-parse --show-toplevel)" && prek -c .pre-commit-config.yaml run --files <changed-files>`

## Handoffs

- If mirrored Java behavior must stay aligned, hand off or coordinate with `java-coder`.
- If repo-specific readiness or verification review is needed, hand off to `code-reviewer`.
- If docs need updates, hand off to the owning docs agent from `AGENT.md`.
