---
layout: default
---

# CLI Quickstart

For a high-level overview and other entry points, see [Quickstarts](index.md).

Run the Open Link Token CLI end-to-end to generate tokens from a sample dataset in minutes.

## Prerequisites

Choose one of:

- **Self-contained executable** (easiest) - Download and run, zero dependencies
- **Docker** (recommended for reproducibility) - No other dependencies needed
- **Python 3.10+**

## Quick Start with Self-Contained Executable

The easiest way to get started. No Docker, Java, or Python installation required.

### Download

Download the appropriate executable for your platform from the [latest release](https://github.com/TruvetaPublic/OpenLinkToken/releases):

- **Linux**: `openlinktoken-cli-{version}-linux-x64.zip`
- **macOS**: `openlinktoken-cli-{version}-macos-universal.zip` (works on both Intel and Apple Silicon)
- **Windows**: `openlinktoken-cli-{version}-windows-x64.zip`

Each downloadable ZIP is also published with a matching `.sha256` sidecar for manual verification.

### Extract and Run

**Linux/macOS:**

```bash
# Extract the zip file
unzip openlinktoken-cli-2.0.0-alpha-macos-universal.zip
cd openlinktoken-cli-2.0.0-alpha-macos-universal

# Make executable (if needed)
chmod +x openlinktoken

# Run the CLI
./olt generate-key-pair --name recipient --force
./olt initiate-exchange --name quickstart --public-key "$HOME/.openlinktoken/recipient.public.pem" --output /path/to/quickstart.exchange.json
./olt package \
  -i /path/to/sample.csv \
  -o /path/to/output.csv \
  --exchange-config /path/to/quickstart.exchange.json
```

**Windows PowerShell:**

```powershell
# Extract the zip file
Expand-Archive openlinktoken-cli-2.0.0-alpha-windows-x64.zip
cd openlinktoken-cli-2.0.0-alpha-windows-x64

# Run the CLI
.\olt.exe generate-key-pair --name recipient --force
.\olt.exe initiate-exchange --name quickstart --public-key "$HOME/.openlinktoken/recipient.public.pem" --output C:\path\to\quickstart.exchange.json
.\olt.exe package `
  -i C:\path\to\sample.csv `
  -o C:\path\to\output.csv `
  --exchange-config C:\path\to\quickstart.exchange.json
```

### Verifying the Executable

The self-contained executable includes:

- Python 3.11 runtime (bundled)
- All dependencies (pyarrow, pandas, cryptography)
- Open Link Token CLI and core library

No installation or setup required — just download, extract, and run.

## Quick Start with Docker

The fastest way to get started. No Python installation required.

### Linux/Mac

```bash
cd /path/to/OpenLinkToken

./run-openlinktoken.sh package \
  -i ./resources/sample.csv \
  -o ./resources/output.csv \
  --exchange-config ./resources/quickstart.exchange.json
```

### Windows PowerShell

```powershell
cd C:\path\to\OpenLinkToken

.\run-openlinktoken.ps1 package `
  -i .\resources\sample.csv `
  -o .\resources\output.csv `
  --exchange-config .\resources\quickstart.exchange.json
```

## Subcommands

The CLI is organized into subcommands. Choose the one that matches your workflow:

| Subcommand                  | Description                                             | Requires                      |
| --------------------------- | ------------------------------------------------------- | ----------------------------- |
| `decrypt`                   | Decrypt encrypted tokens back to hashed form            | exchange config + private key |
| `encrypt`                   | Encrypt previously tokenized (hashed) output            | exchange config + private key |
| `generate-key-pair`         | Generate an ECDH public/private key pair                | none                          |
| `initiate-exchange`         | Create the exchange config used by later commands       | recipient public key          |
| `package`                   | Tokenize and encrypt in one step — use for data sharing | exchange config + private key |
| `tokenize`                  | Tokenize without encryption — use for internal analysis | exchange config + private key |
| `tokenize --mode hash-only` | Output deterministic SHA-256 tokens without HMAC        | none                          |
| `tokenize --mode demo`      | Output plain attribute signatures — use for exploration | none                          |
| `update`                    | Upgrade the CLI to the latest (or a specific) release   | none                          |

For most use cases, `package` is the right starting point.
Use `tokenize --mode hash-only` when you need deterministic SHA-256 output without creating an exchange config first.
Use `tokenize --mode demo` to explore token output without managing secrets.

## Common Arguments

These arguments are shared across all subcommands:

| Argument            | Short | Description                                                                                                                                                                                |
| ------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `--input`           | `-i`  | Input file path (CSV or Parquet)                                                                                                                                                           |
| `--output`          | `-o`  | Output file path                                                                                                                                                                           |
| `--exchange-config` |       | Exchange config JSON path. Defaults to `./openlinktoken-YYYY-MM-DD.exchange.json` when omitted on consumer commands.                                                                       |
| `--private-key`     |       | Private key PEM used to decrypt the exchange config and derive later transport keys                                                                                                        |
| `--private-key-env` |       | Environment variable containing the private key PEM                                                                                                                                        |
| `--mode`            |       | Tokenize mode selector: `default`, `hash-only`, or `demo` (`hash-only` cannot be combined with exchange-config or private-key options; `demo` cannot be combined with `--exchange-config`) |
| `--hash-record-ids` |       | SHA-256 hash each input `RecordId` before writing to output (one-way, no traceability; default `tokenize` mode and `package` only)                                                         |

## `package` Command

Tokenizes and encrypts records in one step. This produces tokens that can be safely shared with external partners.

### Example: CSV Input

**Input file (`sample.csv`):**

```csv
RecordId,FirstName,LastName,BirthDate,Sex,PostalCode,SSN
patient_001,John,Doe,1980-01-15,Male,98004,123-45-6789
patient_002,Jane,Smith,1975-03-22,Female,90210,987-65-4321
```

**Command:**

```bash
olt generate-key-pair --name recipient --force
olt initiate-exchange --name quickstart --public-key ~/.openlinktoken/recipient.public.pem --output ./quickstart.exchange.json
olt package \
  -i sample.csv \
  -o tokens.csv \
  --exchange-config ./quickstart.exchange.json
```

**Output (`tokens.csv`):**

```csv
RecordId,RuleId,Token
patient_001,T1,Gn7t1Zj16E5Qy+z9iINtcz...
patient_001,T2,pUxPgYL9+cMxkA+8928Pi...
patient_001,T3,rwjfwIo5OcJUItTx8KCo...
patient_001,T4,9o7HIYZkhizczFzJL1HFy...
patient_001,T5,QpBpGBqaMhagfcHGZhVa...
patient_002,T1,...
```

### Example: Parquet Input

```bash
olt package \
  -i input.parquet \
  -o tokens.parquet \
  --exchange-config ./quickstart.exchange.json
```

## Other Subcommands

For detail on `tokenize`, `encrypt`, `decrypt`, and `generate-key-pair`, see:

- [Tokenize](../operations/tokenize.md) — `tokenize` subcommand
- [Decrypting Tokens](../operations/decrypting-tokens.md) — `decrypt` subcommand
- [Key Management](../security.md#key-management--secrets) — `generate-key-pair` and key guidance
- [CLI Reference](../reference/cli.md) — full argument reference for all subcommands

## `generate-key-pair` Command

Generates an ECDH public/private key pair and writes the keys to `~/.openlinktoken/`.

```bash
olt generate-key-pair --curve P-256 --name my-org-key
```

This creates:

- `~/.openlinktoken/my-org-key.private.pem` — PKCS#8 PEM private key (permissions `600`)
- `~/.openlinktoken/my-org-key.public.pem` — SubjectPublicKeyInfo PEM public key (permissions `644`)

**Options:**

| Option    | Short | Description                                  | Default                        |
| --------- | ----- | -------------------------------------------- | ------------------------------ |
| `--curve` | `-c`  | Elliptic curve: `P-256`, `P-384`, or `P-521` | `P-256`                        |
| `--name`  | `-n`  | Base name for the output key files           | `openlinktoken-<ISO8601-date>` |
| `--force` |       | Overwrite existing key files                 | false                          |

## Understanding the Output

### Token File

Each input record produces 5 tokens (T1–T5):

| Column     | Description                                                                                                                                     |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `RecordId` | Original record identifier                                                                                                                      |
| `RuleId`   | Token rule (T1, T2, T3, T4, or T5)                                                                                                              |
| `Token`    | Encrypted match token (`olt.V1`), base64-encoded HMAC (default `tokenize`/decrypted), or 64-character SHA-256 hex (`tokenize --mode hash-only`) |

### Metadata File

A `.metadata.json` file is created alongside the output:

```json
{
  "Platform": "Python",
  "PythonVersion": "3.11.0",
  "Version": "2.0.0",
  "TotalRows": 2,
  "TotalRowsWithInvalidAttributes": 0,
  "InvalidAttributesByType": {},
  "BlankTokensByRule": {},
  "HashingSecretHash": "e0b4e60b...",
  "EncryptionSecretHash": "a1b2c3d4..."
}
```

## Troubleshooting

### "No private key matching this exchange config was found"

Pass `--private-key` or `--private-key-env`, or place the matching key under `~/.openlinktoken/`.

### "Invalid BirthDate"

Ensure dates are in `YYYY-MM-DD` format and between 1910-01-01 and today.

### "File not found"

Check that input file path is correct and file exists.

### "Invalid SSN"

SSN must be 9 digits. Area code cannot be 000, 666, or 900-999.

### Unexpected internal error

If a command fails unexpectedly, check the `Stack trace: <path>` line printed to **stderr**. The CLI archives a redacted traceback under `~/.openlinktoken/logs` on Linux and macOS or `%APPDATA%\.openlinktoken\logs` on Windows.

## Keeping the CLI Up to Date

### Automatic Version Check

Each time you run the CLI it silently checks (in the background) whether a newer release is available. If one is found, a notice is printed to **stderr** after the command completes:

```
⚠ A new version of Open Link Token is available: v2.1.0 (you have v2.0.0)
   Release notes: https://github.com/TruvetaPublic/OpenLinkToken/releases/tag/v2.1.0
   Run 'olt update' to upgrade, or set OLT_DISABLE_UPDATE_CHECK=1 to silence this message.
```

The check never blocks or delays the primary command and is cached for 24 hours. To disable it:

```bash
# Disable for a single run
openlinktoken --no-update-check package ...

# Disable permanently (add to your shell profile)
export OLT_DISABLE_UPDATE_CHECK=1
```

### Self-Update with `olt update`

```bash
# Upgrade to the latest release
olt update

# Upgrade to a specific version
olt update --version v2.1.0

# Preview changes without applying them
olt update --dry-run
```

The updater downloads the correct platform asset, verifies its SHA-256 checksum when available, prompts for confirmation, and replaces the binary in-place.

## Next Steps

- [Java API Quickstart](java-quickstart.md) - Use the Java library directly
- [Python Quickstart](python-quickstart.md) - Use Python CLI
- [Configuration](../config/configuration.md) - Advanced options
- [Token Rules](../concepts/token-rules.md) - Understand T1-T5
