---
layout: default
---

# Managing Extensions

Operator guide for installing, listing, and removing OpenToken CLI extensions. Extensions add top-level subcommands to the CLI without requiring a CLI upgrade.

---

## Installing an Extension

### From a URL

```bash
opentoken extension install https://example.com/opentoken-ext-hello-world-1.0.0-py3-none-any.whl
```

The CLI prints a security warning and prompts for confirmation before installing. Review the source URL carefully — extensions run with the same privileges as the CLI process.

### From a Local File

Use the `file://` scheme to install from a local `.whl` file:

```bash
opentoken extension install file:///path/to/opentoken_ext_hello_world-1.0.0-py3-none-any.whl
```

Use an absolute path in the `file://` URL.

### Skipping Confirmation

Pass `--yes` to suppress the confirmation prompt. Use this in CI pipelines or container builds where you have already validated the source:

```bash
opentoken extension install --yes https://example.com/opentoken-ext-hello-world-1.0.0-py3-none-any.whl
```

### What Install Does

The exact steps depend on how OpenToken is installed:

**Python package mode** (pip install / source install — the common case):

1. Installs the wheel via `pip` into the active Python environment's site-packages.
2. Records the extension metadata in `~/.opentoken/extensions/registry.json` (or `$OPENTOKEN_EXTENSIONS_DIR/registry.json`).
3. Prints the installed extension name, version, and command name.

**Frozen binary mode** (PyInstaller binary):

1. Extracts the wheel contents into `~/.opentoken/extensions/<name>/src/` (or `$OPENTOKEN_EXTENSIONS_DIR/<name>/src/`).
2. Records the extension metadata in `~/.opentoken/extensions/registry.json` (or `$OPENTOKEN_EXTENSIONS_DIR/registry.json`).
3. Prints the installed extension name, version, and command name.

---

## Listing Installed Extensions

```bash
opentoken extension list
```

Sample output:

```
Name          Version  Command       Source
hello-world   1.0.0    hello-world   file:///home/user/dist/opentoken_ext_hello_world-1.0.0-py3-none-any.whl
```

| Column  | Description                                        |
| ------- | -------------------------------------------------- |
| Name    | Extension package name as recorded in the registry |
| Version | SemVer version string                              |
| Command | Top-level subcommand added to the CLI              |
| Source  | URL or `file://` path used at install time         |

If no extensions are installed, the command prints `No extensions installed.`.

---

## Uninstalling an Extension

```bash
opentoken extension uninstall <name>
```

The CLI removes the extension package from the extensions directory and deletes its entry from `registry.json`. The corresponding subcommand is no longer available after the next CLI invocation.

---

## Upgrading an Extension

There is no `opentoken extension update` subcommand. To upgrade an installed extension, reinstall it with the new wheel URL:

```bash
opentoken extension install https://example.com/opentoken-ext-hello-world-2.0.0-py3-none-any.whl
```

When the extension is already installed, `install` replaces it in-place with the new version.

If you prefer an explicit two-step approach, uninstall the old version first:

```bash
opentoken extension uninstall hello-world
opentoken extension install https://example.com/opentoken-ext-hello-world-2.0.0-py3-none-any.whl
```

The two-step approach is useful when you want to confirm the old version is cleanly removed before installing a newer one, or when switching to a wheel from a different source URL.

---

## Using `OPENTOKEN_EXTENSIONS_DIR` in CI/Containers

By default, extensions install to `~/.opentoken/extensions/`. Set `OPENTOKEN_EXTENSIONS_DIR` to override this path:

```bash
export OPENTOKEN_EXTENSIONS_DIR=/opt/opentoken/extensions
opentoken extension install --yes https://example.com/opentoken-my-ext-1.0.0-py3-none-any.whl
```

This is useful when:

- Running OpenToken in a container where the home directory is ephemeral.
- Sharing a single extensions directory across multiple users or CI agents.
- Pre-baking extensions into a Docker image layer at a predictable path.

**Docker example:**

```dockerfile
ENV OPENTOKEN_EXTENSIONS_DIR=/opt/opentoken/extensions
RUN opentoken extension install --yes \
    https://example.com/opentoken-my-ext-1.0.0-py3-none-any.whl
```

