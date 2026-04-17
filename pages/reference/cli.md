---
layout: default
---

# CLI Reference

Complete reference for Open Link Token CLI arguments, modes, and examples. This page is the single source of truth for CLI flags and options; other documentation (such as Configuration) links here instead of duplicating them.

## Installation Options

### Self-Contained Executable (Recommended)

Download the pre-built executable from [releases](https://github.com/TruvetaPublic/OpenLinkToken/releases):

- **Linux**: `openlinktoken-cli-{version}-linux-x64.zip`
- **macOS**: `openlinktoken-cli-{version}-macos-universal.zip` (Intel + Apple Silicon)
- **Windows**: `openlinktoken-cli-{version}-windows-x64.zip`

No dependencies required. Extract and run.

### Other Options

- **Docker**: Use `run-openlinktoken.sh` (Linux/Mac) or `run-openlinktoken.ps1` (Windows)
- **Python**: Install with `uv pip install openlinktoken-cli`, then run `openlinktoken` or `python -m openlinktoken_cli.main`

For installation details, see the [CLI Quickstart](../quickstarts/cli-quickstart.md).

## Security Note

Treat generated token outputs and metadata as **sensitive**. In particular, `tokenize` output is intended for internal use and should not be shared externally (for example, in tickets, chats, or public repos).

The `tokenize` subcommand is primarily used to build **internal overlap-analysis datasets** that can be joined against **encrypted tokens received from external partners** (after decryption). If you need to **exchange** tokens across organizations, use `package` and follow a controlled exchange process: [Sharing Tokenized Data](../operations/sharing-tokenized-data.md).

## Command Syntax

**Linux/macOS (Bash):**

```bash
# Self-contained executable
./openlinktoken [OPTIONS]

# Python
python -m openlinktoken_cli.main <subcommand> [OPTIONS]
```

**Windows (PowerShell):**

```powershell
# Self-contained executable
.\olt.exe [OPTIONS]

# Python
python -m openlinktoken_cli.main <subcommand> [OPTIONS]
```

## Global Options

These options are accepted by the root command and apply to every invocation:

| Option              | Description                                                 |
| ------------------- | ----------------------------------------------------------- |
| `--no-update-check` | Disable the automatic background version check for this run |

The automatic version check can also be disabled permanently by setting the environment variable `OLT_DISABLE_UPDATE_CHECK=1`.

## Arguments by Subcommand

### `package` (Default Encrypted Mode)

| Argument            | Short | Required | Description                                                                                     |
| ------------------- | ----- | -------- | ----------------------------------------------------------------------------------------------- |
| `--input`           | `-i`  | Yes      | Path to input file (CSV or Parquet)                                                             |
| `--output`          | `-o`  | Yes      | Path to output file                                                                             |
| `--type`            | `-t`  | Yes      | File type: `csv` or `parquet`                                                                   |
| `--exchange-config` |       | No       | Exchange config JSON path. Defaults to `./openlinktoken-YYYY-MM-DD.exchange.json` when omitted. |
| `--private-key`     |       | No\*     | Private key PEM used to decrypt the exchange config and derive the transport encryption key     |
| `--private-key-env` |       | No\*     | Environment variable containing the private key PEM                                             |
| `--output-type`     | `-ot` | No       | Output file type if different from input                                                        |
| `--hash-record-ids` |       | No       | SHA-256 hash each input `RecordId` before writing to output (one-way, no traceability)          |

### `tokenize` (Hashed Tokens Only)

| Argument            | Short | Required         | Description                                                                                     |
| ------------------- | ----- | ---------------- | ----------------------------------------------------------------------------------------------- |
| `--input`           | `-i`  | Yes              | Path to input file (CSV or Parquet)                                                             |
| `--output`          | `-o`  | Yes              | Path to output file                                                                             |
| `--type`            | `-t`  | Yes              | File type: `csv` or `parquet`                                                                   |
| `--exchange-config` |       | Normal mode only | Exchange config JSON path. Defaults to `./openlinktoken-YYYY-MM-DD.exchange.json` when omitted. |
| `--private-key`     |       | No\*             | Private key PEM used to decrypt the exchange config                                             |
| `--private-key-env` |       | No\*             | Environment variable containing the private key PEM                                             |
| `--demo-mode`       |       | No               | No hashing; outputs raw attribute signatures. Cannot be combined with `--exchange-config`.      |
| `--output-type`     | `-ot` | No               | Output file type if different from input                                                        |
| `--hash-record-ids` |       | No               | SHA-256 hash each input `RecordId` before writing to output (one-way, no traceability)          |

### `encrypt` (Encrypt Input Tokens)

| Argument            | Short | Required | Description                                                                                     |
| ------------------- | ----- | -------- | ----------------------------------------------------------------------------------------------- |
| `--input`           | `-i`  | Yes      | Path to input file (CSV or Parquet)                                                             |
| `--output`          | `-o`  | Yes      | Path to output file                                                                             |
| `--type`            | `-t`  | Yes      | File type: `csv` or `parquet`                                                                   |
| `--exchange-config` |       | No       | Exchange config JSON path. Defaults to `./openlinktoken-YYYY-MM-DD.exchange.json` when omitted. |
| `--private-key`     |       | No\*     | Private key PEM used to decrypt the exchange config and derive the transport encryption key     |
| `--private-key-env` |       | No\*     | Environment variable containing the private key PEM                                             |
| `--output-type`     | `-ot` | No       | Output file type if different from input                                                        |

### `decrypt` (Decrypt Encrypted Tokens)

| Argument            | Short | Required | Description                                                                                     |
| ------------------- | ----- | -------- | ----------------------------------------------------------------------------------------------- |
| `--input`           | `-i`  | Yes      | Path to input file (must be encrypted)                                                          |
| `--output`          | `-o`  | Yes      | Path to output file                                                                             |
| `--type`            | `-t`  | Yes      | File type: `csv` or `parquet`                                                                   |
| `--exchange-config` |       | No       | Exchange config JSON path. Defaults to `./openlinktoken-YYYY-MM-DD.exchange.json` when omitted. |
| `--private-key`     |       | No\*     | Private key PEM used to decrypt the exchange config and derive the transport encryption key     |
| `--private-key-env` |       | No\*     | Environment variable containing the private key PEM                                             |
| `--output-type`     | `-ot` | No       | Output file type if different from input                                                        |

### `generate-key-pair` (ECDH Key Generation)

Available in the Python CLI.

| Argument  | Short | Required | Default                        | Description                                        |
| --------- | ----- | -------- | ------------------------------ | -------------------------------------------------- |
| `--curve` | `-c`  | No       | `P-256`                        | Elliptic curve: `P-256`, `P-384`, or `P-521`       |
| `--name`  | `-n`  | No       | `openlinktoken-<ISO8601-date>` | Base name for output key files                     |
| `--force` |       | No       | `false`                        | Overwrite existing key files if they already exist |

Writes key files to `~/.openlinktoken/`:

- `~/.openlinktoken/<name>.private.pem` — PKCS#8 PEM private key (permissions `600`)
- `~/.openlinktoken/<name>.public.pem` — SubjectPublicKeyInfo PEM public key (permissions `644`)
- `~/.openlinktoken/` directory is created with permissions `700` if absent.

### `initiate-exchange` (ECDH Key-Exchange Bootstrap)

Available in the Python CLI.

Generates, reuses, or derives a sender key pair, encrypts a hashing secret into a versioned multi-recipient JWE JSON exchange artifact, and writes recipient entries for both the sender and the partner. The artifact does **not** embed any private keys.

| Argument                   | Short | Required | Default                        | Description                                                                                                       |
| -------------------------- | ----- | -------- | ------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| `--public-key`             |       | Yes\*    |                                | Path to the partner's public key (PEM/SPKI format)                                                                |
| `--public-key-stdin`       |       | Yes\*    | `false`                        | Read the partner's public key PEM from stdin instead of `--public-key`                                            |
| `--public-key-env`         |       | Yes\*    |                                | Read the partner's public key PEM from the named environment variable                                             |
| `--name`                   | `-n`  | No       | `openlinktoken-<ISO8601-date>` | Base name for local key files                                                                                     |
| `--output`                 | `-o`  | No       | `./<name>.exchange.json`       | Output path for the exchange config JSON                                                                          |
| `--hashingsecret`          |       | No\*\*   | randomly generated             | Hashing secret to encrypt when you intentionally pass it on the command line                                      |
| `--hashingsecret-stdin`    |       | No\*\*   | `false`                        | Read the hashing secret from stdin instead of passing it on the command line                                      |
| `--hashingsecret-env`      |       | No\*\*   |                                | Read the hashing secret from the named environment variable                                                       |
| `--curve`                  | `-c`  | No       | `P-256`                        | Elliptic curve for generated keys: `P-256`, `P-384`, or `P-521`                                                   |
| `--force`                  |       | No       | `false`                        | Overwrite existing key files and exchange config                                                                  |
| `--sender-private-key`     |       | No       |                                | Reuse an existing sender private key PEM for the sender-side recipient entry instead of generating a new key pair |
| `--sender-private-key-env` |       | No       |                                | Read the sender private key PEM from the named environment variable without writing local sender key files        |

**Outputs:**

- `~/.openlinktoken/<name>.private.pem` — local private key (permissions `600`) when Open Link Token generates a sender key or reuses `--sender-private-key`
- `~/.openlinktoken/<name>.public.pem` — local public key (permissions `644`) when Open Link Token generates a sender key or reuses `--sender-private-key`
- `<output>` — versioned multi-recipient JWE JSON exchange artifact containing the encrypted hashing secret

`<output>` can be decrypted by either side with its own matching private key. The JSON is still sensitive, but it does **not** contain private key material.

\* Provide one of `--public-key`, `--public-key-stdin`, or `--public-key-env`.

\*\* Provide at most one of `--hashingsecret`, `--hashingsecret-stdin`, or `--hashingsecret-env`. If you omit all three, Open Link Token generates a secure random hashing secret. For pre-existing secrets, prefer `--hashingsecret-env` or `--hashingsecret-stdin` so the secret does not appear in shell history or process arguments. Because stdin can only be consumed once per command, `--hashingsecret-stdin` cannot be combined with `--public-key-stdin`.

**Example:**

```bash
# Step 1 – recipient generates their key pair and shares the public key
olt generate-key-pair --name recipient-org

# Step 2 – sender initiates the exchange using the recipient's public key
olt initiate-exchange \
  --name sender-q2 \
  --public-key ./recipient-org.public.pem \
  --output ./sender-q2.exchange.json
```

To reuse an existing sender private key instead of generating a new one:

```bash
olt initiate-exchange \
  --name sender-q2 \
  --public-key ./recipient-org.public.pem \
  --sender-private-key ~/.openlinktoken/sender-q2.private.pem \
  --output ./sender-q2.exchange.json
```

To read the partner public key from stdin as an alternative to `--public-key`:

```bash
cat ./recipient-org.public.pem | olt initiate-exchange \
  --name sender-q2 \
  --public-key-stdin \
  --output ./sender-q2.exchange.json
```

To provide an existing hashing secret without exposing it in the process argument list:

```bash
export OLT_HASHING_SECRET="$(az keyvault secret show --vault-name my-vault --name hashing-secret --query value -o tsv)"

olt initiate-exchange \
  --name sender-q2 \
  --public-key ./recipient-org.public.pem \
  --hashingsecret-env OLT_HASHING_SECRET \
  --output ./sender-q2.exchange.json
```

To supply both the partner public key and the sender private key by reference in
one command, use environment-variable references instead of stdin:

```bash
OLT_PARTNER_PUBLIC_KEY="$(az keyvault secret show --vault-name my-vault --name recipient-public-key --query value -o tsv)" \
OLT_SENDER_PRIVATE_KEY="$(az keyvault secret show --vault-name my-vault --name sender-private-key --query value -o tsv)" \
olt initiate-exchange \
  --name sender-q2 \
  --public-key-env OLT_PARTNER_PUBLIC_KEY \
  --sender-private-key-env OLT_SENDER_PRIVATE_KEY \
  --output ./sender-q2.exchange.json
```

When `--sender-private-key-env` is used, Open Link Token derives the sender public key
in memory and does not write local sender key files under `~/.openlinktoken/`.

For `tokenize`, `package`, `encrypt`, and `decrypt`, Open Link Token resolves the exchange config from `--exchange-config` or from the date-based default path `./olt-YYYY-MM-DD.exchange.json`. When neither `--private-key` nor `--private-key-env` is supplied, the CLI falls back to `~/.openlinktoken/` fingerprint-based key lookup.

\* Provide at most one of `--private-key` or `--private-key-env`.

See [Sharing Tokenized Data](../operations/sharing-tokenized-data.md) for the full two-command ECDH bootstrap workflow.
For a field-by-field format reference, see `docs/exchange-config-format.md`.

### `update` (Self-Update CLI)

Downloads and installs the latest (or a specific) release of the Open Link Token CLI in-place.

| Argument    | Short | Required | Description                                           |
| ----------- | ----- | -------- | ----------------------------------------------------- |
| `--version` |       | No       | Install a specific release tag (default: latest)      |
| `--dry-run` |       | No       | Show what would be updated without making any changes |
| `--yes`     | `-y`  | No       | Skip the interactive confirmation prompt              |

```bash
# Update to the latest release
olt update

# Update to a specific version
olt update --version v2.1.0

# Preview what would change (no-op)
olt update --dry-run

# Update without prompting for confirmation
olt update --yes
```

Release assets are published with SHA-256 sidecars, and `olt update` verifies the matching checksum automatically before the binary is replaced. The command exits non-zero if the checksum does not match.

## Modes of Operation

### Encrypted Mode (Default)

Generates fully encrypted tokens using AES-256-GCM. Tokens can be decrypted later with the encryption key.

```bash
olt package \
  -i input.csv -t csv -o output.csv \
  -h "HashingSecret" \
  -e "EncryptionKey-Exactly32Chars!!"
```

**Token Pipeline:**

```
Signature → SHA-256 → HMAC-SHA256 → AES-256-GCM → Base64
```

### `tokenize` Subcommand

Generates one-way hashed tokens. Faster but tokens cannot be decrypted.

```bash
olt tokenize \
  -i input.csv -t csv -o output.csv \
  -h "HashingSecret"

```

**Token Pipeline:**

```
Signature → SHA-256 → HMAC-SHA256 → Base64
```

### Demo Mode (`tokenize --demo-mode`)

Outputs raw attribute signature strings without any hashing. Both the SHA-256 and HMAC
steps are skipped. No `--hashingsecret` is required, making it easy to inspect which
attribute values compose each token for development, testing, or demos.

> ⚠️ **Demo-mode output must not be used in production or shared externally.** The raw
> signatures expose the normalised attribute values directly and provide no privacy
> protection across trust boundaries.

```bash
olt tokenize \
  -i input.csv -t csv -o output.csv \
  --demo-mode
```

**Token Pipeline:**

```text
Signature → (passthrough) → Raw pipe-separated string
```

**Example demo token** (T1 rule, first name + last name + birth date):

```text
JOHN|DOE|19800115
```

**Differences from normal `tokenize`:**

| Aspect                          | Normal mode                    | Demo mode                                  |
| ------------------------------- | ------------------------------ | ------------------------------------------ |
| `--hashingsecret`               | Required                       | Not required (ignored if supplied)         |
| Token pipeline                  | SHA-256 → HMAC-SHA256 → Base64 | Passthrough → raw signature string         |
| Token format                    | Base64-encoded HMAC-SHA256     | Pipe-separated normalised attribute values |
| `HashingSecretHash` in metadata | Present                        | Absent                                     |
| Safe to share                   | No (internal only)             | No (never suitable for exchange)           |

## File Format Examples

### CSV Input

```csv
RecordId,FirstName,LastName,BirthDate,Sex,PostalCode,SSN
patient_001,John,Doe,1980-01-15,Male,98004,123-45-6789
patient_002,Jane,Smith,1975-03-22,Female,90210,987-65-4321
```

**Column Aliases Accepted:**

| Standard Name | Accepted Aliases                                   |
| ------------- | -------------------------------------------------- |
| RecordId      | Id                                                 |
| FirstName     | GivenName                                          |
| LastName      | Surname                                            |
| BirthDate     | DateOfBirth                                        |
| Sex           | Gender                                             |
| PostalCode    | ZipCode, ZIP3, ZIP4, ZIP5                          |
| SSN           | SocialSecurityNumber, NationalIdentificationNumber |

### CSV Output

```csv
RecordId,RuleId,Token
patient_001,T1,Gn7t1Zj16E5Qy+z9iINtczP6fRDYta6C0XFr...
patient_001,T2,pUxPgYL9+cMxkA+8928Pil+9W+dm9kISwHYP...
patient_001,T3,rwjfwIo5OcJUItTx8KCoSZMtr7tVGSyXsWv/...
patient_001,T4,9o7HIYZkhizczFzJL1HFyanlllzSa8hlgQWQ...
patient_001,T5,QpBpGBqaMhagfcHGZhVavn23ko03jkyS9Vo4...
```

### Parquet Schema

**Input:**

```text
RecordId: string
FirstName: string
LastName: string
BirthDate: string (YYYY-MM-DD)
Sex: string
PostalCode: string
SSN: string
```

**Output:**

```text
RecordId: string
RuleId: string
Token: string
```

## Metadata Output

Every run generates a `.metadata.json` file:

```json
{
  "Platform": "Python",
  "PythonVersion": "3.11.0",
  "Version": "2.0.0-alpha",
  "TotalRows": 100,
  "TotalRowsWithInvalidAttributes": 3,
  "InvalidAttributesByType": {
    "BirthDate": 2,
    "SSN": 1
  },
  "BlankTokensByRule": {
    "T1": 2,
    "T4": 1
  },
  "HashingSecretHash": "e0b4e60b...",
  "EncryptionSecretHash": "a1b2c3d4..."
}
```

## Docker Script Options

### Bash (run-openlinktoken.sh)

```bash
./run-openlinktoken.sh package \
  -i ./input.csv \
  -o ./output.csv \
  -t csv \
  -h "HashingKey" \
  -e "EncryptionKey" \
  [--skip-build] \
  [--verbose]
```

| Option         | Description               |
| -------------- | ------------------------- |
| `--skip-build` | Skip Docker image rebuild |
| `--verbose`    | Show detailed output      |
| `--help`       | Show help message         |

### PowerShell (run-openlinktoken.ps1)

```powershell
.\run-openlinktoken.ps1 package `
  -i .\input.csv `
  -o .\output.csv `
  -FileType csv `
  -h "HashingKey" `
  -e "EncryptionKey" `
  [-SkipBuild] `
  [-Verbose]
```

## Extensions

The `extension` subcommand manages CLI extensions. Extensions add top-level subcommands to `openlinktoken` without requiring a CLI upgrade. See [Extension Author Reference](extensions.md) for how to build extensions, and [Managing Extensions](../operations/managing-extensions.md) for operator workflows.

### `extension install`

```bash
olt extension install [--yes] <url>
```

Downloads and installs an extension from a URL or `file://` path.

| Option  | Description                                                            |
| ------- | ---------------------------------------------------------------------- |
| `<url>` | Source URL (`https://`) or `file://` absolute path to a `.whl` package |
| `--yes` | Skip the security confirmation prompt                                  |

A security warning is always printed before installing. Confirmation is required unless `--yes` is passed. The CLI aborts with an error if the extension requires packages not bundled in the binary (Tier-3 extensions are not supported under the binary install).

### `extension list`

```bash
olt extension list
```

Prints a table of all installed extensions with name, version, command name, and source URL.

### `extension uninstall`

```bash
olt extension uninstall <name>
```

Removes the named extension and its registry entry. The `<name>` argument is the extension name as shown in `extension list`.

---

### Extension Environment Variables

| Variable             | Description                                                                                                                                             |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `OLT_EXTENSIONS_DIR` | Override the default extension install directory (`~/.openlinktoken/extensions/`). Set in CI or containers to install extensions at a predictable path. |

### Registry File

The extension registry is stored at:

```
~/.openlinktoken/extensions/registry.json
```

When `OLT_EXTENSIONS_DIR` is set, the registry is stored in that directory instead. The registry records each extension's name, version, module path, entry-point class, install path, and source URL. It is read at CLI startup to discover extensions under the binary install.

---

## Error Messages

| Error                                  | Cause                        | Solution                         |
| -------------------------------------- | ---------------------------- | -------------------------------- |
| "Encryption key not provided"          | Missing `-e` in package mode | Add `-e "key"` or use `tokenize` |
| "Encryption key must be 32 characters" | Key length wrong             | Use exactly 32 characters        |
| "Input file not found"                 | Invalid path                 | Check file exists                |
| "Unknown file type"                    | Invalid `-t` value           | Use `csv` or `parquet`           |
| "Invalid attribute: BirthDate"         | Date validation failed       | Use YYYY-MM-DD format            |
| "Unsupported curve '…'"                | Invalid `--curve` value      | Use `P-256`, `P-384`, or `P-521` |
| "Key files for '…' already exist"      | Name collision without force | Use `--force` to overwrite       |

## Exit Codes

| Code | Meaning           |
| ---- | ----------------- |
| 0    | Success           |
| 1    | Invalid arguments |
| 2    | File not found    |
| 3    | Processing error  |

## Version Check & Updates

### Automatic Version Check on Startup

Every time the CLI is run, it performs a lightweight background check against the GitHub Releases API to determine whether a newer version is available. This check:

- Runs asynchronously in a background thread — it **never delays** the primary command
- Has a 2-second timeout; network errors are silently ignored
- Caches the result for **24 hours** in the Open Link Token user cache file:
  - Linux / macOS: `~/.openlinktoken/update-check.json`
  - Windows: `%APPDATA%\.openlinktoken\update-check.json`
- Prints a notice to **stderr** (not stdout) only when a newer version is found, so piped/scripted usage is unaffected

**Sample notice:**

```
⚠ A new version of Open Link Token is available: v2.1.0 (you have v2.0.0)
   Release notes: https://github.com/TruvetaPublic/OpenLinkToken/releases/tag/v2.1.0
   Run 'olt update' to upgrade, or set OLT_DISABLE_UPDATE_CHECK=1 to silence this message.
```

### Opting Out

The version check can be disabled per-run or permanently:

| Mechanism                            | Scope                                       |
| ------------------------------------ | ------------------------------------------- |
| `--no-update-check` CLI flag         | Per invocation                              |
| `OLT_DISABLE_UPDATE_CHECK=1` env var | Persistent (shell profile / CI environment) |

When disabled, no network request is made and no cache is read or written.

### Self-Updating (`olt update`)

Use the `update` subcommand to upgrade the CLI in-place:

```bash
# Upgrade to the latest release
olt update

# Upgrade to a specific release
olt update --version v2.1.0

# Preview what would change without applying it
olt update --dry-run

# Skip confirmation prompt (for scripts / CI)
olt update --yes
```

#### Update Behaviour

1. Fetches release information from the GitHub Releases API
2. Selects the correct platform asset for the current OS and architecture
3. Downloads the asset to a temporary location
4. Verifies the published SHA-256 checksum before replacing the binary
5. Prompts for confirmation (skipped with `--yes` or when stdin is non-interactive)
6. Replaces the installed binary in-place
7. Prints the new version on success

#### Update Error Handling

| Condition                       | Exit code | Message                                           |
| ------------------------------- | --------- | ------------------------------------------------- |
| Already on the latest version   | 0         | `Open Link Token is already up to date (v2.0.0).` |
| Asset not found for platform    | 1         | Clear error with download link                    |
| Checksum verification failed    | 1         | Error message; downloaded file is deleted         |
| Insufficient write permissions  | 1         | Suggests `sudo` or manual download link           |
| Network error / release missing | 1         | Descriptive error                                 |

## Performance Tips

- Use Parquet for large datasets (faster I/O, compression)
- Use `tokenize` if decryption not needed (20-30% faster)
- For very large files, consider [PySpark integration](../operations/spark-or-databricks.md)

## Next Steps

- [Java API Reference](java-api.md) - Programmatic usage
- [Python API Reference](python-api.md) - Programmatic usage
- [Configuration](../config/configuration.md) - Advanced settings
- [Decrypting Tokens](../operations/decrypting-tokens.md) - Reverse encrypted tokens
