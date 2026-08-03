---
layout: default
---

# Overview

## What is Open Link Token?

Open Link Token is a privacy-preserving tokenization and matching library for secure person linkage using PII-derived attributes. It generates cryptographically secure matching tokens from person attributes, enabling matching across datasets without directly comparing names, birthdates, SSNs, and other sensitive identifiers.

Both Java and Python implementations produce **byte-identical deterministic tokenized outputs** (and byte-identical decrypted token payloads) for the same normalized input, enabling flexible deployment and cross-language workflows.

## The Problem

Organizations often need to match people across datasets—finding the same person across systems and time. Direct comparison of names and birthdates raises privacy concerns and is error-prone due to typos and data quality variations. **Open Link Token solves this by generating deterministic cryptographic fingerprints from person data, with optional encrypted token wrapping for secure exchange.**

## The Solution

Instead of storing or comparing raw person attributes:

```
John Doe | 1975-03-15 | 98004 → [STORED OR COMPARED]
```

Open Link Token generates secure tokens derived from those attributes:

```
John Doe | 1975-03-15 | 98004 → SHA-256 HASH → HMAC-SHA256 → AES-256/JWE (olt.V1) → Token
```

Matching is performed on deterministic tokenized values (or decrypted token payloads), not on raw PII.

## How It Works

1. **Input**: Person records with attributes (name, birthdate, SSN, postal code, sex)
2. **Validation & Normalization**: Attributes are validated and normalized (uppercase, diacritic removal, supported Latin Extended transliteration, title stripping)
3. **Token Generation**: Five deterministic token rules (T1–T5) combine different attributes; ML1 can add one model-based rule by default
4. **Transformation**: Deterministic HMAC-SHA256 hashes are produced; encrypted mode wraps them as `olt.V1` JWE match tokens
5. **Output**: Encrypted `olt.V1` tokens (default), deterministic tokenized values, or `tokenize --mode hash-only` SHA-256 output. `package` and `tokenize` also write metadata.

## Key Concepts

### Token Generation Rules

Open Link Token uses **5 distinct deterministic token rules (T1–T5)** that
define which attributes combine to form each token. When the optional AI module
is available, `package` and default `tokenize` also emit one `ML1` row for
records with valid ML1 inputs:

| Rule | Definition                                      | Use Case                 |
| ---- | ----------------------------------------------- | ------------------------ |
| T1   | Last name + first initial + sex + birthdate     | Standard matching        |
| T2   | Last name + full first name + birthdate + ZIP-3 | Data with varied names   |
| T3   | Last name + full first name + sex + birthdate   | Higher precision         |
| T4   | SSN + sex + birthdate                           | Authoritative identifier |
| T5   | Last name + first 3 letters + sex               | Quick search             |

ML1 uses an ONNX model over PostalCode, BirthDate, FirstName, LastName, and
Sex. Use `--disable-inferencing` to emit only T1–T5.

### Validation & Normalization

Before tokens are generated, attributes are validated against practical, PII-focused rules:

- **FirstName/LastName**: No placeholders, proper length, diacritics removed, supported Latin Extended letters transliterated to ASCII
- **BirthDate**: 1910–today, valid format (YYYY-MM-DD)
- **SSN**: Valid US social security number (area, group, serial checks)
- **PostalCode**: Valid US ZIP or Canadian postal code
- **Sex**: Male or Female

Invalid records are tracked and reported in metadata.

### Encryption Process

The token is transformed through a secure pipeline:

```
Token Signature → SHA-256 Hash → HMAC-SHA256 → JWE (AES-256-GCM) → Prefix `olt.V1.`
```

Or using the `tokenize` subcommand (no encryption):

```
Token Signature → SHA-256 Hash → HMAC-SHA256 → Base64-encoded HMAC value
```

## Data Flow

```
Input CSV/Parquet
       ↓
Validate & Normalize
       ↓
Generate Token Signatures (T1-T5 plus ML1 when enabled)
       ↓
Hash & Encrypt
       ↓
Output CSV/Parquet (plus metadata for `package`/`tokenize`)
```

## Multi-Language Parity

Open Link Token is implemented in **Java and Python**. Both produce **byte-identical deterministic values** (tokenized outputs, `--mode hash-only` outputs where supported, and decrypted token payloads) for the same normalized input and secrets. This enables:

- Flexible deployment (choose Java or Python)
- Cross-language processing (encrypt in one language, decrypt in another)
- Distributed processing with PySpark

## Security Properties

- **No Reversal**: Tokens cannot be decrypted back to original data without the encryption key
- **Deterministic matching basis**: Same normalized input produces the same tokenized/decrypted value
- **Randomized encrypted representation**: Encrypted `olt.V1` tokens use random IVs, so ciphertext differs across runs
- **Privacy-Focused**: Designed for regulated environments where PII must be protected
- **Validation**: Rejects invalid or placeholder values before processing

## Who Uses Open Link Token?

- **Data Engineers**: Building record linkage pipelines
- **Privacy/Infra Engineers**: Securing sensitive data in regulated systems
- **Data/Platform Teams**: Linking records across datasets while preserving privacy
- **Researchers**: Linking datasets for cohort studies without exposing raw identifiers

## Next Steps

**→ [Quickstarts](../quickstarts/index.md)** – Try Open Link Token in 5 minutes. Choose CLI (Docker), Python, or Java.

Once you've run through a quickstart:

- [Token Rules](../concepts/token-rules.md) – Deep dive into T1–T5 and matching strategies
- [Security](../security.md) – Understand validation rules and cryptography
