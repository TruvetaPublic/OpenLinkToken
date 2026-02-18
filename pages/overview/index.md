---
layout: default
---

# Overview

## What is OpenToken?

OpenToken is a privacy-preserving tokenization and matching library for secure person linkage using PII-derived attributes. It generates cryptographically secure matching tokens from person attributes, enabling matching across datasets without directly comparing names, birthdates, SSNs, and other sensitive identifiers.

Both Java and Python implementations produce **byte-identical tokens** for the same normalized input, enabling flexible deployment and cross-language workflows.

## The Problem

Organizations often need to match people across datasets—finding the same person across systems and time. Direct comparison of names and birthdates raises privacy concerns and is error-prone due to typos and data quality variations. **OpenToken solves this by generating deterministic cryptographic tokens from person data.**

## The Solution

Instead of storing or comparing raw person attributes:

```
John Doe | 1975-03-15 | 98004 → [STORED OR COMPARED]
```

OpenToken generates secure tokens derived from those attributes:

```
John Doe | 1975-03-15 | 98004 → SHA-256 HASH → HMAC-SHA256 → AES-256 ENCRYPT → Token
```

Matching is done by comparing the encrypted tokens, not the original data.

## How It Works

1. **Input**: Person records with attributes (name, birthdate, SSN, postal code, sex)
2. **Validation & Normalization**: Attributes are validated and normalized (uppercase, diacritic removal, title stripping)
3. **Token Generation**: Multiple token rules (T1–T5) combine different attributes
4. **Encryption**: Tokens are hashed and encrypted using HMAC-SHA256 and AES-256
5. **Output**: Token signatures for matching and metadata

## Key Concepts

### Token Generation Rules

OpenToken uses **5 distinct token rules (T1–T5)** that define which attributes combine to form each token. Each rule targets different matching scenarios:

| Rule | Definition                                      | Use Case                 |
| ---- | ----------------------------------------------- | ------------------------ |
| T1   | Last name + first initial + sex + birthdate     | Standard matching        |
| T2   | Last name + full first name + birthdate + ZIP-3 | Data with varied names   |
| T3   | Last name + full first name + sex + birthdate   | Higher precision         |
| T4   | SSN + sex + birthdate                           | Authoritative identifier |
| T5   | Last name + first 3 letters + sex               | Quick search             |

### Validation & Normalization

Before tokens are generated, attributes are validated against practical, PII-focused rules:

- **FirstName/LastName**: No placeholders, proper length, diacritics normalized
- **BirthDate**: 1910–today, valid format (YYYY-MM-DD)
- **SSN**: Valid US social security number (area, group, serial checks)
- **PostalCode**: Valid US ZIP or Canadian postal code
- **Sex**: Male or Female

Invalid records are tracked and reported in metadata.

### Encryption Process

The token is transformed through a secure pipeline:

```
Token Signature → SHA-256 Hash → HMAC-SHA256 → AES-256 Encrypt → Base64 Encode
```

Or using the `tokenize` subcommand (no encryption):

```
Token Signature → SHA-256 Hash → HMAC-SHA256 → Base64 Encode
```

## Data Flow

```
Input CSV/Parquet
       ↓
Validate & Normalize
       ↓
Generate Token Signatures (T1-T5)
       ↓
Hash & Encrypt
       ↓
Output CSV/Parquet + Metadata
```

## Multi-Language Parity

OpenToken is implemented in **Java and Python**. Both produce **byte-identical tokens** for the same normalized input using the same hashing and encryption keys. This enables:

- Flexible deployment (choose Java or Python)
- Cross-language processing (encrypt in one language, decrypt in another)
- Distributed processing with PySpark

## Security Properties

- **No Reversal**: Tokens cannot be decrypted back to original data without the encryption key
- **Deterministic**: Same input always produces the same token (enables matching)
- **Privacy-Focused**: Designed for regulated environments where PII must be protected
- **Validation**: Rejects invalid or placeholder values before processing

## Who Uses OpenToken?

- **Data Engineers**: Building person matching pipelines
- **Privacy/Infra Engineers**: Securing sensitive data in regulated systems
- **Data/Platform Teams**: Linking records across datasets while preserving privacy
- **Researchers**: Linking datasets for cohort studies without exposing raw identifiers

## Next Steps

**→ [Quickstarts](../quickstarts/index.md)** – Try OpenToken in 5 minutes. Choose CLI (Docker), Python, or Java.

Once you've run through a quickstart:

- [Token Rules](../concepts/token-rules.md) – Deep dive into T1–T5 and matching strategies
- [Security](../security.md) – Understand validation rules and cryptography
