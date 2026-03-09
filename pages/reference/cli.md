---
layout: default
---

# CLI Reference

Complete reference for OpenToken CLI arguments, modes, and examples. This page is the single source of truth for CLI flags and options; other documentation (such as Configuration) links here instead of duplicating them.

## Installation Options

### Self-Contained Executable (Recommended)

Download the pre-built executable from [releases](https://github.com/TruvetaPublic/OpenToken/releases):

- **Linux**: `opentoken-cli-{version}-linux-x64.zip`
- **macOS**: `opentoken-cli-{version}-macos-universal.zip` (Intel + Apple Silicon)
- **Windows**: `opentoken-cli-{version}-windows-x64.zip`

No dependencies required. Extract and run.

### Other Options

- **Docker**: Use `run-opentoken.sh` (Linux/Mac) or `run-opentoken.ps1` (Windows)
- **Python**: Install with `uv pip install opentoken-cli`, then run `opentoken` or `python -m opentoken_cli.main`

For installation details, see the [CLI Quickstart](../quickstarts/cli-quickstart.md).

## Security Note

Treat generated token outputs and metadata as **sensitive**. In particular, `tokenize` output is intended for internal use and should not be shared externally (for example, in tickets, chats, or public repos).

The `tokenize` subcommand is primarily used to build **internal overlap-analysis datasets** that can be joined against **encrypted tokens received from external partners** (after decryption). If you need to **exchange** tokens across organizations, use `package` and follow a controlled exchange process: [Sharing Tokenized Data](../operations/sharing-tokenized-data.md).

## Command Syntax

**Linux/macOS (Bash):**

```bash
# Self-contained executable
./opentoken [OPTIONS]

# Python
python -m opentoken_cli.main <subcommand> [OPTIONS]
```

**Windows (PowerShell):**

```powershell
# Self-contained executable
.\opentoken.exe [OPTIONS]

# Python
python -m opentoken_cli.main <subcommand> [OPTIONS]
```

## Arguments by Subcommand

### `package` (Default Encrypted Mode)

| Argument            | Short | Required | Description                                                                            |
| ------------------- | ----- | -------- | -------------------------------------------------------------------------------------- |
| `--input`           | `-i`  | Yes      | Path to input file (CSV or Parquet)                                                    |
| `--output`          | `-o`  | Yes      | Path to output file                                                                    |
| `--type`            | `-t`  | Yes      | File type: `csv` or `parquet`                                                          |
| `--hashingsecret`   | `-h`  | Yes      | Secret key for HMAC-SHA256 hashing                                                     |
| `--encryptionkey`   | `-e`  | Yes      | 32-character key for AES-256 encryption                                                |
| `--output-type`     | `-ot` | No       | Output file type if different from input                                               |
| `--hash-record-ids` |       | No       | SHA-256 hash each input `RecordId` before writing to output (one-way, no traceability) |

### `tokenize` (Hashed Tokens Only)

| Argument            | Short | Required         | Description                                                                            |
| ------------------- | ----- | ---------------- | -------------------------------------------------------------------------------------- |
| `--input`           | `-i`  | Yes              | Path to input file (CSV or Parquet)                                                    |
| `--output`          | `-o`  | Yes              | Path to output file                                                                    |
| `--type`            | `-t`  | Yes              | File type: `csv` or `parquet`                                                          |
| `--hashingsecret`   | `-h`  | Normal mode only | Secret key for HMAC-SHA256 hashing                                                     |
| `--demo-mode`       |       | No               | No hashing; outputs raw attribute signatures (see below)                               |
| `--output-type`     | `-ot` | No               | Output file type if different from input                                               |
| `--hash-record-ids` |       | No               | SHA-256 hash each input `RecordId` before writing to output (one-way, no traceability) |

### `encrypt` (Encrypt Input Tokens)

| Argument          | Short | Required | Description                              |
| ----------------- | ----- | -------- | ---------------------------------------- |
| `--input`         | `-i`  | Yes      | Path to input file (CSV or Parquet)      |
| `--output`        | `-o`  | Yes      | Path to output file                      |
| `--type`          | `-t`  | Yes      | File type: `csv` or `parquet`            |
| `--encryptionkey` | `-e`  | Yes      | 32-character key for AES-256 encryption  |
| `--output-type`   | `-ot` | No       | Output file type if different from input |

### `decrypt` (Decrypt Encrypted Tokens)

| Argument          | Short | Required | Description                              |
| ----------------- | ----- | -------- | ---------------------------------------- |
| `--input`         | `-i`  | Yes      | Path to input file (must be encrypted)   |
| `--output`        | `-o`  | Yes      | Path to output file                      |
| `--type`          | `-t`  | Yes      | File type: `csv` or `parquet`            |
| `--encryptionkey` | `-e`  | Yes      | 32-character key for AES-256 encryption  |
| `--output-type`   | `-ot` | No       | Output file type if different from input |

## Modes of Operation

### Encrypted Mode (Default)

Generates fully encrypted tokens using AES-256-GCM. Tokens can be decrypted later with the encryption key.

```bash
opentoken package \
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
opentoken tokenize \
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
opentoken tokenize \
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
  "OpenTokenVersion": "2.0.0-alpha",
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

### Bash (run-opentoken.sh)

```bash
./run-opentoken.sh package \
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

### PowerShell (run-opentoken.ps1)

```powershell
.\run-opentoken.ps1 package `
  -i .\input.csv `
  -o .\output.csv `
  -FileType csv `
  -h "HashingKey" `
  -e "EncryptionKey" `
  [-SkipBuild] `
  [-Verbose]
```

## Error Messages

| Error                                  | Cause                        | Solution                         |
| -------------------------------------- | ---------------------------- | -------------------------------- |
| "Encryption key not provided"          | Missing `-e` in package mode | Add `-e "key"` or use `tokenize` |
| "Encryption key must be 32 characters" | Key length wrong             | Use exactly 32 characters        |
| "Input file not found"                 | Invalid path                 | Check file exists                |
| "Unknown file type"                    | Invalid `-t` value           | Use `csv` or `parquet`           |
| "Invalid attribute: BirthDate"         | Date validation failed       | Use YYYY-MM-DD format            |

## Exit Codes

| Code | Meaning           |
| ---- | ----------------- |
| 0    | Success           |
| 1    | Invalid arguments |
| 2    | File not found    |
| 3    | Processing error  |

## Performance Tips

- Use Parquet for large datasets (faster I/O, compression)
- Use `tokenize` if decryption not needed (20-30% faster)
- For very large files, consider [PySpark integration](../operations/spark-or-databricks.md)

## Next Steps

- [Java API Reference](java-api.md) - Programmatic usage
- [Python API Reference](python-api.md) - Programmatic usage
- [Configuration](../config/configuration.md) - Advanced settings
- [Decrypting Tokens](../operations/decrypting-tokens.md) - Reverse encrypted tokens
