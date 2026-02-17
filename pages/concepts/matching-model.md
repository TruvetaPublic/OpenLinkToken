---
layout: default
---

# Matching Model

OpenToken uses a multi-rule tokenization strategy to enable privacy-preserving person matching across datasets that contain PII.

---

## Overview

The matching model generates cryptographically secure tokens from personal identifiers (PII) without exposing the underlying data. Different token rules balance **precision** (fewer false positives) against **recall** (fewer missed matches).

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Person Record (PII)                          │
│  Name, DOB, SSN, Sex, Postal Code                              │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Normalization                                │
│  - Remove titles/suffixes                                       │
│  - Strip diacritics                                             │
│  - Standardize formats                                          │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Validation                                   │
│  - Date ranges                                                  │
│  - SSN patterns                                                 │
│  - Required fields                                              │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                Token Generation (T1-T5)                         │
│  - Concatenate attributes per rule                              │
│  - HMAC-SHA256 hash                                             │
│  - Optional AES-256 encryption                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Why Multiple Token Rules?

Real-world data is messy:

- Names may have typos or variations
- Dates may be recorded differently
- SSNs may be missing or partially known
- Addresses change over time

Using **five distinct rules** allows matching at different confidence levels:

OpenToken emits tokens with a `RuleId` of `T1`–`T5`. These identifiers are **rule names**, not “tiers” (they don’t imply an ordering). In practice, different rules tend to trade off precision vs. recall based on which attributes they include.

| RuleId | Attributes (normalized signature)      | Typical use                                             |
| :----- | :------------------------------------- | :------------------------------------------------------ |
| T1     | Last + First initial + Sex + BirthDate | Higher recall; tolerates first-name variation           |
| T2     | Last + First + BirthDate + ZIP-3       | Adds geography; helps when sex is unreliable or missing |
| T3     | Last + First + Sex + BirthDate         | Higher precision; stricter than T1                      |
| T4     | SSN (digits) + Sex + BirthDate         | Very high precision when SSN is present                 |
| T5     | Last + First[0:3] + Sex                | Highest recall / lowest precision; use cautiously       |

---

## Token Rules Summary

### T1: Last Name + First Initial + Sex + BirthDate

```text
LastName + FirstName (first initial) + Sex + BirthDate
```

Designed for higher recall when first names vary (e.g., nicknames) by using only the first initial.

- **Strengths**: Tolerates first-name variation; good candidate generator
- **Limitations**: Lower precision than full-name rules (only first initial)

---

### T2: Last Name + First Name + BirthDate + ZIP-3

```text
LastName + FirstName + BirthDate + PostalCode (ZIP-3)
```

Uses full first name and adds a coarse location signal (ZIP-3).

- **Strengths**: Adds geography; useful when sex is missing/unreliable
- **Limitations**: Requires postal code; ZIP can change over time

---

### T3: Last Name + First Name + Sex + BirthDate

```text
LastName + FirstName + Sex + BirthDate
```

More specific than T1 (uses full first name), so it tends to be higher precision but less tolerant of first-name variation.

- **Strengths**: Higher precision when names are stable
- **Limitations**: Full first name required; more sensitive to name variation/typos

---

### T4: SSN (Digits) + Sex + BirthDate

```text
SSN (digits only) + Sex + BirthDate
```

Very high precision when SSN is present and valid.

- **Strengths**: Highest precision
- **Limitations**: Requires SSN (often missing)

---

### T5: Last Name + First 3 Letters + Sex

```text
LastName + FirstName (first 3 chars) + Sex
```

Uses only the first 3 characters of first name.

- **Strengths**: Highest recall for first-name variation
- **Limitations**: Lower precision; no birth date in the signature

---

## Matching Strategies

### Union Matching (High Recall)

Match if **any** token rule matches:

```text
Match = T1 ∨ T2 ∨ T3 ∨ T4 ∨ T5
```

Use for: Research studies, broad population analysis

### Intersection Matching (High Precision)

Match only if **multiple** rules match:

```text
Match = (T1 ∨ T2) ∧ (T3 ∨ T4)
```

Use for: Clinical record linkage, regulatory requirements

### Tiered Matching

Apply rules in sequence, stopping at first match:

```python
for rule in [T1, T2, T3, T4, T5]:
    if rule.matches(record_a, record_b):
        return (True, rule.confidence)
return (False, None)
```

Use for: Adaptive matching based on data quality

---

## Collision Resistance

Token security relies on:

