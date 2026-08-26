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

- **Linux**: `olt-cli-{version}-linux-x64.zip`
- **macOS**: `olt-cli-{version}-macos-universal.zip` (works on both Intel and Apple Silicon)
- **Windows**: `olt-cli-{version}-windows-x64.zip`

Each downloadable ZIP is also published with a matching `.sha256` sidecar for manual verification.

### One-Line Installers

Install the latest release without manually downloading or extracting an archive:

```bash
# macOS/Linux - installs to ~/.local/bin
curl -fsSL https://github.com/TruvetaPublic/OpenLinkToken/releases/latest/download/install.sh | bash

# macOS/Linux - install a specific version
curl -fsSL https://github.com/TruvetaPublic/OpenLinkToken/releases/latest/download/install.sh | \
  bash -s -- --version v2.1.1
```

```powershell
# Windows - installs to ~/.openlinktoken/bin
irm https://github.com/TruvetaPublic/OpenLinkToken/releases/latest/download/install.ps1 | iex

# Windows - install a specific version
& ([scriptblock]::Create((irm https://github.com/TruvetaPublic/OpenLinkToken/releases/latest/download/install.ps1))) -Version v2.1.1
```

Both installers detect the platform, install to a user-writable directory, and verify the downloaded ZIP against its SHA-256 release sidecar.

### Extract and Run

**Linux/macOS:**

```bash
# Extract the zip file
unzip olt-cli-2.1.2-macos-universal.zip
cd olt-cli-2.1.2-macos-universal
cd olt

# The bundle keeps the executable and its runtime files together.
chmod +x olt

# Simulate receiving the recipient's public key (in practice, your partner provides this)
./olt generate-key-pair --name recipient
# Create the exchange config using the recipient's public key
./olt initiate-exchange --public-key "$HOME/.openlinktoken/recipient.public.pem"
# Tokenize and encrypt your data
./olt package -i /path/to/sample.csv
```

**Windows PowerShell:**

```powershell
# Extract the zip file
Expand-Archive olt-cli-2.1.2-windows-x64.zip
cd olt-cli-2.1.2-windows-x64
cd olt

# Simulate receiving the recipient's public key (in practice, your partner provides this)
.\olt.exe generate-key-pair --name recipient
# Create the exchange config using the recipient's public key
.\olt.exe initiate-exchange --public-key "$HOME/.openlinktoken/recipient.public.pem"
# Tokenize and encrypt your data
.\olt.exe package -i C:\path\to\sample.csv
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

# Create a local recipient key pair and an exchange config for this example.
# In a real exchange, the partner supplies the recipient public key.
./run-olt.sh generate-key-pair --name quickstart-recipient
./run-olt.sh initiate-exchange \
  --name quickstart-sender \
  --public-key "$HOME/.openlinktoken/quickstart-recipient.public.pem" \
  --output ./resources/quickstart.exchange.json

./run-olt.sh package \
  -i ./resources/sample.csv \
  -o ./resources/output.csv \
  --exchange-config ./resources/quickstart.exchange.json
```

### Windows PowerShell

```powershell
cd C:\path\to\OpenLinkToken

.\run-olt.ps1 generate-key-pair --name quickstart-recipient
.\run-olt.ps1 initiate-exchange `
  --name quickstart-sender `
  --public-key "$HOME/.openlinktoken/quickstart-recipient.public.pem" `
  --output .\resources\quickstart.exchange.json

.\run-olt.ps1 package `
  -i .\resources\sample.csv `
  -o .\resources\output.csv `
  --exchange-config .\resources\quickstart.exchange.json
```

## Subcommands

The CLI is organized into subcommands. Choose the one that matches your workflow:

| Subcommand                  | Description                                             | Requires                                                    |
| --------------------------- | ------------------------------------------------------- | ----------------------------------------------------------- |
| `decrypt`                   | Decrypt encrypted tokens back to hashed form            | exchange config + private key                               |
| `encrypt`                   | Encrypt previously tokenized (hashed) output            | exchange config + private key                               |
| `generate-key-pair`         | Generate an ECDH public/private key pair                | none                                                        |
| `initiate-exchange`         | Create the exchange config used by later commands       | recipient public key                                        |
| `package`                   | Tokenize and encrypt in one step — use for data sharing | exchange config + private key                               |
| `tokenize`                  | Tokenize without encryption — use for internal analysis | exchange config + private key                               |
| `tokenize --mode hash-only` | Output deterministic SHA-256 tokens without HMAC        | none for base output; optional exchange config for rotation |
| `tokenize --mode demo`      | Output plain attribute signatures — use for exploration | none for base output; optional exchange config for rotation |
| `update`                    | Upgrade the CLI to the latest (or a specific) release   | none                                                        |

For most use cases, `package` is the right starting point.
Use `tokenize --mode hash-only` when you need deterministic SHA-256 output without creating an exchange config first.
Use `tokenize --mode demo` to explore token output without managing secrets.

## Common Arguments

These arguments are shared across all subcommands:

