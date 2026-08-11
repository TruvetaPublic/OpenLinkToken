---
layout: default
---

# Configuration & Tuning

Input formats, output modes, and customization options.

## Input File Format

Open Link Token processes CSV and Parquet files. Both formats support the same attribute columns with flexible naming.

### Column Names & Aliases

Input columns are case-insensitive and support common aliases:

| Attribute                  | Accepted Column Names                                         | Required | Type   | Example                                       |
| -------------------------- | ------------------------------------------------------------- | -------- | ------ | --------------------------------------------- |
| **Record ID**              | `RecordId`, `Id`                                              | Optional | String | `patient_123`, `uuid-abc...`                  |
| **First Name**             | `FirstName`, `GivenName`                                      | Yes      | String | `John`                                        |
| **Last Name**              | `LastName`, `Surname`                                         | Yes      | String | `Doe`                                         |
| **Birth Date**             | `BirthDate`, `DateOfBirth`                                    | Yes      | Date   | `1980-01-15`                                  |
| **Sex**                    | `Sex`, `Gender`                                               | Yes      | String | `Male`, `M`, `Female`, `F`                    |
| **Postal Code**            | `PostalCode`, `ZipCode`, `ZIP3`, `ZIP4`, `ZIP5`               | Yes      | String | `98004`, `K1A 1A1`                            |
| **Social Security Number** | `SocialSecurityNumber`, `NationalIdentificationNumber`, `SSN` | Yes      | String | `123-45-6789` (digits-only values normalized) |

These mappings describe the Python CLI. Column names are matched
case-insensitively.

### CSV Format

CSV files must include the required columns (with any accepted column name):

```csv
RecordId,FirstName,LastName,BirthDate,Sex,PostalCode,SSN
ID001,John,Doe,1980-01-15,Male,98004,123-45-6789
ID002,Jane,Smith,1975-06-20,Female,K1A1A1,987-65-4321
ID003,Robert,Johnson,1990-03-10,Male,10001,456-78-9123
```

**Requirements:**

- Header row is required
- Columns can be in any order
- All required attributes must be present (RecordId is optional)
- Use quoted values for commas within fields: `"Doe, Jr."`
- UTF-8 encoding recommended

**Date Formats Accepted:**

- `YYYY-MM-DD` (recommended)
- `MM/DD/YYYY`
- `MM-DD-YYYY`
- `DD.MM.YYYY`

**Sex Values Accepted:**

- `Male`, `M`
- `Female`, `F`
  (Case-insensitive)

**SSN Formats Accepted:**

- `123-45-6789` (preferred input format)
- Digits-only values (normalized automatically; dashes removed internally)

**Postal Code Formats:**

- **US ZIP:** `98004` (5 digits), `98004-1234` (9 digits), `980` (ZIP-3, auto-padded to 98000)
- **Canadian:** `K1A 1A1` (postal code with space), `K1A1A1` (without space, auto-formatted)

### Parquet Format

Parquet files follow the same column naming conventions and requirements as CSV:

```python
import pyarrow.parquet as pq

# Read with Open Link Token
df = pq.read_table("data.parquet").to_pandas()

# Must have required columns
assert "FirstName" in df.columns or "GivenName" in df.columns
```

When writing Parquet output, use standard Parquet compression (Snappy or Gzip).

### Handling Missing/Invalid Data

| Scenario                    | Behavior                                                           |
| --------------------------- | ------------------------------------------------------------------ |
| **RecordId missing**        | Auto-generates UUID for each record                                |
| **Required column missing** | Processing fails; column name mismatch error                       |
| **NULL/empty value**        | Record marked invalid; counted in `TotalRowsWithInvalidAttributes` |
| **Invalid attribute**       | Record marked invalid; counted in `InvalidAttributesByType`        |
| **All attributes valid**    | Record processed; up to 6 tokens generated (T1–T5 plus ML1)        |

Records with invalid attributes are still output (with blank tokens for that rule), but flagged in metadata. ML1 is
generated only when its five required attributes are valid; pass `--disable-inferencing` to omit it.

---

## Output File Format

`package` and `tokenize` generate tokens plus metadata. `encrypt` and `decrypt`
write token files only and do not emit metadata.

### Tokens Output

CSV or Parquet file (same format as input; when packaged via the `package` command with ZIP output, always parquet by default):

```csv
RecordId,RuleId,Token
ID001,T1,olt.V1.<JWE compact serialization>
ID001,T2,olt.V1.<JWE compact serialization>
ID001,T3,olt.V1.<JWE compact serialization>
ID001,T4,olt.V1.<JWE compact serialization>
ID001,T5,olt.V1.<JWE compact serialization>
ID001,ML1,olt.V1.<JWE compact serialization>
ID002,T1,...
```

