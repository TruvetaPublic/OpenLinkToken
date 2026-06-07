---
layout: default
---

# Running Batch Jobs

How to run Open Link Token in batch mode across CSV or Parquet files at scale using CLI or Docker.

---

## Overview

Open Link Token processes input files (CSV or Parquet) and produces two outputs:

1. **Tokens file** (CSV or Parquet): Contains `RecordId`, `RuleId`, `Token` columns
2. **Metadata file** (JSON): Processing statistics, secret hashes, and validation counts

When the output path ends in `.zip`, the `package` and `encrypt` commands bundle the output tokens file and exchange config JSON (plus metadata JSON for `package`) into a single zip archive for upload.

---

## CLI Batch Processing

### Basic Syntax

```bash
olt <subcommand> [OPTIONS]
```

### Required Arguments

| Argument            | Alias      | Description               | Example                                   |
| ------------------- | ---------- | ------------------------- | ----------------------------------------- |
| `-i`                | `--input`  | Input file path           | `-i data.csv`                             |
| `-o`                | `--output` | Output file path          | `-o tokens.csv`                           |
| `--exchange-config` |            | Exchange config JSON path | `--exchange-config ./batch.exchange.json` |

### Optional Arguments

| Argument            | Alias | Description                                         | Default                       |
| ------------------- | ----- | --------------------------------------------------- | ----------------------------- |
| `--private-key`     |       | Private key PEM used to decrypt the exchange config | Auto-discovered when possible |
| `--private-key-env` |       | Environment variable containing the private key PEM |                               |
| `tokenize`          |       | Tokenize without encryption                         | Subcommand                    |
| `decrypt`           |       | Decrypt mode                                        | Subcommand                    |

### CLI Example

```bash
cd lib/python/openlinktoken-cli
source ../../.venv/bin/activate
uv pip install -r requirements.txt -e . -e ../openlinktoken

olt package \
  -i ../../../resources/sample.csv \
  -o ../../../resources/output.csv \
  --exchange-config ../../../resources/batch.exchange.json
```

### ZIP Output

Pass a `.zip` path to `-o` to bundle the output tokens file, metadata JSON (for `package`), and exchange config into a single archive.

**`package` — tokens, metadata, and exchange config:**

```bash
olt package \
  -i ../../../resources/sample.csv \
  -o ../../../resources/output.zip \
  --exchange-config ../../../resources/batch.exchange.json
```

The resulting archive contains three files:

| File                   | Description                               |
| ---------------------- | ----------------------------------------- |
| `output.csv`           | Encrypted tokens (same format as input)   |
| `output.metadata.json` | Processing metadata                       |
| `batch.exchange.json`  | Exchange config used for this package run |

**`encrypt` — tokens and exchange config:**

```bash
olt encrypt \
  -i ../../../resources/hashed.csv \
  -o ../../../resources/output.zip \
  --exchange-config ../../../resources/batch.exchange.json
```

The resulting archive contains two files:

| File                  | Description                               |
| --------------------- | ----------------------------------------- |
| `output.csv`          | Encrypted tokens (same format as input)   |
| `batch.exchange.json` | Exchange config used for this encrypt run |

---

## Docker Batch Processing

### Convenience Scripts (Recommended)

**Bash (Linux/Mac):**

```bash
cd /path/to/OpenLinkToken

./run-openlinktoken.sh package \
  -i ./resources/sample.csv \
  -o ./resources/output.csv \
  --exchange-config ./resources/batch.exchange.json
```

**PowerShell (Windows):**

```powershell
cd C:\path\to\Open Link Token

.\run-openlinktoken.ps1 package `
  -i .\resources\sample.csv `
  -o .\resources\output.csv `
  --exchange-config .\resources\batch.exchange.json
```

### Script Options

| Option       | Bash | PowerShell   | Description          |
| ------------ | ---- | ------------ | -------------------- |
| Skip rebuild | `-s` | `-SkipBuild` | Reuse existing image |
| Verbose      | `-v` | `-Verbose`   | Show detailed output |

### Manual Docker Commands

```bash
# Build the image
docker build -t openlinktoken:latest .

# Run with sample data
docker run --rm -v $(pwd)/resources:/app/resources \
  openlinktoken:latest package \
  -i /app/resources/sample.csv \
  -o /app/resources/output.csv \
  --exchange-config /app/resources/batch.exchange.json

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
  "Version": "1.0.0",
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

### Environment Variables for Private Keys

Use this override when the CLI cannot auto-discover a matching key from `~/.openlinktoken/`.

```bash
export OLT_PRIVATE_KEY_PEM="$(cat ~/.openlinktoken/batch.private.pem)"

olt package \
  -i data.csv -o tokens.csv \
  --exchange-config ./batch.exchange.json \
  --private-key-env OLT_PRIVATE_KEY_PEM
```

### Logging and Monitoring

Check the metadata file after each run for:

- `TotalRowsWithInvalidAttributes`: Records that failed validation
- `InvalidAttributesByType`: Breakdown by attribute type
- `BlankTokensByRule`: Rules that produced blank tokens

---

## Troubleshooting

| Problem                                                  | Solution                                                                                          |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| "No private key matching this exchange config was found" | Pass `--private-key` / `--private-key-env`, or install the matching key under `~/.openlinktoken/` |
| "Invalid BirthDate"                                      | Use YYYY-MM-DD format; date must be 1910-01-01 to today                                           |
| "Column not found"                                       | Check column names match [accepted aliases](../config/configuration.md)                           |
| Docker build fails                                       | Ensure Docker is running; use absolute paths                                                      |

---

## Next Steps

- **Distributed processing**: [Spark or Databricks](spark-or-databricks.md)
- **Tokenize**: [Tokenize](tokenize.md)
- **Decrypt tokens**: [Decrypting Tokens](decrypting-tokens.md)
