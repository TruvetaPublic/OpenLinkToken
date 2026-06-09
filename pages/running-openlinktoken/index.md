---
layout: default
---

# Running Open Link Token

Guides for generating tokens in different environments and use cases.

## CLI Guide

The Open Link Token CLI accepts command-line arguments for flexible token generation.

### Basic Syntax

```bash
olt <subcommand> [OPTIONS]
```

### Arguments

#### All Subcommands

| Argument | Alias      | Required | Default                       | Description                      | Example         |
| -------- | ---------- | -------- | ----------------------------- | -------------------------------- | --------------- |
| `-i`     | `--input`  | Yes      |                               | Input file path (CSV or Parquet) | `-i data.csv`   |
| `-o`     | `--output` | No       | Auto-generated per subcommand | Output file path                 | `-o tokens.csv` |

#### Optional Arguments by Subcommand

| Argument            | Alias | `package` | `tokenize` | `encrypt` | `decrypt` | Description                                               | Default                       | Example                                                 |
| ------------------- | ----- | --------- | ---------- | --------- | --------- | --------------------------------------------------------- | ----------------------------- | ------------------------------------------------------- |
| `--exchange-config` |       | ✓         | ✓          | ✓         | ✓         | Exchange config JSON path                                 | Date-based default path       | `--exchange-config ./quickstart.exchange.json`          |
| `--private-key`     |       | ✓         | ✓          | ✓         | ✓         | Private key PEM used to decrypt the exchange config       | Auto-discovered when possible | `--private-key ~/.openlinktoken/quickstart.private.pem` |
| `--private-key-env` |       | ✓         | ✓          | ✓         | ✓         | Environment variable containing the private key PEM       |                               | `--private-key-env OLT_PRIVATE_KEY_PEM`                 |
| `--mode`            |       |           | ✓          |           |           | Tokenize mode selector: `default`, `hash-only`, or `demo` | `default`                     | `tokenize --mode hash-only`                             |

If a matching key already exists under `~/.openlinktoken/`, you can omit `--private-key` and `--private-key-env` for the commands that use an exchange config. `tokenize --mode hash-only` and `tokenize --mode demo` do not use exchange-config or private-key inputs.

### Usage Examples

#### Token Generation (Encryption Mode)

Generates encrypted tokens. Consumer commands resolve the hashing secret and transport key from an exchange config plus a matching private key.

```bash
cd lib/python/openlinktoken-cli
source ../../.venv/bin/activate
uv pip install -r requirements.txt -e . -e ../openlinktoken

olt package \
  -i ../../../resources/sample.csv \
  -o ../../../resources/output.csv \
  --exchange-config ../../../resources/quickstart.exchange.json
```

#### Token Generation (Tokenize)

Generates HMAC-SHA256 hashed tokens without transport encryption, using the same exchange-config workflow.

```bash
olt tokenize \
  -i ../../../resources/sample.csv \
  -o ../../../resources/hashed-output.csv \
  --exchange-config ../../../resources/quickstart.exchange.json
```

For deterministic SHA-256 output without HMAC or an exchange config, use:

```bash
olt tokenize \
  -i ../../../resources/sample.csv \
  -o ../../../resources/hash-only-output.csv \
  --mode hash-only
```

#### Token Decryption

Decrypts previously encrypted tokens using the same exchange config and a matching private key.

```bash
olt decrypt \
  -i ../../../resources/output.csv \
  -o ../../../resources/decrypted.csv \
  --exchange-config ../../../resources/quickstart.exchange.json
```

#### Key Pair Generation

Generates an ECDH public/private key pair and writes keys to `~/.openlinktoken/`.

```bash
olt generate-key-pair \
  --curve P-256 \
  --name my-key
```

This writes:

- `~/.openlinktoken/my-key.private.pem` — PKCS#8 PEM private key (permissions `600`)
- `~/.openlinktoken/my-key.public.pem` — SubjectPublicKeyInfo PEM public key (permissions `644`)
- `~/.openlinktoken/` directory is created with permissions `700` if it does not already exist.

If `--name` is omitted, a timestamp-based default name is used: `openlinktoken-<ISO8601-date>` (e.g., `openlinktoken-2025-03-05`).

To overwrite an existing key, add `--force`:

```bash
olt generate-key-pair --name my-key --force
```

Supported curves (`--curve` / `-c`):

