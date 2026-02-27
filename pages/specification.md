---
layout: default
---

# OpenToken Specification

## Overview

OpenToken is a privacy-preserving token generation system for deterministic person matching across datasets. This specification defines the scope, inputs, processing steps, and outputs of the token generation pipeline.

**Purpose:** Generate cryptographically secure tokens from person attributes such that:
- Identical inputs always produce identical deterministic matching values (hash-only or decrypted)
- Tokens reveal nothing about the underlying data (one-way)
- Matching can occur on different attribute combinations via 5 distinct token rules (T1–T5)

**Applicability:** This specification applies to both Java and Python implementations. Cross-language deterministic outputs (hash-only and decrypted values) must be byte-identical for the same normalized inputs and secrets.

---

## Scope and Goals

### In Scope

1. **Person attribute normalization**: Transformation of raw input data into canonical forms
2. **Token rule definitions**: Five rules (T1–T5) combining attributes in distinct ways
3. **Token generation pipeline**: Deterministic transformation of normalized attributes → final tokens
4. **Metadata tracking**: Processing statistics, system info, and secret hashes for audit
5. **Error handling**: Behavior when attributes fail validation
6. **Output formats**: CSV and Parquet serialization

### Out of Scope

- User authentication or access control
- Network transport or API specification (see implementation-specific documentation)
- Data backup, archival, or long-term storage strategy
- Performance tuning or optimization parameters (see [Configuration](config/configuration.md))
- Distributed/parallel processing details (handled by PySpark implementation separately)

---

## Input Expectations

### File Formats

**Supported input formats:**
- CSV (comma-separated values, with header row)
- Parquet (columnar binary format)

### Size and Processing Model

OpenToken is designed for **streaming-style** processing: it reads records, normalizes/validates, emits up to 5 tokens, and writes output without needing to hold the full dataset in memory.

**Practical constraints:**
- There is **no fixed maximum file size** imposed by OpenToken itself; limits are driven by your machine/cluster resources (CPU, memory, disk) and the underlying CSV/Parquet libraries.
- Output size is roughly **5× the number of input rows** (one row per rule per record) plus metadata.
- For Parquet, performance and memory usage depend on row group sizing and the reader implementation.

**Recommendations:**
- Prefer **Parquet** for large jobs (faster parsing, smaller I/O, better parallelism).
- Ensure disk space for outputs (tokens + `.metadata.json`).
- For very large datasets, use the **PySpark** integration to scale horizontally.

### Required Attributes

All of the following must be provided per record:

| Attribute      | Type   | Constraints                                  | Examples                                      | Normalization                                  |
| -------------- | ------ | -------------------------------------------- | --------------------------------------------- | ---------------------------------------------- |
| **FirstName**  | String | Non-empty after normalization                | "John", "José", "JoAnn"                       | Remove titles, suffixes, diacritics; uppercase |
| **LastName**   | String | Non-empty after normalization                | "Smith", "O'Brien", "García"                  | Remove suffixes, diacritics; uppercase         |
| **BirthDate**  | Date   | 1910-01-01 to today                          | "1980-01-15", "01/15/1980", "15.01.1980"      | ISO 8601 YYYY-MM-DD                            |
| **Sex**        | String | "Male" or "Female" (case-insensitive)        | "M", "F", "male", "FEMALE"                    | Uppercase; normalize M→MALE, F→FEMALE          |
| **PostalCode** | String | Valid US ZIP or Canadian postal code         | "98004", "K1A 1A1", "98004-1234"              | Remove dashes; pad ZIP to 5 digits             |
| **SSN**        | String | 9 numeric digits (US Social Security Number) | "123-45-6789" (digits-only inputs normalized) | Remove dashes                                  |

### Optional Attributes

- **RecordId**: Unique identifier per record (defaults to UUID if omitted)

### Validation Rules

Attributes are validated **after normalization**. See [Concepts: Normalization and Validation](concepts/normalization-and-validation.md) for detailed rules:

