---
layout: default
---

# Token and Attribute Registration

This guide explains how to register custom tokens and attributes in both Java and Python implementations to ensure cross-language parity.

## Overview

OpenLinkToken uses different registration mechanisms:

| Language | Mechanism         | Location             |
| -------- | ----------------- | -------------------- |
| Java     | ServiceLoader SPI | `META-INF/services/` |
| Python   | Explicit imports  | Loader classes       |

**Critical**: Both implementations must be updated together to maintain cross-language compatibility.

## Java Registration (ServiceLoader SPI)

Java uses the ServiceLoader pattern for runtime discovery.

### Registering a New Attribute

1. **Create the attribute class** extending `BaseAttribute`:

```java
package com.truveta.openlinktoken.attributes.person;

import java.util.List;

import com.truveta.openlinktoken.attributes.BaseAttribute;
import com.truveta.openlinktoken.attributes.validation.RegexValidator;

/**
 * Middle name attribute with standard string normalization.
 */
public class MiddleNameAttribute extends BaseAttribute {
    private static final String NAME = "MiddleName";
    private static final String[] ALIASES = new String[] { NAME };

    public MiddleNameAttribute() {
        super(List.of(new RegexValidator("^[A-Za-z\\s\\-']+$")));
    }

    @Override
    public String getName() {
        return NAME;
    }

    @Override
    public String[] getAliases() {
        return ALIASES;
    }

    @Override
    public String normalize(String value) {
        if (value == null) {
            throw new IllegalArgumentException("MiddleName value cannot be null");
        }
        return value.trim();
    }
}
```

2. **Register in service file** at [lib/java/openlinktoken/src/main/resources/META-INF/services/com.truveta.openlinktoken.attributes.Attribute](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/lib/java/openlinktoken/src/main/resources/META-INF/services/com.truveta.openlinktoken.attributes.Attribute):

```
com.truveta.openlinktoken.attributes.general.DateAttribute
com.truveta.openlinktoken.attributes.general.RecordIdAttribute
com.truveta.openlinktoken.attributes.general.StringAttribute
com.truveta.openlinktoken.attributes.person.BirthDateAttribute
com.truveta.openlinktoken.attributes.person.FirstNameAttribute
com.truveta.openlinktoken.attributes.person.LastNameAttribute
com.truveta.openlinktoken.attributes.person.MiddleNameAttribute
com.truveta.openlinktoken.attributes.person.PostalCodeAttribute
com.truveta.openlinktoken.attributes.person.SexAttribute
com.truveta.openlinktoken.attributes.person.SocialSecurityNumberAttribute
```

**Rules for service files:**

- One fully-qualified class name per line
- Keep entries **alphabetically sorted**
- No blank lines or comments
- No trailing whitespace

### Registering a New Token Rule

1. **Create the token class** implementing `Token`:

```java
package com.truveta.openlinktoken.tokens.definitions;

import java.util.ArrayList;

import com.truveta.openlinktoken.attributes.AttributeExpression;
import com.truveta.openlinktoken.attributes.person.BirthDateAttribute;
import com.truveta.openlinktoken.attributes.person.FirstNameAttribute;
import com.truveta.openlinktoken.attributes.person.LastNameAttribute;
import com.truveta.openlinktoken.attributes.person.PostalCodeAttribute;
import com.truveta.openlinktoken.tokens.Token;

/**
 * Token rule T6 - Example custom token.
 */
public class T6Token implements Token {
    private static final long serialVersionUID = 1L;
    private static final String ID = "T6";

    private final ArrayList<AttributeExpression> definition = new ArrayList<>();

    public T6Token() {
        definition.add(new AttributeExpression(LastNameAttribute.class, "T|U"));
        definition.add(new AttributeExpression(FirstNameAttribute.class, "T|U"));
        definition.add(new AttributeExpression(BirthDateAttribute.class, "T|D"));
        definition.add(new AttributeExpression(PostalCodeAttribute.class, "T|S(0,3)"));
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

2. **Register in service file** at [lib/java/openlinktoken/src/main/resources/META-INF/services/com.truveta.openlinktoken.tokens.Token](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/lib/java/openlinktoken/src/main/resources/META-INF/services/com.truveta.openlinktoken.tokens.Token):

```
com.truveta.openlinktoken.tokens.definitions.T1Token
com.truveta.openlinktoken.tokens.definitions.T2Token
com.truveta.openlinktoken.tokens.definitions.T3Token
com.truveta.openlinktoken.tokens.definitions.T4Token
com.truveta.openlinktoken.tokens.definitions.T5Token
com.truveta.openlinktoken.tokens.definitions.T6Token
```

## Python Registration (Explicit Imports)

Python uses explicit imports in loader classes.

### Registering a New Attribute

1. **Create the attribute class**:

```python
# lib/python/openlinktoken/src/main/openlinktoken/attributes/person/middle_name_attribute.py

