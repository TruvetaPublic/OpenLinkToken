---
layout: default
---

# Configuration

Configuration options for OpenLinkToken inputs, outputs, secrets, and runtime behavior.

---

## CLI Arguments

OpenLinkToken can be run from the Python CLI or via the helper shell/PowerShell scripts.

At a high level you must always specify:

- the input path and type (CSV or Parquet)
- an output path for tokens
- a hashing secret (required)
- either an encryption key (for `package`) or the `tokenize` subcommand to skip encryption
- optionally the `decrypt` subcommand when reading previously encrypted tokens

For the complete, authoritative list of flags, short options, and defaults, see the [CLI Reference](../reference/cli.md).

---

## Environment Variables

Secrets can be passed via environment variables for security:

```bash
export OLT_HASHING_SECRET="MyHashingKey"
export OLT_ENCRYPTION_KEY="MyEncryptionKey32CharactersLong"

olt package \
  -i data.csv -t csv -o tokens.csv \
  -h "$OLT_HASHING_SECRET" \
  -e "$OLT_ENCRYPTION_KEY"
```

### Docker Environment

```bash
docker run --rm \
  -e OLT_HASHING_SECRET="MyHashingKey" \
  -e OLT_ENCRYPTION_KEY="MyEncryptionKey32CharactersLong" \
  -v $(pwd)/resources:/app/resources \
  openlinktoken:latest package \
  -i /app/resources/sample.csv \
  -t csv \
  -o /app/resources/output.csv \
  -h "$OLT_HASHING_SECRET" \
  -e "$OLT_ENCRYPTION_KEY"
```

---

## Input File Format

### Supported Formats

| Format  | Extension  | Description                                          |
| ------- | ---------- | ---------------------------------------------------- |
| CSV     | `.csv`     | Comma-separated values with header row               |
| Parquet | `.parquet` | Columnar binary format (recommended for large files) |

### Column Names & Aliases

Input columns are **case-insensitive** and support common aliases:

| Attribute       | Accepted Column Names                                  | Required | Type   |
| --------------- | ------------------------------------------------------ | -------- | ------ |
| **Record ID**   | `RecordId`, `Id`                                       | Optional | String |
| **First Name**  | `FirstName`, `GivenName`                               | Yes      | String |
| **Last Name**   | `LastName`, `Surname`                                  | Yes      | String |
| **Birth Date**  | `BirthDate`, `DateOfBirth`                             | Yes      | Date   |
| **Sex**         | `Sex`, `Gender`                                        | Yes      | String |
| **Postal Code** | `PostalCode`, `ZipCode`, `ZIP3`, `ZIP4`, `ZIP5`        | Yes      | String |
| **SSN**         | `SocialSecurityNumber`, `NationalIdentificationNumber` | Yes      | String |

### Date Formats Accepted

- `YYYY-MM-DD` (recommended)
- `MM/DD/YYYY`
- `MM-DD-YYYY`
- `DD.MM.YYYY`

### Sex Values Accepted

- `Male`, `M`
- `Female`, `F`

(Case-insensitive)

### SSN Formats Accepted

- `123-45-6789` (preferred input format)
- Digits-only values (normalized automatically; dashes removed internally)

### Postal Code Formats

**US ZIP Codes:**

- `98004` (5 digits)
- `98004-1234` (9 digits, dash removed)
- `980` (ZIP-3, auto-padded to `98000`)

**Canadian Postal Codes:**

- `K1A 1A1` (with space)
- `K1A1A1` (without space, auto-formatted)

---

## Output Configuration

### Output Type Override

Use `-ot` to specify a different output format:

```bash
# Input CSV, output Parquet
olt package \
  -i data.csv -t csv \
  -o tokens.parquet -ot parquet \
  -h "HashingKey" -e "EncryptionKey"
```

### Output Files Generated

Each run produces two files:

1. **Tokens file**: `<output_path>` (CSV or Parquet)
2. **Metadata file**: `<output_path>.metadata.json` (always JSON)

---

## Processing Modes

OpenLinkToken supports three processing modes that control how token signatures are transformed:

- **Encryption (default)** – produces encrypted tokens suitable for external exchange; requires both a hashing secret and an encryption key.
- **Tokenize** – produces one-way hashed tokens for internal matching and overlap analysis; requires only the hashing secret.
- **Decrypt** – takes previously encrypted tokens and decrypts them back to their hashed form (equivalent to `tokenize` output).

For the exact CLI flags that enable each mode, see the [CLI Reference](../reference/cli.md).

---

## Secret Requirements

### Hashing Secret

- **Purpose**: HMAC-SHA256 key for deterministic hashing
- **Minimum length**: 8 characters recommended
- **Best practice**: 16+ characters with mixed case and digits

### Encryption Key

- **Purpose**: AES-256-GCM symmetric encryption key
- **Required length**: Exactly 32 characters (32 bytes)
- **Error if wrong length**: "Key must be 32 characters long"

---

## Environment-Specific Configuration

### Local Development

```bash
# Python
source ../../.venv/bin/activate
python -m openlinktoken_cli.main package \
  -i ../../resources/sample.csv -t csv -o ../../resources/output.csv \
  -h "HashingKey" -e "EncryptionKey32Characters!!!!!"
```

### Docker Container

```bash
./run-openlinktoken.sh package \
  -i ./resources/sample.csv \
  -o ./resources/output.csv \
  -t csv \
  -h "HashingKey" \
  -e "EncryptionKey32Characters!!!!!"
```

### Spark/Databricks Cluster

```python
from openlinktoken_pyspark import OpenLinkTokenProcessor

processor = OpenLinkTokenProcessor(
    hashing_secret=dbutils.secrets.get("openlinktoken", "hashing_secret"),
    encryption_key=dbutils.secrets.get("openlinktoken", "encryption_key")
)
```

See [Spark or Databricks](../operations/spark-or-databricks.md) for cluster configuration.

---

## Handling Missing/Invalid Data

| Scenario                    | Behavior                                              |
| --------------------------- | ----------------------------------------------------- |
| **RecordId missing**        | Auto-generates UUID for each record                   |
| **Required column missing** | Processing fails with column name mismatch error      |
| **NULL/empty value**        | Record marked invalid; counted in metadata            |
| **Invalid attribute**       | Record marked invalid; blank token for affected rules |

---

## Next Steps

- **Batch processing**: [Running Batch Jobs](../operations/running-batch-jobs.md)
- **Metadata format**: [Reference: Metadata Format](../reference/metadata-format.md)
