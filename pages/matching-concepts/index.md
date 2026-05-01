---
layout: default
---

# Matching Concepts

Understand how Open Link Token tokens work for record linkage and the strategies behind the 5 token rules.

## Token Generation Rules

Open Link Token generates **5 distinct tokens (T1–T5)** per person, each combining different attributes to target different matching scenarios.

### Rule Definitions

| Rule   | Definition                       | Attributes Used                                              | Best For                                    |
| ------ | -------------------------------- | ------------------------------------------------------------ | ------------------------------------------- |
| **T1** | `LAST\|FIRST[0]\|SEX\|BIRTHDATE` | Last name + first initial + sex + birthdate                  | Standard matching; higher recall            |
| **T2** | `LAST\|FIRST\|BIRTHDATE\|ZIP3`   | Last name + full first name + birthdate + first 3 ZIP digits | Flexible name matching with geographic data |
| **T3** | `LAST\|FIRST\|SEX\|BIRTHDATE`    | Last name + full first name + sex + birthdate                | Higher precision; stricter matching         |
| **T4** | `SSN\|SEX\|BIRTHDATE`            | Full SSN + sex + birthdate                                   | Authoritative matching; highest confidence  |
| **T5** | `LAST\|FIRST[0:3]\|SEX`          | Last name + first 3 characters + sex                         | Quick search; lower entropy                 |

**Legend**: `U(X)` = uppercase(X), `[0]` = first character, `[0:3]` = first 3 characters

### Example

Given a person:

```
FirstName: John
LastName: Doe
Sex: Male
BirthDate: 2000-01-01
PostalCode: 98004
SSN: 123-45-6789
```

Token signatures are:

| Rule | Token Signature                |
| ---- | ------------------------------ |
| T1   | `DOE\|J\|MALE\|2000-01-01`     |
| T2   | `DOE\|JOHN\|2000-01-01\|980`   |
| T3   | `DOE\|JOHN\|MALE\|2000-01-01`  |
| T4   | `SSN_DIGITS\|MALE\|2000-01-01` |
| T5   | `DOE\|JOH\|MALE`               |

These signatures are then hashed and encrypted to produce the final tokens.

`SSN_DIGITS` represents the digits-only normalization of the SSN input (123-45-6789 → digits only).

## Why Multiple Rules?

Different attributes have different error rates and availability:

- **Name changes**: Nicknames, middle names, hyphenated surnames
- **SSN unavailability**: Not always available in all datasets
- **Postal code drift**: People move; ZIP-3 is more stable than full code
- **Sex variation**: May be recorded differently across sources

Using **5 rules increases match confidence** by capturing different attribute combinations:

- **Match on T4 (or T4 + any other rule)**: Very high confidence (SSN + Sex + BirthDate)
- **Match on T2 + T3**: High confidence (full name + BirthDate plus ZIP-3 and/or Sex)
- **Match on T5 alone**: Medium confidence (Last name + first 3 letters + Sex)

## How Matching Works

Suppose you have two datasets and want to find matching persons:

### Dataset A

```
RecordId: A1, Name: John Doe, BirthDate: 2000-01-01, ...
RecordId: A2, Name: Jane Smith, BirthDate: 1985-06-15, ...
```

### Dataset B

```
RecordId: B1, Name: Jon Doe, BirthDate: 2000-01-01, ...     # Same person as A1 (typo in name)
RecordId: B2, Name: Jane Smith, BirthDate: 1985-06-15, ...   # Same person as A2
RecordId: B3, Name: Alice Brown, BirthDate: 1990-03-20, ...  # No match
```

### Tokens Generated