from typing import List

from openlinktoken.attributes.base_attribute import BaseAttribute
from openlinktoken.attributes.validation.regex_validator import RegexValidator


class MiddleNameAttribute(BaseAttribute):
    """Middle name attribute with standard string normalization."""

    NAME = "MiddleName"
    ALIASES = [NAME]

    def __init__(self):
        super().__init__([
            RegexValidator(r"^[A-Za-z\s\-']+$"),
        ])

    def get_name(self) -> str:
        return self.NAME

    def get_aliases(self) -> List[str]:
        return self.ALIASES.copy()

    def normalize(self, value: str) -> str:
        if value is None:
            raise ValueError("MiddleName value cannot be null")
        return value.strip()
```

2. **Register in AttributeLoader**:

Edit `lib/python/openlinktoken/src/main/openlinktoken/attributes/attribute_loader.py`:

```python
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.middle_name_attribute import MiddleNameAttribute  # Add import
from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
# ... other imports

class AttributeLoader:
    @staticmethod
    def load():
        return {
            FirstNameAttribute(),
            LastNameAttribute(),
            MiddleNameAttribute(),  # Add to set
            BirthDateAttribute(),
            # ... other attributes
        }
```

### Registering a New Token Rule

1. **Create the token class**:

```python
# lib/python/openlinktoken/src/main/openlinktoken/tokens/definitions/t6_token.py

from typing import List

from openlinktoken.attributes.attribute_expression import AttributeExpression
from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from openlinktoken.tokens.token import Token

class T6Token(Token):
    """Token rule T6 - Example custom token."""

    ID = "T6"

    def __init__(self):
        self._definition = [
            AttributeExpression(LastNameAttribute, "T|U"),
            AttributeExpression(FirstNameAttribute, "T|U"),
            AttributeExpression(BirthDateAttribute, "T|D"),
            AttributeExpression(PostalCodeAttribute, "T|S(0,3)"),
        ]

    def get_identifier(self) -> str:
        return self.ID

    def get_definition(self) -> List[AttributeExpression]:
        return self._definition