| Argument            | Short               | Description                                                                                                                                                 |
| ------------------- | ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--input`           | `-i`                | Input file path (CSV or Parquet)                                                                                                                            |
| `--output`          | `-o`                | Output file path                                                                                                                                            |
| `-c`                | `--exchange-config` | Exchange config JSON path. Defaults to `./openlinktoken-YYYY-MM-DD.exchange.json` when omitted on consumer commands.                                        |
| `--private-key`     |                     | Private key PEM used to decrypt the exchange config and derive later transport keys                                                                         |
| `--private-key-env` |                     | Environment variable containing the private key PEM                                                                                                         |
| `--mode`            |                     | Tokenize mode selector: `default`, `hash-only`, or `demo`; hash-only/demo do not need secrets, but an exchange config may be supplied for rotation settings |
| `--hash-record-ids` |                     | SHA-256 hash each input `RecordId` before writing to output (one-way, no traceability; default `tokenize` mode and `package` only)                          |

## `package` Command

Tokenizes and encrypts records in one step. This produces tokens that can be safely shared with external partners.

By default, `package` writes a self-contained `<input>_packaged.zip` bundle containing the tokens (Parquet), metadata, and exchange config — ready to hand off to your partner. Pass `-o tokens.csv` to write a plain CSV instead.

### Example: CSV Input

**Input file (`sample.csv`):**

```csv
RecordId,FirstName,LastName,BirthDate,Sex,PostalCode,SSN
patient_001,John,Doe,1980-01-15,Male,98004,123-45-6789
patient_002,Jane,Smith,1975-03-22,Female,90210,987-65-4321
```

**Command:**

```bash
# Simulate receiving the recipient's public key (in practice, your partner provides this)
olt generate-key-pair --name recipient
# Create the exchange config using the recipient's public key
olt initiate-exchange --public-key ~/.openlinktoken/recipient.public.pem
# Tokenize and encrypt your data — write CSV so you can inspect it directly
olt package -i sample.csv -o tokens.csv
```

**Output (`tokens.csv`):**

```csv
RecordId,RuleId,Token
patient_001,T1,olt.V1.<JWE compact serialization>
patient_001,T2,olt.V1.<JWE compact serialization>
patient_001,T3,olt.V1.<JWE compact serialization>
patient_001,T4,olt.V1.<JWE compact serialization>
patient_001,T5,olt.V1.<JWE compact serialization>
patient_001,ML1,olt.V1.<JWE compact serialization>
patient_002,T1,...
```

For valid records, `package` emits T1–T5 plus one `ML1` row by default. ML1 is
omitted when its required attributes are invalid or when
`--disable-inferencing` is supplied. The `olt.V1.<JWE compact serialization>`
values above are encrypted package output; `tokenize` and `decrypt` instead
write unwrapped values.

### Example: Parquet Input

```bash
olt package -i input.parquet -o tokens.parquet
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

Each input record can produce up to 6 tokens: T1–T5 plus one ML1 row when ML1's
required attributes are valid. Use `--disable-inferencing` for T1–T5 only:

```bash
olt package -i sample.csv -o tokens.csv --disable-inferencing
```

| Column     | Description                                                                                                                                             |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RecordId` | Original record identifier                                                                                                                              |
| `RuleId`   | Token rule (`T1`–`T5` or `ML1`)                                                                                                                         |
| `Token`    | Encrypted package token (`olt.V1.<JWE>`), base64-encoded HMAC (default `tokenize`/decrypted), or 64-character SHA-256 hex (`tokenize --mode hash-only`) |

### Metadata File

`package` and `tokenize` create metadata. For CSV or Parquet output, a
`.metadata.json` file is created alongside the output; for ZIP output,
`package` embeds the metadata in the archive. `encrypt` and `decrypt` do not
create metadata files.

```json
{
  "Platform": "Python",
  "PythonVersion": "3.11.0",
  "Version": "2.1.0",
  "TotalRows": 2,
  "TotalRowsWithInvalidAttributes": 0,
  "InvalidAttributesByType": {},
  "BlankTokensByRule": {
    "T1": 0,
    "T2": 0,
    "T3": 0,
    "T4": 0,
    "T5": 0,
    "ML1": 0
  }
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
⚠ A new version of Open Link Token is available: v2.1.1 (you have v2.0.0)
   Release notes: https://github.com/TruvetaPublic/OpenLinkToken/releases/tag/v2.1.1
   Run 'olt update' to upgrade, or set OLT_DISABLE_UPDATE_CHECK=1 to silence this message.
```

The check never blocks or delays the primary command and is cached for 24 hours. To disable it:

```bash
# Disable for a single run
olt --no-update-check package ...

# Disable permanently (add to your shell profile)
export OLT_DISABLE_UPDATE_CHECK=1
```

### Self-Update with `olt update`

```bash
# Upgrade to the latest release
olt update

# Upgrade to a specific version
olt update --version v2.1.1

# Preview changes without applying them
olt update --dry-run
```

The updater downloads the correct platform asset, verifies its SHA-256 checksum when available, prompts for confirmation, and replaces the binary in-place.

## Next Steps

- [Java API Quickstart](java-quickstart.md) - Use the Java library directly
- [Python Quickstart](python-quickstart.md) - Use Python CLI
- [Configuration](../config/configuration.md) - Advanced options
- [Token Rules](../concepts/token-rules.md) - Understand T1-T5
