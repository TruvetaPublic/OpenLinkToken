# `.github/actions`

Reusable GitHub Actions building blocks live here.

## Contents

| Path               | Purpose                                                                                                      |
| ------------------ | ------------------------------------------------------------------------------------------------------------ |
| `setup-toolchain/` | Composite action that prepares the Java and Python toolchains used by CI, publishing, and release workflows. |

## Editing guidance

- Prefer adding shared workflow setup here instead of duplicating the same steps across multiple workflow files.
- Keep `action.yml` inputs and descriptions current so workflow authors can understand how to use the action without opening the implementation.
- When changing this folder, review the workflow callers under [`../workflows/`](../workflows/README.md).

## Related files

- Runtime repo guidance: [`../copilot-instructions.md`](../copilot-instructions.md)
- Workflow consumers: [`../workflows/`](../workflows/README.md)
