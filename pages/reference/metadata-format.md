---
layout: default
---

# Metadata Format

Complete reference for the OpenToken metadata JSON file structure, fields, and usage for audit and verification.

## Overview

OpenToken generates a metadata file alongside every token output file. Metadata files provide:

- **Processing statistics**: Counts of total records, invalid attributes, and blank tokens
- **System information**: Platform (Java/Python), runtime version, library version
- **Secure hashes**: SHA-256 hashes of secrets for verification (not the secrets themselves)
- **Audit trail**: What was processed and how (platform, version, and validation statistics)

Metadata files:
- Always use JSON format with `.metadata.json` extension
- Are automatically generated (e.g., `output.csv` → `output.metadata.json`)
- Contain no raw person data or actual secrets

---

## Metadata Structure

### File Format

```
Filename: <output-file-name>.metadata.json
Format: JSON (UTF-8)
Extension: .metadata.json
```

**Example filenames:**
- `output.csv` → `output.metadata.json`
- `tokens.parquet` → `tokens.metadata.json`
- `/data/results.csv` → `/data/results.metadata.json`

### JSON Schema

```json
{
  "Platform": "string",
  "JavaVersion": "string (optional, Java only)",
  "PythonVersion": "string (optional, Python only)",
  "OpenTokenVersion": "string",
  "TotalRows": integer,
  "TotalRowsWithInvalidAttributes": integer,
  "InvalidAttributesByType": {
    "AttributeName": integer,
    ...
  },
  "BlankTokensByRule": {
    "RuleId": integer,
    ...
  },
  "HashingSecretHash": "string (hex)",
  "EncryptionSecretHash": "string (hex, optional)"
}
```

---

## Field Descriptions

### Platform Information

| Field              | Type   | Description                          | Example                |
| ------------------ | ------ | ------------------------------------ | ---------------------- |
| `Platform`         | String | Processing platform/language         | `"Java"` or `"Python"` |
| `JavaVersion`      | String | Java runtime version (Java only)     | `"21.0.0"`             |
| `PythonVersion`    | String | Python runtime version (Python only) | `"3.11.5"`             |
| `OpenTokenVersion` | String | OpenToken library version            | `"1.12.2"`             |

**Notes:**
- Only `JavaVersion` OR `PythonVersion` appears (not both)
- Platform value determines which version field is present

### Processing Statistics

| Field                            | Type    | Description                               | Example                            |
| -------------------------------- | ------- | ----------------------------------------- | ---------------------------------- |
| `TotalRows`                      | Integer | Total input records processed             | `101`                              |
| `TotalRowsWithInvalidAttributes` | Integer | Records with ≥1 invalid attribute         | `9`                                |
| `InvalidAttributesByType`        | Object  | Count of invalid values by attribute name | `{"FirstName": 1, "BirthDate": 3}` |
| `BlankTokensByRule`              | Object  | Count of blank tokens by rule ID          | `{"T1": 5, "T2": 12}`              |

**InvalidAttributesByType:**
- Keys: Attribute names (e.g., `FirstName`, `BirthDate`, `SocialSecurityNumber`)
- Values: Count of invalid occurrences across all records
- A single record with 2 invalid attributes contributes 2 to the sum
- Sum of counts ≥ `TotalRowsWithInvalidAttributes`

**BlankTokensByRule:**
- Keys: Rule IDs (`T1`, `T2`, `T3`, `T4`, `T5`)
- Values: Count of blank tokens for that rule
- Blank tokens occur when a rule requires an invalid attribute
- Example: Invalid `BirthDate` causes blank tokens for T1, T2, T3, T4 (but not T5)

### Secret Hashes

| Field                  | Type   | Description                                    | Example                                 |
| ---------------------- | ------ | ---------------------------------------------- | --------------------------------------- |
| `HashingSecretHash`    | String | SHA-256 hash of hashing secret (hex)           | `"e0b4e60b6a9f7ea3b13c0d6a6e1b8c5d..."` |
| `EncryptionSecretHash` | String | SHA-256 hash of encryption key (hex, optional) | `"a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6..."` |

**Security:**
- Hashes are **not reversible** (SHA-256 is one-way)
- Used for verification: calculate hash of your secret and compare to metadata
- `EncryptionSecretHash` omitted in `--hash-only` mode (no encryption used)

---

## Example Metadata

### Full Example (Encryption Mode)

```json
{
  "Platform": "Java",
  "JavaVersion": "21.0.0",
  "OpenTokenVersion": "2.0.0-alpha",
  "TotalRows": 101,
  "TotalRowsWithInvalidAttributes": 9,
  "InvalidAttributesByType": {
    "SocialSecurityNumber": 2,
    "FirstName": 1,
    "PostalCode": 1,
    "LastName": 2,
    "BirthDate": 3
  },
  "BlankTokensByRule": {
    "T1": 5,
    "T2": 12,
    "T3": 3,
    "T4": 8,
    "T5": 7
  },
  "HashingSecretHash": "e0b4e60b6a9f7ea3b13c0d6a6e1b8c5d4e3f2a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0",
  "EncryptionSecretHash": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8"
}
```

### Hash-Only Mode Example

