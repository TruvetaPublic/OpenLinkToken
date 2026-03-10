---
layout: default
---

# CLI Quickstart

For a high-level overview and other entry points, see [Quickstarts](index.md).

Run the OpenToken CLI end-to-end to generate tokens from a sample dataset in minutes.

## Prerequisites

Choose one of:

- **Self-contained executable** (easiest) - Download and run, zero dependencies
- **Docker** (recommended for reproducibility) - No other dependencies needed
- **Python 3.10+**

## Quick Start with Self-Contained Executable

The easiest way to get started. No Docker, Java, or Python installation required.

### Download

Download the appropriate executable for your platform from the [latest release](https://github.com/TruvetaPublic/OpenToken/releases):

- **Linux**: `opentoken-cli-{version}-linux-x64.zip`
- **macOS**: `opentoken-cli-{version}-macos-universal.zip` (works on both Intel and Apple Silicon)
- **Windows**: `opentoken-cli-{version}-windows-x64.zip`

### Extract and Run

**Linux/macOS:**

```bash
# Extract the zip file
unzip opentoken-cli-2.0.0-alpha-macos-universal.zip
cd opentoken-cli-2.0.0-alpha-macos-universal

# Make executable (if needed)
chmod +x opentoken

# Run the CLI
./opentoken package \
  -i /path/to/sample.csv \
  -o /path/to/output.csv \
  -t csv \
  -h "HashingKey" \
  -e "Secret-Encryption-Key-Goes-Here."
```

**Windows PowerShell:**

```powershell
# Extract the zip file
Expand-Archive opentoken-cli-2.0.0-alpha-windows-x64.zip
cd opentoken-cli-2.0.0-alpha-windows-x64

# Run the CLI
.\opentoken.exe package `
  -i C:\path\to\sample.csv `
  -o C:\path\to\output.csv `
  -t csv `
  -h "HashingKey" `
  -e "Secret-Encryption-Key-Goes-Here."
```

### Verifying the Executable

The self-contained executable includes:

- Python 3.11 runtime (bundled)
- All dependencies (pyarrow, pandas, cryptography)
- OpenToken CLI and core library

No installation or setup required — just download, extract, and run.

## Quick Start with Docker

The fastest way to get started. No Python installation required.

### Linux/Mac

```bash
cd /path/to/OpenToken

./run-opentoken.sh package \
  -i ./resources/sample.csv \
  -o ./resources/output.csv \
  -t csv \
  -h "HashingKey" \
  -e "Secret-Encryption-Key-Goes-Here."
```

### Windows PowerShell

```powershell
cd C:\path\to\OpenToken

.\run-opentoken.ps1 package `
  -i .\resources\sample.csv `
  -o .\resources\output.csv `
  -t csv `
  -h "HashingKey" `
  -e "Secret-Encryption-Key-Goes-Here."
```

## Subcommands

The CLI is organized into subcommands. Choose the one that matches your workflow:

| Subcommand             | Description                                             | Requires   |
| ---------------------- | ------------------------------------------------------- | ---------- |
| `package`              | Tokenize and encrypt in one step — use for data sharing | `-h`, `-e` |
| `tokenize`             | Tokenize without encryption — use for internal analysis | `-h`       |
| `tokenize --demo-mode` | Output plain attribute signatures — use for exploration | none       |
| `encrypt`              | Encrypt previously tokenized (hashed) output            | `-e`       |
| `decrypt`              | Decrypt encrypted tokens back to hashed form            | `-e`       |
| `generate-key-pair`    | Generate an ECDH public/private key pair                | none       |

For most use cases, `package` is the right starting point.
Use `tokenize --demo-mode` to explore token output without managing secrets.

## Common Arguments

These arguments are shared across all subcommands:

| Argument            | Short | Description                                                                     |
| ------------------- | ----- | ------------------------------------------------------------------------------- |
| `--input`           | `-i`  | Input file path (CSV or Parquet)                                                |
| `--output`          | `-o`  | Output file path                                                                |
| `--type`            | `-t`  | File type: `csv` or `parquet`                                                   |
| `--hashingsecret`   | `-h`  | Secret key for HMAC hashing (required unless `--demo-mode`)                     |
| `--encryptionkey`   | `-e`  | 32-character key for AES encryption                                             |
| `--demo-mode`       |       | Skip all hashing; output plain attribute signatures (tokenize only)             |
| `--hash-record-ids` |       | SHA-256 hash each input `RecordId` before writing to output (one-way, no traceability; `tokenize` and `package` only) |

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
opentoken package \
  -i sample.csv \
  -t csv \
  -o tokens.csv \
  -h "MyHashingSecret" \
  -e "MyEncryptionKey-32Characters!"
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
opentoken package \
  -i input.parquet \
  -t parquet \
  -o tokens.parquet \
  -h "MyHashingSecret" \
  -e "MyEncryptionKey-32Characters!"
```

## Other Subcommands

For detail on `tokenize`, `encrypt`, `decrypt`, and `generate-key-pair`, see:

- [Tokenize](../operations/tokenize.md) — `tokenize` subcommand
- [Decrypting Tokens](../operations/decrypting-tokens.md) — `decrypt` subcommand
- [Key Management](../security.md#key-management--secrets) — `generate-key-pair` and key guidance
- [CLI Reference](../reference/cli.md) — full argument reference for all subcommands

## `generate-key-pair` Command

Generates an ECDH public/private key pair and writes the keys to `~/.opentoken/`.

```bash
opentoken generate-key-pair --curve P-256 --name my-org-key
```

This creates:
- `~/.opentoken/my-org-key.private.pem` — PKCS#8 PEM private key (permissions `600`)
- `~/.opentoken/my-org-key.public.pem` — SubjectPublicKeyInfo PEM public key (permissions `644`)

**Options:**

| Option    | Short | Description                                  | Default                   |
| --------- | ----- | -------------------------------------------- | ------------------------- |
| `--curve` | `-c`  | Elliptic curve: `P-256`, `P-384`, or `P-521` | `P-256`                   |
| `--name`  | `-n`  | Base name for the output key files           | `opentoken-<ISO8601-date>` |
| `--force` |       | Overwrite existing key files                 | false                     |

## Understanding the Output

### Token File

Each input record produces 5 tokens (T1–T5):

| Column     | Description                                                             |
| ---------- | ----------------------------------------------------------------------- |
| `RecordId` | Original record identifier                                              |
| `RuleId`   | Token rule (T1, T2, T3, T4, or T5)                                      |
| `Token`    | Encrypted match token (ot.V1 format) or base64-encoded HMAC (hash-only) |

### Metadata File

A `.metadata.json` file is created alongside the output:

```json
{
  "Platform": "Python",
  "PythonVersion": "3.11.0",
  "OpenTokenVersion": "2.0.0",
  "TotalRows": 2,
  "TotalRowsWithInvalidAttributes": 0,
  "InvalidAttributesByType": {},
  "BlankTokensByRule": {},
  "HashingSecretHash": "e0b4e60b...",
  "EncryptionSecretHash": "a1b2c3d4..."
}
```

## Troubleshooting

### "Encryption key not provided"

Either provide `-e "YourKey"` with `package` or use the `tokenize` subcommand.

### "Invalid BirthDate"

Ensure dates are in `YYYY-MM-DD` format and between 1910-01-01 and today.

### "File not found"

Check that input file path is correct and file exists.

### "Invalid SSN"

SSN must be 9 digits. Area code cannot be 000, 666, or 900-999.

## Next Steps

- [Java API Quickstart](java-quickstart.md) - Use the Java library directly
- [Python Quickstart](python-quickstart.md) - Use Python CLI
- [Configuration](../config/configuration.md) - Advanced options
- [Token Rules](../concepts/token-rules.md) - Understand T1-T5
