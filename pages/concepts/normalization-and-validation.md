---
layout: default
---

# Normalization and Validation

Open Link Token applies consistent normalization and validation rules to ensure accurate, reproducible token generation across different data sources.

---

## Overview

Every attribute goes through two phases:

1. **Normalization**: Transform input to a standard format
2. **Validation**: Verify the normalized value meets requirements

```
Input → Normalize → Validate → Token Generation
         ↓            ↓
      Standard     Accept/
       Format      Reject
```

---

## Name Attributes

### First Name / Last Name

**Normalization Steps:**

1. Trim leading/trailing whitespace
2. Convert to uppercase
3. Remove diacritics and transliterate supported Latin Extended letters to ASCII (é → E, Ł → L, Æ → AE)
4. Remove titles: Dr, Mr, Mrs, Ms, Miss, Prof
5. Remove suffixes: Jr, Sr, II, III, IV, PhD, MD
6. Remove non-alphabetic characters (spaces, apostrophes, hyphens, periods)

**Examples:**

| Input          | Normalized |
| -------------- | ---------- |
| `"  John  "`   | `"JOHN"`   |
| `"María"`      | `"MARIA"`  |
| `"Łukasz"`     | `"LUKASZ"` |
| `"Søren"`      | `"SOREN"`  |
| `"Ægir"`       | `"AEGIR"`  |
| `"Øst"`        | `"OST"`    |
| `"Dr. Smith"`  | `"SMITH"`  |
| `"O'Brien"`    | `"OBRIEN"` |
| `"Œberg"`      | `"OEBERG"` |
| `"García Jr."` | `"GARCIA"` |

**Validation:**

- Must not be empty after normalization
- No numeric characters allowed

---

## Birth Date

**Normalization:**

- Parse multiple date formats
- Output as `yyyy-MM-dd` (ISO 8601)

**Accepted Input Formats:**

| Format        | Example     |
| ------------- | ----------- |
| `yyyy-MM-dd`  | 1985-03-15  |
| `MM/dd/yyyy`  | 03/15/1985  |
| `M/d/yyyy`    | 3/15/1985   |
| `dd-MMM-yyyy` | 15-Mar-1985 |

**Validation Rules:**

| Rule         | Value       |
| ------------ | ----------- |
| Minimum date | 1910-01-01  |
| Maximum date | Today       |
| Age range    | 0-115 years |

**Examples:**

| Input          | Normalized     | Valid           |
| -------------- | -------------- | --------------- |
| `"03/15/1985"` | `"1985-03-15"` | ✓               |
| `"1985-03-15"` | `"1985-03-15"` | ✓               |
| `"1899-01-01"` | —              | ✗ (before 1910) |
| `"2099-01-01"` | —              | ✗ (future date) |

---

## Social Security Number (SSN)

**Normalization:**

- Remove all non-digit characters
- Format as `XXX-XX-XXXX`

**Validation Rules:**

| Rule             | Description              |
| ---------------- | ------------------------ |
| Length           | Exactly 9 digits         |
| Area (first 3)   | Not 000, 666, or 900-999 |
| Group (middle 2) | Not 00                   |
| Serial (last 4)  | Not 0000                 |
| Known invalid    | Reject common test SSNs  |

**Invalid SSN Patterns:**

```
000-XX-XXXX  (Invalid area)
666-XX-XXXX  (Invalid area)
9XX-XX-XXXX  (Reserved for ITIN)
XXX-00-XXXX  (Invalid group)
XXX-XX-0000  (Invalid serial)
111-11-1111  (Common test pattern)
123-45-6789  (Common test pattern)
```

**Examples:**

| Input                  | Normalized      | Valid          |
| ---------------------- | --------------- | -------------- |
| `"123-45-6789"`        | —               | ✗ (test SSN)   |
| `"078-05-1120"`        | `"078-05-1120"` | ✓              |
| `"000-12-3456"`        | —               | ✗ (area = 000) |
| Digits-only test input | `"123-45-6789"` | ✗ (test SSN)   |

