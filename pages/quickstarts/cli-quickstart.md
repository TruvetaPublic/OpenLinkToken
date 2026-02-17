---
layout: default
---

# CLI Quickstart

For a high-level overview and other entry points, see [Quickstarts](index.md).

Run the OpenToken CLI end-to-end to generate tokens from a sample dataset in minutes.

## Prerequisites

Choose one of:

- **Docker** (recommended) - No other dependencies needed
- **Java 21+** and Maven 3.8+
- **Python 3.10+**

## Quick Start with Docker

The fastest way to get started. No Java or Python installation required.

### Linux/Mac

```bash
cd /path/to/OpenToken

./run-opentoken.sh \
  -i ./resources/sample.csv \
  -o ./resources/output.csv \
  -t csv \
  -h "HashingKey" \
  -e "Secret-Encryption-Key-Goes-Here."
```

### Windows PowerShell

```powershell
cd C:\path\to\OpenToken

.\run-opentoken.ps1 `
  -i .\resources\sample.csv `
  -o .\resources\output.csv `
  -FileType csv `
  -h "HashingKey" `
  -e "Secret-Encryption-Key-Goes-Here."
```

## CLI Arguments

| Argument          | Short | Description                                | Required |
| ----------------- | ----- | ------------------------------------------ | -------- |
| `--input`         | `-i`  | Input file path (CSV or Parquet)           | Yes      |
| `--output`        | `-o`  | Output file path                           | Yes      |
| `--type`          | `-t`  | File type: `csv` or `parquet`              | Yes      |
| `--hashingsecret` | `-h`  | Secret key for HMAC hashing                | Yes      |
| `--encryptionkey` | `-e`  | 32-character key for AES encryption        | No*      |
| `--hash-only`     |       | Skip encryption, output hashed tokens only | No       |

*Required unless `--hash-only` is specified.

## Example: CSV Input

**Input file (`sample.csv`):**

```csv
RecordId,FirstName,LastName,BirthDate,Sex,PostalCode,SSN
patient_001,John,Doe,1980-01-15,Male,98004,123-45-6789
patient_002,Jane,Smith,1975-03-22,Female,90210,987-65-4321
```

**Command:**

```bash
java -jar opentoken-cli-*.jar \
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

## Example: Parquet Input

```bash
java -jar opentoken-cli-*.jar \
  -i input.parquet \
  -t parquet \
  -o tokens.parquet \
  -h "MyHashingSecret" \
  -e "MyEncryptionKey-32Characters!"
```

## Hash-Only Mode

Generate tokens without encryption (faster, but tokens cannot be decrypted):

```bash
java -jar opentoken-cli-*.jar \
  -i sample.csv \
  -t csv \
  -o tokens.csv \
  -h "MyHashingSecret" \
  --hash-only
```

### Security Note (Hash-Only)

`--hash-only` output is intended for **internal use** and should **not** be shared externally. Hash-only tokens are deterministic and can still be linkable across datasets.

The primary use case for hash-only mode is to build an **internal overlap-analysis dataset** that you join against **encrypted tokens received from an external partner** (after decrypting their tokens to the hash-only equivalent). If you need to exchange tokens across organizations, use encrypted mode and follow [Sharing Tokenized Data](../operations/sharing-tokenized-data.md).

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
  "Platform": "Java",
  "JavaVersion": "21.0.0",
  "OpenTokenVersion": "1.7.0",
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

Either provide `-e "YourKey"` or use `--hash-only` flag.

### "Invalid BirthDate"

Ensure dates are in `YYYY-MM-DD` format and between 1910-01-01 and today.

### "File not found"

Check that input file path is correct and file exists.

### "Invalid SSN"

SSN must be 9 digits. Area code cannot be 000, 666, or 900-999.

## Next Steps

- [Java Quickstart](java-quickstart.md) - Build from source
- [Python Quickstart](python-quickstart.md) - Use Python CLI
- [Configuration](../config/configuration.md) - Advanced options
- [Token Rules](../concepts/token-rules.md) - Understand T1-T5