| Curve   | Description                      |
| ------- | -------------------------------- |
| `P-256` | NIST P-256 / secp256r1 (default) |
| `P-384` | NIST P-384 / secp384r1           |
| `P-521` | NIST P-521 / secp521r1           |

### Output Files

Token generation produces two files:

**Tokens File** (CSV or Parquet):

```
RecordId,RuleId,Token
record1,T1,Gn7t1Zj16E5Qy+z9iINtczP6fRDYta6C0XFrQtpjnVQSEZ5pQXAzo02Aa9LS9oNMOog6Ssw9GZE6fvJrX2sQ/cThSkB6m91L
record1,T2,pUxPgYL9+cMxkA+8928Pil+9W+dm9kISwHYPdkZS+I2nQ/bQ/8HyL3FOVf3NYPW5NKZZO1OZfsz7LfKYpTlaxyzMLqMF2Wk7
...
```

**Metadata File** (always JSON, suffixed `.metadata.json`):

```json
{
  "JavaVersion": "21.0.0",
  "Version": "2.0.0-alpha",
  "Platform": "Java",
  "TotalRows": 1,
  "TotalRowsWithInvalidAttributes": 0,
  "InvalidAttributesByType": {},
  "BlankTokensByRule": {},
  "HashingSecretHash": "abc123...",
  "EncryptionSecretHash": "def456..."
}
```

See [Reference: Metadata Format](../reference/metadata-format.md) for detailed field descriptions.

### Console Output and Detailed Logs

For the long-running processing commands (`package`, `tokenize`, `encrypt`, and `decrypt`), the CLI keeps terminal output brief:

- Interactive terminals show a progress indicator while the command runs
- The command finishes with a short summary that surfaces the output path and the most important counts
- A detailed per-run log is written under the Open Link Token logs directory:
  - Linux / macOS: `~/.openlinktoken/logs`
  - Windows: `%APPDATA%\.openlinktoken\logs`

If a processing command fails after it starts, the CLI prints `Stack trace: <path>` and the traceback is appended to that same detailed log file.

---

## Docker

Use Docker for a containerized, dependency-free environment.

### Option 1: Convenience Scripts (Recommended)

Scripts automatically build and run the container.

**Bash (Linux/Mac):**

```bash
cd /path/to/OpenLinkToken

./run-openlinktoken.sh package \
  -i ./resources/sample.csv \
  -o ./resources/output.csv \
  --exchange-config ./resources/quickstart.exchange.json
```

**PowerShell (Windows):**

```powershell
cd C:\path\to\Open Link Token

.\run-openlinktoken.ps1 package `
  -i .\resources\sample.csv `
  -o .\resources\output.csv `
  --exchange-config .\resources\quickstart.exchange.json
```

#### Script Options

| Option       | Bash Alias | PowerShell   | Description          |
| ------------ | ---------- | ------------ | -------------------- |
| Skip rebuild | `-s`       | `-SkipBuild` | Reuse existing image |
| Verbose      | `-v`       | `-Verbose`   | Show detailed output |

Run with `--help` (Bash) or `-Help` (PowerShell) for full usage.

### Option 2: Manual Docker Commands

Build and run the image manually from the repository root.

```bash
# Build the image
docker build -t openlinktoken:latest .

# Run with sample data
docker run --rm -v $(pwd)/resources:/app/resources \
  openlinktoken:latest package \
  -i /app/resources/sample.csv \
  -o /app/resources/output.csv \
  --exchange-config /app/resources/quickstart.exchange.json

# View output
cat resources/output.csv
cat resources/output.metadata.json
```

**Dev Container:** If running in a dev container, use absolute path:

```bash
docker run --rm -v /workspaces/OpenLinkToken/resources:/app/resources \
  openlinktoken:latest ...
```

---

## PySpark Bridge

For large-scale distributed token generation and dataset overlap analysis, use the PySpark bridge.

### When to Use PySpark

- **Large datasets**: Millions of records across multiple files
- **Distributed processing**: Leverage cluster computing
- **Overlap analysis**: Find matching records across datasets at scale
- **Cost-effective**: Process on cloud infrastructure (AWS, GCP, Azure)

### Installation

Ensure the Python root venv is active, then install:

```bash
cd /path/to/OpenLinkToken
source .venv/bin/activate

cd lib/python/openlinktoken-pyspark
uv pip install -r requirements.txt -e .
```

### Basic Usage

```python
from openlinktoken_pyspark import SparkPersonTokenProcessor

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Open Link Token") \
    .getOrCreate()

