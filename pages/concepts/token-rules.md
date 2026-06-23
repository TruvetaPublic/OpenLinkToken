---
layout: default
---

# Token Rules

Open Link Token generates five distinct token types (T1-T5). Each rule defines a **token signature** (a deterministic, normalized string) which is then transformed into the output token via hashing (and optionally encryption).

---

## Overview

Each token rule defines:

- **Required attributes**: Must all be present and valid
- **Concatenation order**: Determines the token signature
- **Use case**: When this rule is most effective

**Notation used below:**

- `U(X)` = uppercase(X)
- `[0]` = first character
- `[0:3]` = first 3 characters

---

## T1: Last Name + First Initial + Sex + Birth Date

**Purpose:** Higher recall matching that tolerates first-name variation

### T1 Signature

```text
T1 = U(LastName) | U(FirstName[0]) | U(Sex) | BirthDate
```

### T1 Characteristics

- **Precision**: Medium-high
- **Recall**: High
- **Best for**: Candidate generation and matching when nicknames/first-name variation are common

### T1 Example

```text
Input:
  FirstName: Thomas
  LastName: O'Reilly
  BirthDate: 11/03/1995
  Sex: Male

Normalized:
  FirstName: THOMAS
  LastName: OREILLY
  BirthDate: 1995-11-03
  Sex: M

Token Signature: "OREILLY|T|M|1995-11-03"
```

---

## T2: Last Name + First Name + Birth Date + ZIP-3

**Purpose:** Adds geography; useful when postal code is available

### T2 Signature

```text
T2 = U(LastName) | U(FirstName) | BirthDate | U(PostalCode[0:3])
```

### T2 Characteristics

- **Precision**: High
- **Recall**: Good (requires postal code)
- **Best for**: Matching within regions; cases where sex is missing or unreliable

### T2 Example

```text
Input:
  FirstName: Maria
  LastName: Garcia
  BirthDate: 03/22/1988
  PostalCode: 90210-4455

Normalized:
  FirstName: MARIA
  LastName: GARCIA
  BirthDate: 1988-03-22
  PostalCode: 90210

Token Signature: "GARCIA|MARIA|1988-03-22|902"
```

---

## T3: Last Name + First Name + Sex + Birth Date

**Purpose:** Higher precision than T1 by requiring the full first name

### T3 Signature

```text
T3 = U(LastName) | U(FirstName) | U(Sex) | BirthDate
```

### T3 Characteristics

- **Precision**: High
- **Recall**: Medium-high
- **Best for**: Stricter matching when you expect name stability

### T3 Example

```text
Token Signature: "GARCIA|MARIA|F|1988-03-22"
```

---

## T4: SSN (Digits Only) + Sex + Birth Date

**Purpose:** Very high precision matching when SSN is present

### T4 Signature

```text
T4 = SSN_digits | U(Sex) | BirthDate
```

Notes:

- The SSN is normalized to digits only (dashes removed).

### T4 Characteristics

- **Precision**: Very high
- **Recall**: Low (SSN often missing)
- **Best for**: High-confidence linking when SSN exists and is valid

### T4 Example

```text
Input SSN: 452-38-7291
SSN_digits: 452387291

Token Signature: "452387291|F|1988-03-22"
```

---

## T5: Last Name + First 3 Letters + Sex

**Purpose:** Highest recall / lowest precision (use cautiously)

### T5 Signature

```text
T5 = U(LastName) | U(FirstName[0:3]) | U(Sex)
```

### T5 Characteristics

- **Precision**: Lower
- **Recall**: Highest
- **Best for**: Broad matching / candidate generation, followed by stricter confirmation

### T5 Example

```text
FirstName: Jonathan -> FirstName[0:3] = JON
Token Signature: "SMITH|JON|M"
```

---

## Token Rule Summary

| RuleId | Signature attributes           | Typical precision | Typical recall |
| ------ | ------------------------------ | ----------------- | -------------- |
| T1     | Last, First[0], Sex, BirthDate | Medium-high       | High           |
| T2     | Last, First, BirthDate, ZIP3   | High              | Good           |
| T3     | Last, First, Sex, BirthDate    | High              | Medium-high    |
| T4     | SSN(digits), Sex, BirthDate    | Very high         | Low            |
| T5     | Last, First[0:3], Sex          | Lower             | Highest        |

---

## Attribute Fallback

When a required attribute is missing or invalid:

1. **Token not generated** for that rule
2. Other rules still computed if their attributes are valid
3. The metadata file records **aggregate counts**

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

- `BlankTokensByRule` counts how many records could **not** produce each rule due to missing/invalid required attributes.
- To see skips per record, look at the output file’s token columns: a blank value means that rule was not generated for that row.

---

## Custom Token Rules

Open Link Token supports defining custom token rules:

### Java

```java
import java.util.ArrayList;

import org.openlinktoken.attributes.AttributeExpression;
import org.openlinktoken.attributes.person.BirthDateAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;
import org.openlinktoken.tokens.Token;

public class CustomToken implements Token {
  private static final long serialVersionUID = 1L;
  private static final String ID = "T6";

  private final ArrayList<AttributeExpression> definition = new ArrayList<>();

  public CustomToken() {
    // Example signature: U(LastName)|BirthDate
    definition.add(new AttributeExpression(LastNameAttribute.class, "T|U"));
    definition.add(new AttributeExpression(BirthDateAttribute.class, "T|D"));
  }

  @Override
  public String getIdentifier() {
    return ID;
  }

  @Override
  public ArrayList<AttributeExpression> getDefinition() {
    return definition;
  }
}
```

### Python

```python
from typing import List

from openlinktoken.attributes.attribute_expression import AttributeExpression
from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.tokens.token import Token

class CustomToken(Token):
  ID = "T6"

  def __init__(self):
    # Example signature: U(LastName)|BirthDate
    self._definition = [
      AttributeExpression(LastNameAttribute, "T|U"),
      AttributeExpression(BirthDateAttribute, "T|D"),
    ]

  def get_identifier(self) -> str:
    return self.ID

  def get_definition(self) -> List[AttributeExpression]:
    return self._definition
```

See [Token Registration](../reference/token-registration.md) for registration details.

---

## Further Reading

- [Matching Model](matching-model.md) - Matching strategies
- [Normalization](normalization-and-validation.md) - Attribute standardization
- [Security](../security.md) - Cryptographic details
