---
layout: default
---

# Configuration & Tuning

Input formats, output modes, and customization options.

## Input File Format

OpenToken processes CSV and Parquet files. Both formats support the same attribute columns with flexible naming.

### Column Names & Aliases

Input columns are case-insensitive and support common aliases:

| Attribute                  | Accepted Column Names                                  | Required | Type   | Example                                       |
| -------------------------- | ------------------------------------------------------ | -------- | ------ | --------------------------------------------- |
| **Record ID**              | `RecordId`, `Id`                                       | Optional | String | `patient_123`, `uuid-abc...`                  |
| **First Name**             | `FirstName`, `GivenName`                               | Yes      | String | `John`                                        |
| **Last Name**              | `LastName`, `Surname`                                  | Yes      | String | `Doe`                                         |
| **Birth Date**             | `BirthDate`, `DateOfBirth`                             | Yes      | Date   | `1980-01-15`                                  |
| **Sex**                    | `Sex`, `Gender`                                        | Yes      | String | `Male`, `M`, `Female`, `F`                    |
| **Postal Code**            | `PostalCode`, `ZipCode`, `ZIP3`, `ZIP4`, `ZIP5`        | Yes      | String | `98004`, `K1A 1A1`                            |
| **Social Security Number** | `SocialSecurityNumber`, `NationalIdentificationNumber` | Yes      | String | `123-45-6789` (digits-only values normalized) |

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

# Read with OpenToken
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
| **All attributes valid**    | Record processed; 5 tokens generated (T1–T5)                       |

Records with invalid attributes are still output (with blank tokens for that rule), but flagged in metadata.

---

## Output File Format

OpenToken generates two output files: tokens and metadata.

### Tokens Output

CSV or Parquet file (same format as input, unless `-ot` specifies otherwise):

```csv
RecordId,RuleId,Token
ID001,T1,Gn7t1Zj16E5Qy+z9iINtczP6fRDYta6C0XFrQtpjnVQSEZ5pQXAzo02Aa9LS9oNMOog6Ssw9GZE6fvJrX2sQ/cThSkB6m91L
ID001,T2,pUxPgYL9+cMxkA+8928Pil+9W+dm9kISwHYPdkZS+I2nQ/bQ/8HyL3FOVf3NYPW5NKZZO1OZfsz7LfKYpTlaxyzMLqMF2Wk7
ID001,T3,rwjfwIo5OcJUItTx8KCoSZMtr7tVGSyXsWv/hhCWmD2pBO5JyfmujsosvwYbYeeQ4Vl1Z3eq0cTwzkvfzJVS/EKaRhtjMZz5
ID001,T4,9o7HIYZkhizczFzJL1HFyanlllzSa8hlgQWQ5gHp3Niuo2AvEGcUwtKZXChzHmAa8Jm3183XVoacbL/bFEJyOYYS4EQDppev
ID001,T5,QpBpGBqaMhagfcHGZhVavn23ko03jkyS9Vo4qe78E4sKw+Zq2CIw4MMWG8VXVwInnsFBVk6NSDUI79wECf5DchV5CXQ9AFqR
ID002,T1,...
```

**Columns:**
- `RecordId`: From input (or auto-generated UUID)
- `RuleId`: Token rule identifier (T1–T5)
- `Token`: Encrypted `ot.V1.<JWE compact serialization>` token (or base64 HMAC token if `--hash-only`)

**Notes:**
- **One row per rule per record**: 5 rows for each valid record
- **Blank tokens**: If a record is invalid, tokens may be blank (logged in metadata)
- **Token length**: Varies by mode and payload size (encrypted `ot.V1` tokens are longer than hash-only tokens)

### Metadata Output

Always JSON format, suffixed `.metadata.json` (e.g., `output.metadata.json`):

```json
{
  "JavaVersion": "21.0.0",
  "OpenTokenVersion": "1.0.0",
  "Platform": "Java",
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
    "T5": 1
  },
  "HashingSecretHash": "abc123def456...",
  "EncryptionSecretHash": "fed456abc123..."
}
```

See [Reference: Metadata Format](../reference/metadata-format.md) for detailed field documentation.

---

## Processing Modes

### Encryption Mode (Default)

Generates encrypted `ot.V1` match tokens using HMAC-SHA256 + JWE/AES-256-GCM.

```bash
java -jar opentoken-cli-*.jar \
  -i data.csv -t csv -o tokens.csv \
  -h "HashingKey" -e "EncryptionKey"
```

**Process:**
```
Token Signature → SHA-256 Hash → HMAC-SHA256(hash, key) → JWE (AES-256-GCM) → Prefix `ot.V1.`
```

**Requires:** Hashing secret (`-h`) and encryption key (`-e`)

Encrypted `ot.V1` tokens include randomized IVs, so ciphertext values are not deterministic across runs.

### Hash-Only Mode

Generates hashed tokens without encryption. Useful for token matching scenarios where encryption overhead is unnecessary.

```bash
java -jar opentoken-cli-*.jar \
  --hash-only \
  -i data.csv -t csv -o tokens.csv \
  -h "HashingKey"
```

**Process:**
```
Token Signature → SHA-256 Hash → HMAC-SHA256(hash, key) → Base64 Encode
```

**Requires:** Hashing secret only (`-h`)

**Benefits:**
- Faster processing
- Smaller output (shorter tokens)
- Suitable for internal matching where raw data is already protected
- Java/Python cross-language compatibility guaranteed

### Decryption Mode

Reverse previous encryption to inspect or verify token generation.

```bash
java -jar opentoken-cli-*.jar \
  -d \
  -i encrypted-tokens.csv -t csv -o decrypted-tokens.csv \
  -e "EncryptionKey"
```

**Output:** HMAC-SHA256 hashed tokens (base64 encoded) **before** AES encryption—equivalent to `--hash-only` output.

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

OpenToken Java and Python implementations produce **identical tokens** for the same input and secrets.

**Verified for:**
- Attribute normalization
- Token generation rules
- Hashing (HMAC-SHA256)
- Encryption (AES-256)

**Test interoperability:**
```bash
cd tools/interoperability
python java_python_interoperability_test.py
```

---

## Next Steps

- **Understand validation rules**: [Security](../security.md)
- **View metadata format**: [Reference: Metadata Format](../reference/metadata-format.md)
- **Define custom tokens**: [Reference](../reference/index.md)
- **Debug tokens**: [Running OpenToken](../running-opentoken/index.md)