- **FirstName/LastName**: At least one alphabetic character after diacritic removal
- **BirthDate**: Valid date within allowed range
- **Sex**: Exactly "MALE" or "FEMALE" after normalization
- **PostalCode**: Valid US ZIP-5 or Canadian postal code format
- **SSN**: Area code ≠ 000/666/900–999; group ≠ 00; serial ≠ 0000; reject common placeholders

If any attribute fails validation, the record is marked invalid in metadata, and affected token rules produce blank tokens.

---

## Processing Steps

### 1. Input Parsing

- Read CSV or Parquet file with header
- Validate schema (all required columns present)
- Stream or batch records (implementation-dependent)

### 2. Attribute Normalization

Each attribute is normalized according to its type:

- **Names** (FirstName, LastName): Remove titles/suffixes, diacritics, extra whitespace; uppercase
- **BirthDate**: Parse input format (multiple formats supported) → ISO 8601 YYYY-MM-DD
- **Sex**: Parse variants (M/male/Male → MALE; F/female/Female → FEMALE)
- **PostalCode**: Remove dashes, zero-pad ZIP codes to 5 digits, uppercase Canadian postal codes
- **SSN**: Remove dashes, validate 9-digit format

**Details:** See [Concepts: Normalization and Validation](concepts/normalization-and-validation.md)

### 3. Attribute Validation

Normalized attributes are validated against business rules:

- Non-empty names
- Valid date ranges
- Valid postal code formats
- SSN validation (area/group/serial constraints)

Invalid records are flagged and tracked in metadata; blank tokens are generated for affected rules.

### 4. Token Rule Application

Apply each of the 5 token rules independently:

| Rule   | Attributes                                                  | Notes                                   |
| ------ | ----------------------------------------------------------- | --------------------------------------- |
| **T1** | U(LastName) \| U(FirstName[0]) \| U(Sex) \| BirthDate       | Standard match; higher recall           |
| **T2** | U(LastName) \| U(FirstName) \| BirthDate \| PostalCode[0:3] | Geographic variation; uses ZIP-3        |
| **T3** | U(LastName) \| U(FirstName) \| U(Sex) \| BirthDate          | Higher precision match; full name + sex |
| **T4** | SocialSecurityNumber \| U(Sex) \| BirthDate                 | Authoritative; uses SSN                 |
| **T5** | U(LastName) \| U(FirstName[0:3]) \| U(Sex)                  | Quick search; no birth date             |

(U = Uppercase, [0] = first char, [0:3] = first 3 chars)

**Details:** See [Concepts: Token Rules](concepts/token-rules.md)

### 5. Token Encryption / Hash Transformation

Each token rule signature is transformed through the cryptographic pipeline.

**Default mode (encrypted):**

```
Signature → SHA-256 → HMAC-SHA256 → JWE (AES-256-GCM) → Prefix `ot.V1.`
```

Encrypted `ot.V1` token strings are intentionally non-deterministic due to randomized IVs.

**Hash-only mode (optional):**

```
Signature → SHA-256 → HMAC-SHA256 → Base64
```

**Parameters required:**
- `hashing_secret`: String (8+ characters recommended) used for HMAC
- `encryption_key`: String exactly 32 characters long (or byte array 32 bytes) used for AES-256 encryption