```
Token(A1, T1) == Token(B1, T1)  ✓ Match (same: last name, first initial, sex, birthdate)
Token(A1, T2) != Token(B1, T2)  ✗ Mismatch (first name differs: JOHN vs JON)
Token(A1, T3) != Token(B1, T3)  ✗ Mismatch (first name differs)
Token(A1, T4) == Token(B1, T4)  ✓ Match (same: SSN, sex, birthdate)
Token(A1, T5) == Token(B1, T5)  ✓ Match (same: last name, first 3 chars, sex)

Token(A2, T1) == Token(B2, T1)  ✓ Match (exact match across attributes)
Token(A2, T2) == Token(B2, T2)  ✓ Match
Token(A2, T3) == Token(B2, T3)  ✓ Match
Token(A2, T4) == Token(B2, T4)  ✓ Match
Token(A2, T5) == Token(B2, T5)  ✓ Match

Token(A1, T1) != Token(B3, T1)  ✗ No match for all rules
Token(A2, T1) != Token(B3, T1)  ✗ No match for all rules
```

### Matching Strategy

A **match is confirmed** when:

- Tokens match across **multiple rules** (not just one)
- The matching rules provide **high discriminative power** (not just sex + birthdate, which is common)

This approach handles:

- **Typos and name variations**: T3 and T5 allow first name differences
- **Data completeness**: T4 works even if SSN is unavailable (use T1–T3 instead)
- **High confidence**: Matching on multiple rules reduces false positives

## Matching Output Format

When you process two datasets and compare tokens:

```json
{
  "RecordA": "A1",
  "RecordB": "B1",
  "MatchingRules": ["T1", "T4", "T5"],
  "ConfidenceLevel": "High",
  "ReasonsForMatch": [
    "T1 match: Last name, first initial, sex, birthdate all consistent",
    "T4 match: SSN, sex, birthdate all match (most authoritative)",
    "T5 match: Last name, first 3 chars, sex all match"
  ]
}
```

## Token Encryption & Decryption

Tokens are encrypted to prevent re-identification, but can be decrypted to debug or verify:

```bash
# Generate encrypted tokens (default mode)
olt package \
  -i data.csv -o output.csv \
  -h "HashingKey" -e "EncryptionKey"

# Decrypt previously encrypted tokens
olt decrypt \
  -i output.csv -o decrypted.csv \
  -e "EncryptionKey"
```

Decrypted tokens show the HMAC-SHA256 hash (base64 encoded) before AES encryption—useful for debugging attribute normalization issues.

## Attributes Used in Token Rules

All tokens use normalized attributes. See [Security](../security.md) for detailed rules.

### Quick Reference

| Attribute  | Normalization                                           | Example                                               |
| ---------- | ------------------------------------------------------- | ----------------------------------------------------- |
| FirstName  | Uppercase, remove titles/suffixes, normalize diacritics | "José María" → "JOSE MARIA"                           |
| LastName   | Uppercase, remove suffixes, normalize diacritics        | "O'Brien" → "OBRIEN"                                  |
| Sex        | Standardized to "Male" or "Female"                      | "M", "m", "Male" → "MALE"                             |
| BirthDate  | YYYY-MM-DD format                                       | "01/15/1980", "1980-01-15" → "1980-01-15"             |
| PostalCode | Uppercase, dash removed for US; space for Canadian      | "98004", "98004-1234" → "98004", "K1A 1A1" → "K1A1A1" |
| SSN        | 9-digit numeric                                         | "123-45-6789" → digits-only string                    |

## Collision Resistance

The token generation pipeline ensures **high collision resistance**:

1. **SHA-256**: ~2^256 possible outputs (collision probability: ~1 in 2^128)
2. **HMAC-SHA256**: Adds secret key; prevents pre-computed tables
3. **AES-256**: Adds another layer of encryption; prevents token re-identification

Even with SHA-256's theoretical weaknesses, Open Link Token's combination is secure for regulated PII use cases.

## Next Steps

- **Understand validation rules**: [Security](../security.md)
- **Decrypt and debug tokens**: [Running Open Link Token](../running-openlinktoken/index.md)
- **View full token specification**: [Specification](../specification.md)
- **Integrate with your system**: [Configuration](../config/configuration.md)
