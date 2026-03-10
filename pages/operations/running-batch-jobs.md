---
layout: default
---

# Running Batch Jobs

How to run OpenToken in batch mode across CSV or Parquet files at scale using CLI or Docker.

---

## Overview

OpenToken processes input files (CSV or Parquet) and produces two outputs:

1. **Tokens file** (CSV or Parquet): Contains `RecordId`, `RuleId`, `Token` columns
2. **Metadata file** (JSON): Processing statistics, secret hashes, and validation counts

---

## CLI Batch Processing

### Basic Syntax

```bash
opentoken <subcommand> [OPTIONS]
```

### Required Arguments

| Argument | Alias             | Description                          | Example         |
| -------- | ----------------- | ------------------------------------ | --------------- |
| `-i`     | `--input`         | Input file path                      | `-i data.csv`   |
| `-t`     | `--type`          | Input file type (`csv` or `parquet`) | `-t csv`        |
| `-o`     | `--output`        | Output file path                     | `-o tokens.csv` |
| `-h`     | `--hashingsecret` | HMAC-SHA256 hashing secret           | `-h "MyKey"`    |

### Optional Arguments

| Argument | Alias             | Description                 | Default                    |
| -------- | ----------------- | --------------------------- | -------------------------- |
| `-e`     | `--encryptionkey` | AES-256 encryption key      | Required in `package` mode |
| `-ot`    | `--output-type`   | Output file type            | Same as input              |
|          | `tokenize`        | Tokenize without encryption | Subcommand                 |
|          | `decrypt`         | Decrypt mode                | Subcommand                 |

### CLI Example

```bash
cd lib/python/opentoken-cli
source ../../.venv/bin/activate
uv pip install -r requirements.txt -e . -e ../opentoken

opentoken package \
  -i ../../../resources/sample.csv \
  -t csv \
  -o ../../../resources/output.csv \
  -h "HashingKey" \
  -e "Secret-Encryption-Key-Goes-Here."
```

---

## Docker Batch Processing

### Convenience Scripts (Recommended)

**Bash (Linux/Mac):**

```bash
cd /path/to/OpenToken

./run-opentoken.sh package \
  -i ./resources/sample.csv \
  -o ./resources/output.csv \
  -t csv \
  -h "HashingKey" \
  -e "Secret-Encryption-Key-Goes-Here."
```

**PowerShell (Windows):**

```powershell
cd C:\path\to\OpenToken

.\run-opentoken.ps1 package `
  -i .\resources\sample.csv `
  -o .\resources\output.csv `
  -FileType csv `
  -h "HashingKey" `
  -e "Secret-Encryption-Key-Goes-Here."
```

### Script Options

| Option       | Bash | PowerShell   | Description          |
| ------------ | ---- | ------------ | -------------------- |
| File type    | `-t` | `-FileType`  | `csv` or `parquet`   |
| Skip rebuild | `-s` | `-SkipBuild` | Reuse existing image |
| Verbose      | `-v` | `-Verbose`   | Show detailed output |

### Manual Docker Commands

```bash
# Build the image
docker build -t opentoken:latest .

# Run with sample data
docker run --rm -v $(pwd)/resources:/app/resources \
  opentoken:latest package \
  -i /app/resources/sample.csv \
  -t csv \
  -o /app/resources/output.csv \
  -h "HashingKey" \
  -e "Secret-Encryption-Key-Goes-Here."

# View output
cat resources/output.csv
cat resources/output.metadata.json
```

---

## Exit Codes

| Exit Code | Meaning                                                 |
| --------- | ------------------------------------------------------- |
| `0`       | Success                                                 |
| `1`       | General error (invalid arguments, file not found, etc.) |
| Non-zero  | Processing failure; check stderr for details            |

---

## Output Files

### Tokens File (CSV)

```csv
RecordId,RuleId,Token
ID001,T1,Gn7t1Zj16E5Qy+z9iINtczP6fRDYta6C0XFrQtpjnVQSEZ5pQXAzo02Aa9LS9oNMOog6Ssw9GZE6fvJrX2sQ/cThSkB6m91L
ID001,T2,pUxPgYL9+cMxkA+8928Pil+9W+dm9kISwHYPdkZS+I2nQ/bQ/8HyL3FOVf3NYPW5NKZZO1OZfsz7LfKYpTlaxyzMLqMF2Wk7
...
```

**Rows per input record:** 5 (one per rule T1–T5)

### Metadata File (JSON)

```json
{
  "Platform": "Java",
  "JavaVersion": "21.0.0",
  "OpenTokenVersion": "1.0.0",
  "TotalRows": 100,
  "TotalRowsWithInvalidAttributes": 3,
  "InvalidAttributesByType": { "BirthDate": 2, "PostalCode": 1 },
  "BlankTokensByRule": { "T1": 2, "T2": 1 },
  "HashingSecretHash": "abc123...",
  "EncryptionSecretHash": "def456..."
}
```

See [Reference: Metadata Format](../reference/metadata-format.md) for complete field descriptions.

---

## Common Patterns

### Environment Variables for Secrets

```bash
export OPENTOKEN_HASHING_SECRET="MyHashingKey"
export OPENTOKEN_ENCRYPTION_KEY="MyEncryptionKey32CharactersLong"

opentoken package \
  -i data.csv -t csv -o tokens.csv \
  -h "$OPENTOKEN_HASHING_SECRET" \
  -e "$OPENTOKEN_ENCRYPTION_KEY"
```

### Logging and Monitoring

Check the metadata file after each run for:

- `TotalRowsWithInvalidAttributes`: Records that failed validation
- `InvalidAttributesByType`: Breakdown by attribute type
- `BlankTokensByRule`: Rules that produced blank tokens

---

## Troubleshooting

| Problem                       | Solution                                                                |
| ----------------------------- | ----------------------------------------------------------------------- |
| "Encryption key not provided" | Add `-e "YourKey"` or run `tokenize` subcommand                         |
| "Invalid BirthDate"           | Use YYYY-MM-DD format; date must be 1910-01-01 to today                 |
| "Column not found"            | Check column names match [accepted aliases](../config/configuration.md) |
| Docker build fails            | Ensure Docker is running; use absolute paths                            |

---

## Next Steps

- **Distributed processing**: [Spark or Databricks](spark-or-databricks.md)
- **Tokenize**: [Tokenize](tokenize.md)
- **Decrypt tokens**: [Decrypting Tokens](decrypting-tokens.md)