1. **HMAC-SHA256**: Cryptographically secure hash function
2. **Secret keys**: Organization-specific hashing keys
3. **Normalization**: Consistent input formatting
4. **AES-256**: Optional encryption layer

Two different people producing the same token (collision) is statistically negligible when:

- Keys are properly managed
- Input data is correctly normalized

---

## Worked Example: From Person Data to Tokens and Matches

This section walks through a complete example: raw input data → normalization → token generation → matching decisions.

### Sample Dataset

Consider four fictional person records from two different systems:

| RecordId | FirstName | LastName   | BirthDate  | Sex    | PostalCode | SSN         |
| -------- | --------- | ---------- | ---------- | ------ | ---------- | ----------- |
| HOS-101  | María     | García Jr. | 03/22/1988 | Female | 90210      | 452-38-7291 |
| HOS-102  | tom       | O'Reilly   | 1995-11-03 | M      | 30301-4455 | 671-82-9134 |
| CLN-201  | Maria     | Garcia     | 1988-03-22 | F      | 90210      | 452-38-7291 |
| CLN-202  | Thomas    | O'Reilly   | 11/03/1995 | Male   | 30301      | —           |

**HOS-** records come from a hospital system; **CLN-** records come from a clinic.

### Step 1: Normalization

OpenToken normalizes each field before token generation. For full rules, see [Normalization and Validation](normalization-and-validation.md).

| RecordId | FirstName | LastName | BirthDate  | Sex | PostalCode | SSN         |
| -------- | --------- | -------- | ---------- | --- | ---------- | ----------- |
| HOS-101  | MARIA     | GARCIA   | 1988-03-22 | F   | 90210      | 452-38-7291 |
| HOS-102  | TOM       | OREILLY  | 1995-11-03 | M   | 30301      | 671-82-9134 |
| CLN-201  | MARIA     | GARCIA   | 1988-03-22 | F   | 90210      | 452-38-7291 |
| CLN-202  | THOMAS    | OREILLY  | 1995-11-03 | M   | 30301      | —           |

**What changed:**

- **María → MARIA**: Diacritic removed, uppercased
- **García Jr. → GARCIA**: Suffix removed, diacritic removed, uppercased
- **tom → TOM**: Uppercased
- **03/22/1988 → 1988-03-22**: Date reformatted to ISO 8601
- **30301-4455 → 30301**: ZIP+4 truncated to 5 digits
- **SSN missing (CLN-202)**: Noted; T4 will be skipped for this record

### Step 2: Token Generation

Each record produces up to five tokens (T1–T5). In encrypted mode, tokens are emitted as `ot.V1` JWE strings. In hash-only mode (or after decryption), tokens are base64-encoded HMAC values used for deterministic equality checks.

For detailed rule compositions, see [Token Rules](token-rules.md).

**HOS-101 (María García, 1988-03-22):**

| Rule | Token Signature                  | Illustrative Token       |
| ---- | -------------------------------- | ------------------------ |
| T1   | `GARCIA\|M\|F\|1988-03-22`       | `Xk9mT2pLc1VhR3dNZUZ...` |
| T2   | `GARCIA\|MARIA\|1988-03-22\|902` | `bHdRa0VuWXBCdkxhTnI...` |
| T3   | `GARCIA\|MARIA\|F\|1988-03-22`   | `cTdYc1pNdkpUa2JQeHo...` |
| T4   | `452387291\|F\|1988-03-22`       | `ZnBOdFdtS2haQWdWcko...` |
| T5   | `GARCIA\|MAR\|F`                 | `RWtqVXhMY0dTcldmbVk...` |

**CLN-201 (Maria Garcia, 1988-03-22):**

| Rule | Token Signature                  | Illustrative Token       |
| ---- | -------------------------------- | ------------------------ |
| T1   | `GARCIA\|M\|F\|1988-03-22`       | `Xk9mT2pLc1VhR3dNZUZ...` |
| T2   | `GARCIA\|MARIA\|1988-03-22\|902` | `bHdRa0VuWXBCdkxhTnI...` |
| T3   | `GARCIA\|MARIA\|F\|1988-03-22`   | `cTdYc1pNdkpUa2JQeHo...` |
| T4   | `452387291\|F\|1988-03-22`       | `ZnBOdFdtS2haQWdWcko...` |
| T5   | `GARCIA\|MAR\|F`                 | `RWtqVXhMY0dTcldmbVk...` |

