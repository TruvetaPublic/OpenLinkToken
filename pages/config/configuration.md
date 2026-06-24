---
layout: default
---

# Configuration

Configuration options for Open Link Token inputs, outputs, secrets, and runtime behavior.

---

## CLI Arguments

Open Link Token can be run from the Python CLI or via the helper shell/PowerShell scripts.

At a high level you must always specify:

- the input path and type (CSV or Parquet)
- an output path for tokens
- an exchange config for consumer commands (`package`, `tokenize`, `encrypt`, `decrypt`)
- either a matching private key, a private-key environment variable, or a locally discoverable key under `~/.openlinktoken/`
- optionally the `decrypt` subcommand when reading previously encrypted tokens

For the complete, authoritative list of flags, short options, and defaults, see the [CLI Reference](../reference/cli.md).

---

## Environment Variables

Consumer commands usually auto-discover the matching private key from `~/.openlinktoken/` when you provide the exchange config:

```bash
olt package \
  -i data.csv -o tokens.csv \
  --exchange-config ./openlinktoken-2026-05-01.exchange.json
```

### Docker Environment

If the runtime cannot auto-discover the matching key, override it explicitly with `--private-key-env`:

```bash
docker run --rm \
  -e OLT_PRIVATE_KEY_PEM="$(cat ~/.openlinktoken/openlinktoken-2026-05-01.private.pem)" \
  -v $(pwd)/resources:/app/resources \
  openlinktoken:latest package \
  -i /app/resources/sample.csv \
  -o /app/resources/output.csv \
  --exchange-config /app/resources/openlinktoken-2026-05-01.exchange.json \
  --private-key-env OLT_PRIVATE_KEY_PEM
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

### Output Format

The output format is auto-detected from the file extension of `-o` (or from the input extension when `-o` is omitted):

```bash
# Input CSV, output Parquet
olt package -i data.csv -o tokens.parquet
```

Supported extensions: `.csv`, `.parquet`. The `package` and `encrypt` subcommands additionally accept `.zip` for self-contained bundles (see [Output Files Generated](#output-files-generated)).

### Output Files Generated

For CSV or Parquet output, each run produces two files:

1. **Tokens file**: `<output_path>` (CSV or Parquet)
2. **Metadata file**: `<output_path>.metadata.json` (always JSON)

When the output path ends in `.zip`, the `package` command bundles all three files into a single archive:

1. `<stem>.parquet` — encrypted tokens (always Parquet)
2. `<stem>.metadata.json` — processing metadata
3. `<exchange-config-filename>.exchange.json` — exchange config

The `encrypt` command also supports `.zip` output, bundling two files (no metadata):

1. `<stem>.csv` (or `.parquet`) — encrypted tokens (same format as input)
2. `<exchange-config-filename>.exchange.json` — exchange config

---

## Processing Modes

Open Link Token supports three processing modes that control how token signatures are transformed:

- **Encryption (default)** – produces encrypted tokens suitable for external exchange; resolves the hashing secret and transport key from an exchange config plus a matching private key.
- **Tokenize** – produces one-way hashed tokens for internal matching and overlap analysis; resolves the hashing secret from the same exchange-config workflow.
- **Decrypt** – takes previously encrypted tokens and decrypts them back to their hashed form (equivalent to `tokenize` output) using the exchange config and a matching private key.

For the exact CLI flags that enable each mode, see the [CLI Reference](../reference/cli.md).

---

## Secret Requirements

### Hashing Secret

- **Purpose**: HMAC-SHA256 key for deterministic hashing
- **Minimum length**: 8 characters recommended
- **Best practice**: 16+ characters with mixed case and digits

### Encryption Key

- **Purpose**: AES-256-GCM symmetric encryption key
- **Required length**: Exactly 32 bytes (a 32-character ASCII string also satisfies this)
- **Error if wrong length**: `Key must be 32 bytes long`

---

## Environment-Specific Configuration

### Local Development

```bash
# Python
source ../../.venv/bin/activate
python -m openlinktoken_cli.main package \
  -i ../../resources/sample.csv -o ../../resources/output.csv \
  --exchange-config ../../resources/openlinktoken-2026-05-01.exchange.json
```

### Docker Container

```bash
./run-olt.sh package \
  -i ./resources/sample.csv \
  -o ./resources/output.csv \
  --exchange-config ./resources/openlinktoken-2026-05-01.exchange.json
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