The registry file (`registry.json`) is always written to the same directory as the installed extensions, regardless of the `OPENTOKEN_EXTENSIONS_DIR` value.

---

## Binary vs. Python Package Install Differences

OpenToken is distributed both as a pre-built PyInstaller binary and as a Python package (`pip install opentoken-cli`). The extension system behaves differently under each.

| Behaviour                                  | Python package                    | PyInstaller binary                     |
| ------------------------------------------ | --------------------------------- | -------------------------------------- |
| Discovery                                  | `importlib.metadata` entry points | `registry.json` + `sys.path` injection |
| Tier-1 extensions (zero-dep)               | ✅ Supported                      | ✅ Supported                           |
| Tier-2 extensions (OpenToken-bundled deps) | ✅ Supported                      | ✅ Supported                           |
| Tier-3 extensions (external deps)          | ✅ Supported                      | ❌ Rejected at install                 |

Tier-3 extensions depend on packages that are not bundled in the binary. `opentoken extension install` detects this and aborts with a clear error message that includes the missing package names and instructions for switching to a Python package install.

If you need Tier-3 extensions, install OpenToken as a Python package:

```bash
pip install opentoken-cli
opentoken extension install <url>
```

---

## Troubleshooting

### Extension does not appear in `opentoken --help`

1. Confirm it is listed in `opentoken extension list`.
2. Check for a load warning at startup. Load warnings are printed to stderr. The format depends on the install mode:

   Python package mode (entry-point track):

   ```
   Failed to load extension from entry point 'hello-world': ModuleNotFoundError: No module named 'opentoken_ext_hello_world'
   ```

   Frozen binary mode (registry track):

   ```
   Failed to load extension 'hello-world' from registry: ModuleNotFoundError: No module named 'opentoken_ext_hello_world'
   ```

3. Verify that `OPENTOKEN_EXTENSIONS_DIR` is set consistently between install and runtime environments.

### `ModuleNotFoundError` on load

The extension package or one of its dependencies is not importable. Common causes:

- The extension was installed under a different Python environment than the one running `opentoken`.
- The extension directory is missing or was moved after install.
- The extension depends on a Tier-3 package that is not installed in the current environment.

Re-install the extension to ensure the package is in the correct location.

### Tier-3 rejection under the binary

```
Error: This extension requires external dependencies that are not bundled in the OpenToken binary: requests
Install the Python package version of OpenToken CLI to use this extension.
```

Switch to the Python package install of OpenToken, or rewrite the extension to use only stdlib or OpenToken-bundled packages. See [Extension Author Reference: Binary Compatibility](../reference/extensions.md#binary-compatibility) for details on the three dependency tiers.

### Command name conflict

```
Extension 'HelloWorldExtension' conflicts with built-in command 'tokenize'; skipping.
```

The extension's `command_name` must not match any built-in subcommand. Contact the extension author to rename the command.

### Registry is out of sync

If the registry file is corrupt or lists an extension whose files are missing, try:

```bash
opentoken extension uninstall <name>
```

**Frozen binary mode:** the uninstall command removes the extracted files from the extensions directory and then deletes the registry entry. If the files are already gone it still cleans up the registry entry.

**Python package mode:** the uninstall command runs `pip uninstall -y <dist-name>` first. If pip reports the package as not installed (pip ≥ 21.3 exits non-zero in this case), the registry entry is **not** automatically removed.

If you are in Python package mode and `uninstall` fails because the package is already gone, confirm with:

```bash
pip show <dist-name>
```

If pip confirms the package is absent, remove the stale registry entry manually — open `~/.opentoken/extensions/registry.json` (or `$OPENTOKEN_EXTENSIONS_DIR/registry.json`) and delete the key for the extension name. Then re-install if needed.

---

## Related Documentation

- [Extension Author Reference](../reference/extensions.md) — Building extensions
- [Extension Quickstart](../quickstarts/extension-quickstart.md) — End-to-end walkthrough
- [CLI Reference](../reference/cli.md) — `opentoken extension` command options and environment variables