**Details:** See [Security: Cryptographic Building Blocks](security.md#cryptographic-building-blocks)

### 6. Metadata Generation

During processing, OpenToken tracks:

- **Counts**: Total rows, invalid attributes per type, blank tokens per rule
- **System Info**: Platform (Java/Python), language version, library version
- **Secrets**: SHA-256 hashes of hashing secret and encryption key (not the secrets themselves)
- **Timestamps**: Processing start, completion, all in UTC
- **Paths**: Input/output file paths

Metadata is written to `.metadata.json` alongside output files.

**Details:** See [Reference: Metadata Format](reference/metadata-format.md)

---

## Outputs

### Token Output (CSV)

**Schema:**
```
RecordId,RuleId,Token
```

**Columns:**
- `RecordId`: From input (or auto-generated if omitted)
- `RuleId`: T1, T2, T3, T4, or T5
- `Token`: Encrypted `ot.V1.<JWE>` token in encrypted mode, or base64 HMAC token in hash-only/decrypted mode (or empty string if validation failed)

**Rows per input record:** 5 (one per rule); may be fewer if errors occur

**Example:**
```csv
RecordId,RuleId,Token
ID001,T1,aB7c9Dz1e4...
ID001,T2,fG3h5kL2m9...
ID001,T3,nP6q8sT1u0...
ID001,T4,vW9xY2zAbC...
ID001,T5,DeF3gHi6jK...
```

### Token Output (Parquet)

Same schema as CSV but with native Parquet types:

```
RecordId (string)
RuleId (string)
Token (string)
```

Parquet format includes compression and is suitable for large datasets.

### Metadata Output

**Filename:** `<output_basename>.metadata.json`

**Contents:**
- Processing statistics (record counts, invalid attributes, blank tokens)
- System information (platform, versions, timestamps)
- Secret hashes (SHA-256 of hashing secret and encryption key)
- File paths (input, output, metadata)

**Example:**
```json
{
  "Platform": "Java",
  "JavaVersion": "21.0.0",
  "OpenTokenVersion": "1.7.0",
  "TotalRows": 100,
  "TotalRowsWithInvalidAttributes": 3,
  "InvalidAttributesByType": {
    "BirthDate": 2,
    "PostalCode": 1
  },
  "BlankTokensByRule": {
    "T1": 2,
    "T2": 1
  },
  "HashingSecretHash": "abc123...",
  "EncryptionSecretHash": "def456..."
}
```

**Details:** See [Reference: Metadata Format](reference/metadata-format.md)

---

## Versioning Notes

### Current Version

**OpenToken Specification v1.0** (as of 2024)

- 5 token rules (T1–T5) finalized
- Attribute set: FirstName, LastName, BirthDate, Sex, PostalCode, SSN
- Normalization rules documented
- Cryptographic pipeline: SHA-256 → HMAC-SHA256 → AES-256-GCM

### Compatibility

- **Java**: JDK 21+
- **Python**: 3.10+
- **Cross-language parity**: Java and Python implementations MUST produce byte-identical deterministic values (hash-only/decrypted) for the same normalized inputs

### Future Considerations

This section is **non-normative** (informational) and describes likely evolution areas:

- Extension mechanism for new token rules (T6+) with explicit cross-language parity requirements
- Support for additional attribute types (e.g., middle name, phone, email) behind versioned schemas
- Metadata schema versioning for forward compatibility
- Formal specification versioning and migration guidance
- Published performance guidance (methodology, baselines by environment)

### Breaking Changes

Any changes to:
- Normalization rules
- Token rule definitions
- Cryptographic algorithms
- Metadata schema

...will require a major version bump and clear migration path.

---

## Cross-References

For deeper information, see:

- **Token Rules**: [Concepts: Token Rules](concepts/token-rules.md)
- **Normalization**: [Concepts: Normalization and Validation](concepts/normalization-and-validation.md)
- **Cryptography & Security**: [Security](security.md)
- **Metadata Fields**: [Reference: Metadata Format](reference/metadata-format.md)
- **Configuration**: [Configuration](config/configuration.md)
- **CLI Usage**: [Running OpenToken](running-opentoken/index.md)
- **Operations**: [Running Batch Jobs](operations/running-batch-jobs.md)

---

## Document History

| Date       | Version | Changes                             |
| ---------- | ------- | ----------------------------------- |
| 2024-01-15 | 1.0     | Initial specification               |
| Planned    | 1.1     | Formalize version field in metadata |