```json
{
  "Platform": "Python",
  "PythonVersion": "3.11.5",
  "OpenTokenVersion": "2.0.0-alpha",
  "TotalRows": 50,
  "TotalRowsWithInvalidAttributes": 2,
  "InvalidAttributesByType": {
    "PostalCode": 2
  },
  "BlankTokensByRule": {
    "T2": 2
  },
  "HashingSecretHash": "abc123def456789abc123def456789abc123def456789abc123def456789abc123"
}
```

**Note:** No `EncryptionSecretHash` because `--hash-only` mode doesn't use encryption.

---

## Interpreting Metadata

### Valid vs Invalid Records

Calculate valid records:
```
Valid Records = TotalRows - TotalRowsWithInvalidAttributes
```

**Example:**
```json
{
  "TotalRows": 100,
  "TotalRowsWithInvalidAttributes": 5
}
```
- 100 records processed
- 5 records had errors
- 95 records were fully valid

### Invalid Attribute Counts

Count totals:
```
Sum of InvalidAttributesByType values ≥ TotalRowsWithInvalidAttributes
```

**Why ≥?** A single record can have multiple invalid attributes.

**Example:**
```json
{
  "TotalRows": 100,
  "TotalRowsWithInvalidAttributes": 5,
  "InvalidAttributesByType": {
    "FirstName": 2,
    "PostalCode": 3,
    "BirthDate": 1
  }
}
```
- Total invalid attribute instances: 2 + 3 + 1 = 6
- Records with errors: 5
- At least one record had 2+ invalid attributes

### Blank Token Analysis

Blank tokens occur when a rule requires an invalid attribute.

**Token rule dependencies:**
- **T1**: LastName, FirstName, Sex, BirthDate
- **T2**: LastName, FirstName, BirthDate, PostalCode
- **T3**: LastName, FirstName, Sex, BirthDate
- **T4**: SocialSecurityNumber, Sex, BirthDate
- **T5**: LastName, FirstName, Sex

**Example:**
```json
{
  "InvalidAttributesByType": {
    "BirthDate": 3
  },
  "BlankTokensByRule": {
    "T1": 3,
    "T2": 3,
    "T3": 3,
    "T4": 3,
    "T5": 0
  }
}
```
- 3 records had invalid BirthDate
- T1–T4 all use BirthDate → 3 blank tokens each
- T5 doesn't use BirthDate → 0 blank tokens

---

## Hash Verification

### Purpose

Verify that the secrets used for token generation match expected values without exposing the secrets themselves.

### Verification Process

1. **Calculate hash of your secret**:
   ```bash
   python tools/hash_calculator.py --hashing-secret "HashingKey"
   ```

2. **Compare to metadata**:
   ```bash
   cat output.metadata.json | grep HashingSecretHash
   ```

3. **Match = correct secret used**

### Hash Calculation

The hash is computed as:
```
SHA-256(secret) → hex-encoded string (64 hex characters)
```

**Python implementation:**
```python
import hashlib

def calculate_hash(secret: str) -> str:
    return hashlib.sha256(secret.encode('utf-8')).hexdigest()

hashing_hash = calculate_hash("HashingKey")
encryption_hash = calculate_hash("Secret-Encryption-Key-Goes-Here.")
```

**Java implementation:**
```java
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;

public static String calculateHash(String secret) throws Exception {
    MessageDigest digest = MessageDigest.getInstance("SHA-256");
    byte[] hash = digest.digest(secret.getBytes(StandardCharsets.UTF_8));
    return bytesToHex(hash);
}

private static String bytesToHex(byte[] bytes) {
    StringBuilder result = new StringBuilder();
    for (byte b : bytes) {
        result.append(String.format("%02x", b));
    }
    return result.toString();
}
```

### Using the Hash Calculator Tool

The `tools/hash_calculator.py` script provides command-line hash calculation:

```bash
# Calculate both hashes
python tools/hash_calculator.py \
  --hashing-secret "HashingKey" \
  --encryption-key "Secret-Encryption-Key-Goes-Here."

# Output:
# HashingSecretHash: e0b4e60b6a9f7ea3b13c0d6a6e1b8c5d...
# EncryptionSecretHash: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6...
```

---

## Usage Notes

### Audit Trail

Metadata provides an audit record of:
- What was processed (record counts and attribute-level statistics)
- When it was processed (inferred from surrounding system logs or job metadata)
- How it was processed (platform, version)
- What secrets were used (via hashes)
- What errors occurred (invalid attributes)

Store metadata files alongside token outputs for compliance and troubleshooting.

### Cross-Language Consistency

Both Java and Python implementations produce identical metadata structure. Only differences:
- `JavaVersion` vs `PythonVersion` field name
- Timestamp format may vary slightly (both ISO 8601 compliant)

### Retention

Consider retaining metadata longer than token files:
- Metadata contains no person data
- Provides audit trail for compliance
- Useful for troubleshooting historic runs

### Security

Metadata files contain SHA-256 hashes of secrets:
- ✓ Safe to log, store, and share (no secrets exposed)
- ✓ Enables verification without revealing secrets
- ✗ Cannot reverse hashes to recover secrets
- ✗ Attacker with metadata alone cannot generate tokens

---

## Next Steps

- **View token rules**: [Concepts: Token Rules](../concepts/token-rules.md)
- **Understand validation**: [Security](../security.md)
- **Use hash calculator**: `tools/hash_calculator.py`
- **See full examples**: [Quickstarts](../quickstarts/index.md)