# Create processor
processor = SparkPersonTokenProcessor(
    spark=spark,
    hashing_secret="HashingKey",
    encryption_key="Secret-Encryption-Key"
)

# Process dataset
tokens_df = processor.process_dataframe(
    input_df=input_spark_df,
    input_type="csv"  # or "parquet"
)

# Write output
tokens_df.coalesce(1).write \
    .mode("overwrite") \
    .csv("output/tokens")
```

### Examples

See example notebooks in `lib/python/openlinktoken-pyspark/notebooks/`:

- [Custom_Token_Definition_Guide.ipynb](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/lib/python/openlinktoken-pyspark/notebooks/Custom_Token_Definition_Guide.ipynb) – Define custom token rules
- [Dataset_Overlap_Analysis_Guide.ipynb](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/lib/python/openlinktoken-pyspark/notebooks/Dataset_Overlap_Analysis_Guide.ipynb) – Find overlapping records across datasets

---

## Troubleshooting

### "No private key matching this exchange config was found"

**Problem**: The CLI found the exchange config but could not auto-discover a matching key under `~/.openlinktoken/`.

**Solution**: Pass the correct key explicitly or provide it through an environment variable:

```bash
olt package \
  -i data.csv \
  -o output.csv \
  --exchange-config ./quickstart.exchange.json \
  --private-key ~/.openlinktoken/quickstart.private.pem
```

### "Invalid BirthDate" or "Date out of range"

**Problem**: BirthDate attribute fails validation.

**Causes**:

- Date is before January 1, 1910
- Date is in the future
- Format is not recognized

**Solution**: Use YYYY-MM-DD format or one of the accepted formats (MM/DD/YYYY, MM-DD-YYYY, DD.MM.YYYY):

```
Correct: 1980-01-15, 01/15/1980
Wrong:   1905-01-01, 2025-12-31, 01-15-80
```

### "Invalid SSN" or "SSN area/group/serial invalid"

**Problem**: SSN fails validation (area, group, or serial validation).

**Causes**:

- Area: 000, 666, or 900–999
- Group: 00
- Serial: 0000
- Common invalid sequences: 111-11-1111, 222-22-2222, etc.

**Solution**: Validate SSN before processing or regenerate test data. See [Security](../security.md) for full rules.

### "Invalid LastName" or "Name is placeholder"

**Problem**: Name is rejected as placeholder or invalid.

**Causes**:

- Value is placeholder: "Unknown", "Test", "N/A", "Anonymous", "Missing"
- LastName is too short (< 2 chars) without being special case ("Ng")
- Null or empty

**Solution**: Clean data before processing. Remove or replace placeholder values.

### "Docker image not found" or build fails

**Problem**: Docker image won't build or run.

**Causes**:

- Docker daemon not running
- Insufficient disk space
- File path issues on Windows

**Solution**:

1. Ensure Docker is running: `docker --version`
2. Use absolute paths, not relative: `/workspaces/OpenLinkToken/resources`
3. Clear Docker cache if needed: `docker system prune`
4. Check file permissions: `ls -la resources/sample.csv`

### Tokens produce unexpected results

**Problem**: Same input produces different tokens across runs or environments.

**Causes**:

- Different hashing/encryption secrets
- Different attribute normalization
- Unicode handling differences

**Solution**:

1. Verify secrets match exactly
2. Check attribute normalization (see [Concepts: Normalization](../concepts/normalization-and-validation.md))
3. Run the interoperability test suite: `tools/interoperability/multi_language_interoperability_test.py`
4. Decrypt and compare hashes to isolate the issue

### CSV parsing errors or column not found

**Problem**: "Column 'FirstName' not found" or CSV parse error.

**Causes**:

- Column names don't match expected aliases
- Commas within values without quoting
- Encoding issues (non-UTF-8)

**Solution**:

1. Verify column names match accepted aliases (see [Configuration](../config/configuration.md))
2. Quote values containing commas: `"Doe, Jr."`
3. Ensure UTF-8 encoding
4. Use Parquet format if CSV parsing continues to fail

---

## Next Steps

- **Get started**: [Quickstarts](../quickstarts/index.md)
- **Configure input formats**: [Configuration](../config/configuration.md)
- **Understand token matching**: [Concepts: Token Rules](../concepts/token-rules.md)
- **Read metadata format**: [Reference: Metadata Format](../reference/metadata-format.md)
- **Contribute improvements**: [Community: Contributing](../community/contributing.md)