```

2. **No registry edit needed for tokens**:

The Python `TokenRegistry.load_all_tokens()` implementation discovers `Token` subclasses by scanning modules in `openlinktoken.tokens.definitions`. As long as your new token lives under that package (for example `t6_token.py`), it will be picked up automatically.

## Cross-Language Sync Verification

### Using the Sync Tool

After making changes in both languages, verify parity:

```bash
python3 tools/multi_language_syncer.py
```

This tool checks:

- Attribute names match between Java and Python
- Token rules are identical
- Normalization logic produces same outputs
- Registration files are complete

### Interoperability Testing

Run the interoperability test suite:

```bash
cd /workspaces/OpenLinkToken/tools/interoperability
python multi_language_interoperability_test.py
```

This verifies that identical inputs produce identical token outputs in both languages.

## File Locations Summary

### Java Files

| Type                   | Location                                                                                                                                                                                                                                                                          |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Attribute classes      | [lib/java/openlinktoken/src/main/java/com/truveta/openlinktoken/attributes/](https://github.com/TruvetaPublic/OpenLinkToken/tree/main/lib/java/openlinktoken/src/main/java/com/truveta/openlinktoken/attributes)                                                                  |
| Token classes          | [lib/java/openlinktoken/src/main/java/com/truveta/openlinktoken/tokens/definitions/](https://github.com/TruvetaPublic/OpenLinkToken/tree/main/lib/java/openlinktoken/src/main/java/com/truveta/openlinktoken/tokens/definitions)                                                  |
| Attribute service file | [lib/java/openlinktoken/src/main/resources/META-INF/services/com.truveta.openlinktoken.attributes.Attribute](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/lib/java/openlinktoken/src/main/resources/META-INF/services/com.truveta.openlinktoken.attributes.Attribute) |
| Token service file     | [lib/java/openlinktoken/src/main/resources/META-INF/services/com.truveta.openlinktoken.tokens.Token](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/lib/java/openlinktoken/src/main/resources/META-INF/services/com.truveta.openlinktoken.tokens.Token)                 |

### Python Files

| Type              | Location                                                                                                                                                                                                                                   |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Attribute classes | [lib/python/openlinktoken/src/main/openlinktoken/attributes/](https://github.com/TruvetaPublic/OpenLinkToken/tree/main/lib/python/openlinktoken/src/main/openlinktoken/attributes)                                                         |
| Token classes     | [lib/python/openlinktoken/src/main/openlinktoken/tokens/definitions/](https://github.com/TruvetaPublic/OpenLinkToken/tree/main/lib/python/openlinktoken/src/main/openlinktoken/tokens/definitions)                                         |
| Attribute loader  | [lib/python/openlinktoken/src/main/openlinktoken/attributes/attribute_loader.py](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/lib/python/openlinktoken/src/main/openlinktoken/attributes/attribute_loader.py)                  |
| Token discovery   | [lib/python/openlinktoken/src/main/openlinktoken/tokens/token_registry.py](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/lib/python/openlinktoken/src/main/openlinktoken/tokens/token_registry.py) (auto-discovers definitions) |

## Common Mistakes

### Java

❌ **Forgetting service file entry**

```
# Attribute won't be discovered at runtime!
```

❌ **Unsorted service file**

```
com.truveta.openlinktoken.attributes.person.SexAttribute
com.truveta.openlinktoken.attributes.person.BirthDateAttribute  # Should be sorted
```

❌ **Blank lines or comments in service file**

```
com.truveta.openlinktoken.attributes.person.BirthDateAttribute

# This comment breaks ServiceLoader
com.truveta.openlinktoken.attributes.person.FirstNameAttribute
```

### Python

❌ **Forgetting loader import**

```python
# AttributeLoader.load() won't include the new attribute!
```

❌ **Not matching module layout**

Keep person attributes under `openlinktoken.attributes.person` (for example `openlinktoken/attributes/person/middle_name_attribute.py`), then import from that module and add the attribute instance to `AttributeLoader.load()`.

### Both Languages

❌ **Updating only one language**

```
# Cross-language parity broken!
# Java has MiddleNameAttribute, Python doesn't
```

❌ **Different attribute names**

```java
// Java: "MiddleName"
// Python: "middle_name"
// These will NOT match!
```

## Checklist for New Attributes/Tokens

Before submitting a PR with new attributes or tokens:

- [ ] Java class created with proper inheritance
- [ ] Java service file updated (sorted alphabetically)
- [ ] Python class created with matching logic
- [ ] Python `AttributeLoader.load()` updated (attributes)
- [ ] Python token module added under `tokens/definitions/` (tokens)
- [ ] Unit tests added for both languages
- [ ] Sync tool passes: `python3 tools/multi_language_syncer.py`
- [ ] Interoperability tests pass
- [ ] Documentation updated

## Next Steps

- [Java API Reference](java-api.md) - Java class details
- [Python API Reference](python-api.md) - Python module details
- [CLI Reference](cli.md) - Command-line options