**Columns:**

- `RecordId`: From input (or auto-generated UUID)
- `RuleId`: Token rule identifier (`T1`–`T5` or `ML1`)
- `Token`: Encrypted `olt.V1.<JWE compact serialization>` token (or base64 HMAC token when generated via `olt tokenize`)

**Notes:**

- **One row per rule per record**: up to 6 rows for each valid record (T1–T5 plus ML1)
- **Blank tokens**: If a record is invalid, tokens may be blank (logged in metadata)
- **Token length**: Varies by mode and payload size (encrypted `olt.V1` tokens are longer than normal `tokenize` or `tokenize --mode hash-only` outputs)

### Metadata Output

For `package` and `tokenize` CSV/Parquet output, metadata is JSON with the
`.metadata.json` suffix (for example, `output.metadata.json`). For ZIP output,
`package` embeds metadata in the archive. `encrypt` and `decrypt` do not emit
metadata:

```json
{
  "PythonVersion": "3.11.0",
  "Version": "2.1.0",
  "Platform": "Python",
  "TotalRows": 3,
  "TotalRowsWithInvalidAttributes": 1,
  "InvalidAttributesByType": {
    "FirstName": 1,
    "BirthDate": 0
  },
  "BlankTokensByRule": {
    "T1": 1,
    "T2": 1,
    "T3": 1,
    "T4": 1,
    "T5": 1,
    "ML1": 0
  }
}
```

See [Reference: Metadata Format](../reference/metadata-format.md) for detailed field documentation.

---

## Processing Modes

### Encryption Mode (Default)

Generates encrypted `olt.V1` match tokens using HMAC-SHA256 + JWE/AES-256-GCM.

```bash
olt package \
  -i data.csv -o tokens.csv \
  --exchange-config ./tuning.exchange.json
```

**Process:**

```
Token Signature → SHA-256 Hash → HMAC-SHA256(hash, key) → JWE (AES-256-GCM) → Prefix `olt.V1.`
```

**Requires:** Exchange config plus a matching private key that the CLI can auto-discover (or an explicit override)

Encrypted `olt.V1` tokens include randomized IVs, so ciphertext values are not deterministic across runs.

### Tokenize Mode (HMAC, No Encryption)

Generates HMAC-SHA256 tokens without transport encryption. Useful for token
matching scenarios where encryption overhead is unnecessary.

```bash
olt tokenize \
  -i data.csv -o tokens.csv \
  --exchange-config ./tuning.exchange.json
```

**Process:**

```
Token Signature → SHA-256 Hash → HMAC-SHA256(hash, key) → Base64 Encode
```

**Requires:** An exchange config plus a matching private key in default mode.
`--mode hash-only` and `--mode demo` do not require secrets; an exchange config
may still be supplied to configure optional rotation settings.

**Benefits:**

- Faster processing
- Smaller output (shorter tokens)
- Suitable for internal matching where raw data is already protected
- Cross-language compatibility guaranteed

ML1 is enabled by default for `package` and default `tokenize` and can add one
`ML1` row per valid record. Use `--disable-inferencing` to produce only T1–T5.

### Decryption Mode

Reverse previous encryption to inspect or verify token generation.

```bash
olt decrypt \
  -i encrypted-tokens.csv -o decrypted-tokens.csv \
  --exchange-config ./tuning.exchange.json
```

**Output:** HMAC-SHA256 hashed tokens (base64 encoded) **before** AES encryption—equivalent to `tokenize` output.

**Use cases:**

- Debugging attribute normalization issues
- Verifying token consistency across datasets
- Re-encrypting with different keys

---

## Custom Token Rules

To define custom token rules beyond T1–T5, see:

- [Reference: Token Registration](../reference/token-registration.md)
- [Spark or Databricks](../operations/spark-or-databricks.md) (notebook example)

---

## Cross-Language Compatibility

Open Link Token produces **identical tokens** for the same input and secrets across integrations.

**Verified for:**

- Attribute normalization
- Token generation rules
- Hashing (HMAC-SHA256)
- Encryption (AES-256)

**Test interoperability:**

```bash
cd tools/interoperability
python multi_language_interoperability_test.py
```

---

## Next Steps

- **Understand validation rules**: [Security](../security.md)
- **View metadata format**: [Reference: Metadata Format](../reference/metadata-format.md)
- **Define custom tokens**: [Reference](../reference/index.md)
- **Debug tokens**: [Running Open Link Token](../running-openlinktoken/index.md)
