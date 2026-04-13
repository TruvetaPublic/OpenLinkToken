---
layout: default
---

# Metadata and Audit

Overview of the metadata produced alongside tokens and how to use it for auditing and verification.

## Overview

Every OpenLinkToken run generates a metadata file (`.metadata.json`) alongside the token output. This metadata provides:

- Processing statistics (records processed, validation failures, blank tokens)
- System information (platform and version)
- Secure secret verification (SHA-256 hashes, not actual secrets)
- Audit trail (platform, library version, and validation statistics)

## Key Concepts

### Processing Statistics

Metadata tracks:

- **Total records processed** (`TotalRows`)
- **Records with errors** (`TotalRowsWithInvalidAttributes`)
- **Invalid attributes by type** (`InvalidAttributesByType`)
- **Blank tokens by rule** (`BlankTokensByRule`)

**Why this matters:**

- Understand data quality issues
- Track which attributes fail validation most often
- Identify patterns in invalid data

### Secret Verification

Metadata includes **SHA-256 hashes of secrets**:

- `HashingSecretHash`: Hash of the hashing secret
- `EncryptionSecretHash`: Hash of the encryption key (if used)

**Purpose:**

- Verify correct secrets were used without exposing them
- Audit trail for compliance
- Detect configuration errors (mismatched secrets)

Use `tools/hash_calculator.py` to verify:

```bash
python tools/hash_calculator.py \
  --hashing-secret "YourSecret" \
  --encryption-key "YourKey"
```

### Audit Trail

Metadata provides:

- What platform and version (`Platform`, `OpenLinkTokenVersion`, and `JavaVersion`/`PythonVersion`)
- What data quality outcomes (record counts and attribute-level statistics)

**Use cases:**

- Compliance audits (who/when/where)
- Troubleshooting historic runs
- Version tracking for reproducibility

## Complete Reference

For full field descriptions, JSON schema, examples, and hash verification details:

→ **See [Reference: Metadata Format](../reference/metadata-format.md)**

## Next Steps

- **View metadata structure**: [Reference: Metadata Format](../reference/metadata-format.md)
- **Understand validation rules**: [Normalization & Validation](normalization-and-validation.md)
- **Use hash calculator**: [tools/hash_calculator.py](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/tools/hash_calculator.py)
