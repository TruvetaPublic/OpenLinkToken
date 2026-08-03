---
layout: default
---

# Metadata Format

Complete reference for the Open Link Token metadata JSON file structure, fields, and usage for audit and verification.

## Overview

The CLI `package` and `tokenize` commands generate metadata. For CSV and
Parquet output, the metadata is a `<output>.metadata.json` sidecar; for ZIP
output, it is embedded in the archive. The `encrypt` and `decrypt` commands do
not generate metadata. Metadata files provide:

- **Processing statistics**: Counts of total records, invalid attributes, and blank tokens
- **System information**: Platform (Java/Python), runtime version, library version
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

For `package -o output.zip`, the archive contains the token output and
`output.metadata.json`.

### JSON Schema

```json
{
  "Platform": "string",
  "PythonVersion": "string (optional, Python only)",
  "Version": "string",
  "TotalRows": integer,
  "TotalRowsWithInvalidAttributes": integer,
  "InvalidAttributesByType": {
    "AttributeName": integer,
    ...
  },
  "BlankTokensByRule": {
    "RuleId": integer,
    ...
  }
}
```

---

## Field Descriptions

### Platform Information

| Field           | Type   | Description                          | Example    |
| --------------- | ------ | ------------------------------------ | ---------- |
| `Platform`      | String | Processing platform/language         | `"Python"` |
| `PythonVersion` | String | Python runtime version (Python only) | `"3.11.5"` |
| `Version`       | String | Open Link Token library version      | `"2.1.0"`  |

**Notes:**

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

- Keys: Rule IDs (`T1`–`T5` and, when ML1 inferencing is enabled, `ML1`)
- Values: Count of blank tokens for that rule
- Blank tokens occur when a rule requires an invalid attribute
- Example: Invalid `BirthDate` causes blank tokens for T1, T2, T3, T4 (but not T5)

## Example Metadata

### Full Example (`package` Command)

```json
{
  "Platform": "Python",
  "PythonVersion": "3.11.5",
  "Version": "2.1.0",
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
    "T5": 7,
    "ML1": 4
  }
}
```

### `tokenize` Subcommand Example

```json
{
  "Platform": "Python",
  "PythonVersion": "3.11.5",
  "Version": "2.1.0",
  "TotalRows": 50,
  "TotalRowsWithInvalidAttributes": 2,
  "InvalidAttributesByType": {
    "PostalCode": 2
  },
  "BlankTokensByRule": {
    "T1": 0,
    "T2": 2,
    "T3": 0,
    "T4": 0,
    "T5": 0,
    "ML1": 2
  }
}
```

The `ML1` entry appears when the optional AI module is installed and ML1
inferencing is enabled. Use `--disable-inferencing` to omit ML1 output and its
corresponding metadata entry.

---

## Interpreting Metadata

### Valid vs Invalid Records

Calculate valid records:

```
Valid Records = TotalRows - TotalRowsWithInvalidAttributes
```

`TotalRowsWithInvalidAttributes` counts distinct records. A single record with
multiple invalid attributes contributes once to this field.

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

- 100 records processed
- 5 records had one or more invalid attributes
- 95 records were fully valid
- Total invalid attribute instances: 2 + 3 + 1 = 6
- At least one record had multiple invalid attributes

### Invalid Attribute Counts

Count totals:

```
Sum of InvalidAttributesByType values ≥ TotalRowsWithInvalidAttributes
```

The sum can be greater because a single record can have multiple invalid
attributes.

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

---

## Usage Notes

### Audit Trail

Metadata provides an audit record of:

- What was processed (record counts and attribute-level statistics)
- How it was processed (platform, version)
- What errors occurred (invalid attributes)

Store metadata files alongside token outputs for compliance and troubleshooting.

### Retention

Consider retaining metadata longer than token files:

- Metadata contains no person data
- Provides audit trail for compliance
- Useful for troubleshooting historic runs

### Security

Metadata files exclude raw person data and secret material:

- ✓ Safe to log, store, and share within your normal operational controls
- ✓ Useful for troubleshooting and audit without exposing runtime secrets
- ✗ Metadata alone cannot generate or decrypt tokens

---

## Next Steps

- **View token rules**: [Concepts: Token Rules](../concepts/token-rules.md)
- **Understand validation**: [Security](../security.md)
- **See full examples**: [Quickstarts](../quickstarts/index.md)
