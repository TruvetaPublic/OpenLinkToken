---
layout: default
---

# Running OpenToken

Guides for generating tokens in different environments and use cases.

## CLI Guide

The OpenToken CLI accepts command-line arguments for flexible token generation. Both Java and Python CLIs support identical options.

### Basic Syntax

```bash
opentoken-cli [OPTIONS] -i <input> -t <type> -o <output> -h <hashing-secret> [-e <encryption-key>]
```

### Arguments

#### Required

| Argument | Alias             | Description                      | Example                  |
| -------- | ----------------- | -------------------------------- | ------------------------ |
| `-i`     | `--input`         | Input file path (CSV or Parquet) | `-i data.csv`            |
| `-t`     | `--type`          | Input file type                  | `-t csv` or `-t parquet` |
| `-o`     | `--output`        | Output file path                 | `-o tokens.csv`          |
| `-h`     | `--hashingsecret` | HMAC-SHA256 hashing secret       | `-h "MyHashingKey"`      |

#### Optional

| Argument | Alias             | Description                                | Default                         | Example                |
| -------- | ----------------- | ------------------------------------------ | ------------------------------- | ---------------------- |
| `-e`     | `--encryptionkey` | AES-256 encryption key                     | Required (unless `--hash-only`) | `-e "MyEncryptionKey"` |
| `-ot`    | `--output-type`   | Output file type                           | Same as input type              | `-ot parquet`          |
|          | `--hash-only`     | Hash-only mode (no encryption)             | False                           | `--hash-only`          |
| `-d`     | `--decrypt`       | Decrypt mode (reverse previous encryption) | False                           | `-d`                   |

### Usage Examples

#### Token Generation (Encryption Mode)

Generates encrypted tokens. Both hashing secret and encryption key required.

**Java:**
```bash
cd lib/java
mvn clean install -DskipTests

java -jar opentoken-cli/target/opentoken-cli-*.jar \
  -i ../../resources/sample.csv \
  -t csv \
  -o ../../resources/output.csv \
  -h "HashingKey" \
  -e "Secret-Encryption-Key-Goes-Here."
```

**Python:**
```bash
cd lib/python/opentoken-cli
source ../../.venv/bin/activate
pip install -r requirements.txt -e . -e ../opentoken

python -m opentoken_cli.main \
  -i ../../../resources/sample.csv \
  -t csv \
  -o ../../../resources/output.csv \
  -h "HashingKey" \
  -e "Secret-Encryption-Key-Goes-Here."
```

#### Token Generation (Hash-Only Mode)

Generates HMAC-SHA256 hashed tokens without AES encryption. Only hashing secret required.

**Java:**
```bash
java -jar opentoken-cli/target/opentoken-cli-*.jar \
  --hash-only \
  -i ../../resources/sample.csv \
  -t csv \
  -o ../../resources/hashed-output.csv \
  -h "HashingKey"
```

**Python:**
```bash
python -m opentoken_cli.main \
  --hash-only \
  -i ../../../resources/sample.csv \
  -t csv \
  -o ../../../resources/hashed-output.csv \
  -h "HashingKey"
```

#### Token Decryption

Decrypts previously encrypted tokens. Only encryption key required.

**Java:**
```bash
java -jar opentoken-cli/target/opentoken-cli-*.jar \
  -d \
  -i ../../resources/output.csv \
  -t csv \
  -o ../../resources/decrypted.csv \
  -e "Secret-Encryption-Key-Goes-Here."
```

**Python:**
```bash
python -m opentoken_cli.main \
  -d \
  -i ../../../resources/output.csv \
  -t csv \
  -o ../../../resources/decrypted.csv \
  -e "Secret-Encryption-Key-Goes-Here."
```

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
  "OpenTokenVersion": "2.0.0-alpha",
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

---

## Docker

Use Docker for a containerized, dependency-free environment.

### Option 1: Convenience Scripts (Recommended)

Scripts automatically build and run the container.

**Bash (Linux/Mac):**
```bash
cd /path/to/OpenToken

./run-opentoken.sh \
  -i ./resources/sample.csv \
  -o ./resources/output.csv \
  -t csv \
  -h "HashingKey" \
  -e "Secret-Encryption-Key-Goes-Here."
```

**PowerShell (Windows):**
```powershell
cd C:\path\to\OpenToken

.\run-opentoken.ps1 `
  -i .\resources\sample.csv `
  -o .\resources\output.csv `
  -FileType csv `
  -h "HashingKey" `
  -e "Secret-Encryption-Key-Goes-Here."
```

#### Script Options

| Option       | Bash Alias | PowerShell   | Description          |
| ------------ | ---------- | ------------ | -------------------- |
| File type    | `-t`       | `-FileType`  | `csv` or `parquet`   |
| Skip rebuild | `-s`       | `-SkipBuild` | Reuse existing image |
| Verbose      | `-v`       | `-Verbose`   | Show detailed output |

Run with `--help` (Bash) or `-Help` (PowerShell) for full usage.

### Option 2: Manual Docker Commands

Build and run the image manually from the repository root.

```bash
# Build the image
docker build -t opentoken:latest .

# Run with sample data
docker run --rm -v $(pwd)/resources:/app/resources \
  opentoken:latest \
  -i /app/resources/sample.csv \
  -t csv \
  -o /app/resources/output.csv \
  -h "HashingKey" \
  -e "Secret-Encryption-Key-Goes-Here."

# View output
cat resources/output.csv
cat resources/output.metadata.json
```

**Dev Container:** If running in a dev container, use absolute path:
```bash
docker run --rm -v /workspaces/OpenToken/resources:/app/resources \
  opentoken:latest ...
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
source /workspaces/OpenToken/.venv/bin/activate

cd lib/python/opentoken-pyspark
pip install -r requirements.txt -e .
```

### Basic Usage

```python
from opentoken_pyspark import SparkPersonTokenProcessor

# Initialize Spark session
spark = SparkSession.builder \
    .appName("OpenToken") \
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

See example notebooks in `lib/python/opentoken-pyspark/notebooks/`:

- [Custom_Token_Definition_Guide.ipynb](https://github.com/TruvetaPublic/OpenToken/blob/main/lib/python/opentoken-pyspark/notebooks/Custom_Token_Definition_Guide.ipynb) – Define custom token rules
- [Dataset_Overlap_Analysis_Guide.ipynb](https://github.com/TruvetaPublic/OpenToken/blob/main/lib/python/opentoken-pyspark/notebooks/Dataset_Overlap_Analysis_Guide.ipynb) – Find overlapping records across datasets

---

## Troubleshooting

### "Encryption key not provided"

**Problem**: Error when running without `-e` flag and without `--hash-only`.

**Solution**: Either provide encryption key `-e "YourKey"` or use `--hash-only`:
```bash
java -jar opentoken-cli-*.jar --hash-only -i data.csv -t csv -o output.csv -h "HashingKey"
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
2. Use absolute paths, not relative: `/workspaces/OpenToken/resources`
3. Clear Docker cache if needed: `docker system prune`
4. Check file permissions: `ls -la resources/sample.csv`

### Tokens don't match across Java/Python

**Problem**: Same input produces different tokens in Java vs. Python.

**Causes**:
- Different hashing/encryption secrets
- Different attribute normalization
- Unicode handling differences

**Solution**:
1. Verify secrets match exactly
2. Check attribute normalization (see [Concepts: Normalization](../concepts/normalization-and-validation.md))
3. Run the interoperability test suite: `tools/interoperability/java_python_interoperability_test.py`
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
