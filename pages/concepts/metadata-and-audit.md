---
layout: default
---

# Metadata and Audit

Overview of the metadata produced alongside tokens and how to use it for auditing and verification.

## Overview

The CLI `package` and `tokenize` commands generate metadata. For CSV and
Parquet output, metadata is written as a `<output>.metadata.json` sidecar; for
ZIP output, it is embedded in the archive. `encrypt` and `decrypt` do not
generate metadata. The metadata provides:

- Processing statistics (records processed, validation failures, blank tokens)
- System information (platform and version)
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

### Runtime Context

Metadata captures the processing environment alongside the row-level counters:

- `Platform`, `Version`, and `JavaVersion`/`PythonVersion` identify the runtime
- Processing statistics show how the run behaved without exposing secret material
- `BlankTokensByRule` can include `T1`–`T5` and, when ML1 is enabled, `ML1`

**Purpose:**

- Audit trail for compliance
- Detect data-quality and processing errors

### Audit Trail

Metadata provides:

- What platform and version (`Platform`, `Version`, and `JavaVersion`/`PythonVersion`)
- What data quality outcomes (record counts and attribute-level statistics)

**Use cases:**

- Compliance audits (who/when/where)
- Troubleshooting historic runs
- Version tracking for reproducibility

## Complete Reference

For full field descriptions, JSON schema, examples, and interpretation guidance:

→ **See [Reference: Metadata Format](../reference/metadata-format.md)**

## Next Steps

- **View metadata structure**: [Reference: Metadata Format](../reference/metadata-format.md)
- **Understand validation rules**: [Normalization & Validation](normalization-and-validation.md)