---

## Sex

**Normalization:**

- Convert to uppercase
- Map to single character

**Accepted Values:**

| Input                     | Normalized |
| ------------------------- | ---------- |
| `"M"`, `"Male"`, `"m"`    | `"M"`      |
| `"F"`, `"Female"`, `"f"`  | `"F"`      |
| `"U"`, `"Unknown"`, `"u"` | `"U"`      |

**Validation:**

- Must be M, F, or U after normalization

---

## Postal Code

**Normalization by Country:**

**US ZIP Codes:**

- Extract first 5 digits
- Accept 5-digit or ZIP+4 format

**Canadian Postal Codes:**

- Uppercase
- Format as `A1A 1A1`

**Examples:**

| Input          | Normalized  | Valid           |
| -------------- | ----------- | --------------- |
| `"98101"`      | `"98101"`   | ✓               |
| `"98101-1234"` | `"98101"`   | ✓               |
| `"k1a 0b1"`    | `"K1A 0B1"` | ✓               |
| `"00000"`      | —           | ✗ (placeholder) |
| `"12345"`      | —           | ✗ (test ZIP)    |

**Invalid Postal Codes:**

```
00000  (Placeholder)
12345  (Common test)
99999  (Placeholder)
```

---

## ZIP3 (Partial Postal Code)

**Purpose:** Broader geographic matching with reduced precision

**Normalization:**

- Extract first 3 digits of postal code

**Examples:**

| Postal Code  | ZIP3  |
| ------------ | ----- |
| `98101`      | `981` |
| `98101-1234` | `981` |
| `10001`      | `100` |

---

## Validation Architecture

### Composable Validators

Validators can be chained for complex rules:

```java
// Java example
List<Validator> validators = List.of(
    new RegexValidator("^[A-Z]+$"),
    new MinLengthValidator(2),
    new MaxLengthValidator(50)
);
```

```python
# Python example
validators = [
    RegexValidator(r"^[A-Z]+$"),
    MinLengthValidator(2),
    MaxLengthValidator(50)
]
```

### Built-in Validators

| Validator            | Purpose               |
| -------------------- | --------------------- |
| `RegexValidator`     | Pattern matching      |
| `DateRangeValidator` | Date bounds           |
| `AgeRangeValidator`  | Age at reference date |
| `MinLengthValidator` | Minimum string length |
| `MaxLengthValidator` | Maximum string length |

---

## Thread Safety

All normalization and validation operations are thread-safe:

- Regex patterns are pre-compiled and immutable
- Date formatters use `DateTimeFormatter` (thread-safe)
- No shared mutable state

---

## Handling Invalid Data

When validation fails:

1. **Token is not generated** for that rule
2. **Processing continues** to other rules
3. **Metadata tracks aggregate counts** (not per-record reasons)
4. **Original data preserved** (not modified)

```json
{
  "TotalRows": 105,
  "TotalRowsWithInvalidAttributes": 12,
  "InvalidAttributesByType": {
    "BirthDate": 3,
    "FirstName": 1,
    "LastName": 2,
    "PostalCode": 2,
    "Sex": 0,
    "SocialSecurityNumber": 4
  },
  "BlankTokensByRule": {
    "T1": 6,
    "T2": 8,
    "T3": 6,
    "T4": 7,
    "T5": 3
  }
}
```

Notes:

- `.metadata.json` does not include per-record invalid reasons (like `INVALID_LENGTH`) or per-record token skip details.
- To understand why a specific row didn’t generate a token, inspect that row’s output token columns (blank means not generated).
- For the full schema, see [Metadata Format](../reference/metadata-format.md).

---

## Further Reading

- [Matching Model](matching-model.md) - How normalized data becomes tokens
- [Token Rules](token-rules.md) - Which attributes each rule uses
- [API Reference](../reference/) - Programmatic attribute handling