**Observation:** HOS-101 and CLN-201 produce **identical token signatures** for all five rules because their normalized attributes are identical. Their hash-only values (or decrypted values) match exactly; encrypted `ot.V1` token strings can differ because encryption uses random IVs.

**HOS-102 (tom O'Reilly, 1995-11-03):**

| Rule | Token Signature                 | Illustrative Token       |
| ---- | ------------------------------- | ------------------------ |
| T1   | `OREILLY\|T\|M\|1995-11-03`     | `UXdlcnR5VWlPcEFzRGZ...` |
| T2   | `OREILLY\|TOM\|1995-11-03\|303` | `WnhjdmJubUtMbUpIR2d...` |
| T3   | `OREILLY\|TOM\|M\|1995-11-03`   | `QWxza2RqZmhHa0xQb1p...` |
| T4   | `671829134\|M\|1995-11-03`      | `TW5iVmN4WmFRd0VyVHl...` |
| T5   | `OREILLY\|TOM\|M`               | `SWp1aHlHdEZyRGVTd1d...` |

**CLN-202 (Thomas O'Reilly, 1995-11-03, no SSN):**

| Rule | Token Signature                    | Illustrative Token       |
| ---- | ---------------------------------- | ------------------------ |
| T1   | `OREILLY\|T\|M\|1995-11-03`        | `RHZiTmNYemFRd0VyWnR...` |
| T2   | `OREILLY\|THOMAS\|1995-11-03\|303` | `S2p1aHlHdEZyRGVWd1h...` |
| T3   | `OREILLY\|THOMAS\|M\|1995-11-03`   | `VXl0ckVXcUFzRGZHaEp...` |
| T4   | — (SSN missing)                    | *Not generated*          |
| T5   | `OREILLY\|THO\|M`                  | `QmFzZTY0UExhY2Vob2w...` |

**Observation:** HOS-102 and CLN-202 can match on **T1** (first initial) even though the full first name differs (TOM vs THOMAS). They do **not** match on rules that require the full first name, and they cannot generate T4 because the SSN is missing.

### Step 3: Matching Decisions

When comparing hash-only (or decrypted) token values across the two systems:

| Record Pair       | T1  | T2  | T3  | T4  | T5  | Match?                |
| ----------------- | --- | --- | --- | --- | --- | --------------------- |
| HOS-101 ↔ CLN-201 | ✓   | ✓   | ✓   | ✓   | ✓   | **Yes** (all rules)   |
| HOS-102 ↔ CLN-202 | ✓   | ✗   | ✗   | —   | ✗   | **Depends** (T1 only) |
| HOS-101 ↔ HOS-102 | ✗   | ✗   | ✗   | ✗   | ✗   | No                    |
| CLN-201 ↔ CLN-202 | ✗   | ✗   | ✗   | ✗   | ✗   | No                    |

**Interpretation:**

- **HOS-101 and CLN-201 are the same person.** Despite surface differences ("María" vs "Maria", suffix "Jr."), normalization produces identical attributes, so all deterministic token values match.
- **HOS-102 and CLN-202 may be the same person, but only match on T1.** Depending on your matching policy, you might require multiple-rule agreement (higher precision) or accept single-rule matches (higher recall).

### Key Takeaways

1. **Normalization is critical.** Two records with superficially different inputs (accents, suffixes, date formats) can match perfectly after normalization.
2. **Missing attributes reduce matching opportunities.** CLN-202 couldn't generate T4 because SSN was missing.
3. **Name variations may prevent matches.** "Tom" vs "Thomas" is a common real-world issue; T5's 3-character prefix helps only if the first 3 letters are identical.
4. **Multiple rules provide fallback.** Even if T4 can't be generated (SSN missing), other rules may still match if other attributes align.

### Related Pages

- [Token Rules](token-rules.md) — Detailed composition of T1–T5
- [Normalization and Validation](normalization-and-validation.md) — Full normalization and validation rules

---

## Cross-Organization Matching

For records from different organizations to match:

1. **Same keys**: Both organizations must use identical hashing/encryption keys
2. **Same normalization**: Attribute processing must be identical
3. **Same rules**: Token generation logic must match exactly

OpenToken ensures this through:

- Dual Java/Python implementations with byte-identical outputs
- Comprehensive normalization documentation
- Interoperability testing

---

## Further Reading

- [Token Rules](token-rules.md) - Detailed rule specifications
- [Normalization](normalization-and-validation.md) - How attributes are standardized
- [Security Model](../security.md) - Cryptographic guarantees
