---
layout: default
---

# Token and Attribute Registration

This guide explains how to register custom tokens and attributes in both Java and Python implementations to ensure cross-language parity.

## Overview

Open Link Token uses different registration mechanisms:

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
package org.openlinktoken.attributes.person;

import java.util.List;

import org.openlinktoken.attributes.BaseAttribute;
import org.openlinktoken.attributes.validation.RegexValidator;

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

2. **Register in service file** at [lib/java/openlinktoken/src/main/resources/META-INF/services/org.openlinktoken.attributes.Attribute](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/lib/java/openlinktoken/src/main/resources/META-INF/services/org.openlinktoken.attributes.Attribute):

```
org.openlinktoken.attributes.general.DateAttribute
org.openlinktoken.attributes.general.RecordIdAttribute
org.openlinktoken.attributes.general.StringAttribute
org.openlinktoken.attributes.person.BirthDateAttribute
org.openlinktoken.attributes.person.FirstNameAttribute
org.openlinktoken.attributes.person.LastNameAttribute
org.openlinktoken.attributes.person.MiddleNameAttribute
org.openlinktoken.attributes.person.PostalCodeAttribute
org.openlinktoken.attributes.person.SexAttribute
org.openlinktoken.attributes.person.SocialSecurityNumberAttribute
```

**Rules for service files:**

- One fully-qualified class name per line
- Keep entries **alphabetically sorted**
- No blank lines or comments
- No trailing whitespace

### Registering a New Token Rule

1. **Create the token class** implementing `Token`:

```java
package org.openlinktoken.tokens.definitions;

import java.util.ArrayList;

import org.openlinktoken.attributes.AttributeExpression;
import org.openlinktoken.attributes.person.BirthDateAttribute;
import org.openlinktoken.attributes.person.FirstNameAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;
import org.openlinktoken.attributes.person.PostalCodeAttribute;
import org.openlinktoken.tokens.Token;

/**
 * Token rule T6 - Example custom token.
 */
public class T6Token implements Token {
    private static final long serialVersionUID = 1L;
    private static final String ID = "T6";

    private final ArrayList<AttributeExpression> definition = new ArrayList<>();

    public T6Token() {
        definition.add(new AttributeExpression("LastName", LastNameAttribute.class, "T|U"));
        definition.add(new AttributeExpression("FirstName", FirstNameAttribute.class, "T|U"));
        definition.add(new AttributeExpression("BirthDate", BirthDateAttribute.class, "T|D"));
        definition.add(new AttributeExpression("PostalCode", PostalCodeAttribute.class, "T|S(0,3)"));
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

Each `AttributeExpression` takes the field ID (`"LastName"`, `"FirstName"`, etc.) as its first argument — the string key used to look up the value in the person-attributes map at token generation time. For built-in attributes, use the attribute's canonical name as the field ID so it resolves automatically; see [FieldRegistry and Field IDs](#fieldregistry-and-field-ids) below.

2. **Register in service file** at [lib/java/openlinktoken/src/main/resources/META-INF/services/org.openlinktoken.tokens.Token](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/lib/java/openlinktoken/src/main/resources/META-INF/services/org.openlinktoken.tokens.Token):

```
org.openlinktoken.tokens.definitions.T1Token
org.openlinktoken.tokens.definitions.T2Token
org.openlinktoken.tokens.definitions.T3Token
org.openlinktoken.tokens.definitions.T4Token
org.openlinktoken.tokens.definitions.T5Token
org.openlinktoken.tokens.definitions.T6Token
```

### FieldRegistry and Field IDs

`FieldRegistry` is the resolution layer that maps a field ID string (the key used in the person-attributes map) to the `Attribute` instance that provides normalization and validation for it.

- `FieldRegistry.createDefault()` auto-populates a registry using every built-in attribute's canonical name (`Attribute.getName()`) as its field ID — this is why field IDs like `"LastName"`, `"FirstName"`, `"Sex"`, `"BirthDate"`, `"PostalCode"`, and `"SocialSecurityNumber"` work with no extra registration.
- `TokenGenerator(tokenDefinition, tokenizer)` uses `FieldRegistry.createDefault()` internally, so no setup is required for built-in fields.
- For custom fields — for example, a token that needs both `MotherLastName` and `FatherLastName` — use `FieldRegistry.Builder` to register additional field IDs, then pass the registry explicitly to `TokenGenerator`:

```java
import org.openlinktoken.attributes.FieldRegistry;
import org.openlinktoken.attributes.general.StringAttribute;
import org.openlinktoken.tokens.TokenGenerator;

var stringAttribute = new StringAttribute();

FieldRegistry fieldRegistry = FieldRegistry.Builder.fromDefaults()
    .register("MotherLastName", StringAttribute.class, stringAttribute)
    .register("FatherLastName", StringAttribute.class, stringAttribute)
    .build();

TokenGenerator generator = new TokenGenerator(new TokenDefinition(), new SHA256Tokenizer(transformers), fieldRegistry);
```

Then reference the new field IDs in a token definition, both backed by the same `StringAttribute` class:

```java
definition.add(new AttributeExpression("MotherLastName", StringAttribute.class, "T|U"));
definition.add(new AttributeExpression("FatherLastName", StringAttribute.class, "T|U"));
```

Because entries are looked up by field ID string, `"MotherLastName"` and `"FatherLastName"` stay distinct even though both resolve to `StringAttribute` behavior — any number of fields can share the same attribute class this way.

To generate tokens with a custom `FieldRegistry`, use `getAllTokensViaFieldId(Map<String, String>)` and `getAllTokenSignaturesViaFieldId(Map<String, String>)` on `TokenGenerator`, passing a person-attributes map keyed by field ID string. See [Java API Reference](java-api.md) for full method signatures.

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
            AttributeExpression(LastNameAttribute, "T|U", field_id="LastName"),
            AttributeExpression(FirstNameAttribute, "T|U", field_id="FirstName"),
            AttributeExpression(BirthDateAttribute, "T|D", field_id="BirthDate"),
            AttributeExpression(PostalCodeAttribute, "T|S(0,3)", field_id="PostalCode"),
        ]

    def get_identifier(self) -> str:
        return self.ID

    def get_definition(self) -> List[AttributeExpression]:
        return self._definition
```

Each `AttributeExpression` takes `field_id` — the string key used to look up the value in the person-attributes dict at token generation time. For built-in attributes, use the attribute's canonical name as the field ID so it resolves automatically; see [FieldRegistry and Field IDs](#fieldregistry-and-field-ids-1) below.

2. **No registry edit needed for tokens**:

The Python `TokenRegistry.load_all_tokens()` implementation discovers `Token` subclasses by scanning modules in `openlinktoken.tokens.definitions`. As long as your new token lives under that package (for example `t6_token.py`), it will be picked up automatically.

### FieldRegistry and Field IDs

`FieldRegistry` is the resolution layer that maps a field ID string (the key used in the person-attributes dict) to the `Attribute` instance that provides normalization and validation for it.

- `FieldRegistry.create_default()` auto-populates a registry using every built-in attribute's canonical name (`get_name()`) as its field ID — this is why field IDs like `"LastName"`, `"FirstName"`, `"Sex"`, `"BirthDate"`, `"PostalCode"`, and `"SocialSecurityNumber"` work with no extra registration.
- `TokenGenerator(token_definition, tokenizer)` defaults to `FieldRegistry.create_default()` internally (via the optional `field_registry=` keyword argument), so no setup is required for built-in fields.
- For custom fields — for example, a token that needs both `MotherLastName` and `FatherLastName` — use `FieldRegistry.Builder` to register additional field IDs, then pass the registry explicitly to `TokenGenerator`:

```python
from openlinktoken.attributes.field_registry import FieldRegistry
from openlinktoken.attributes.general.string_attribute import StringAttribute
from openlinktoken.tokens.token_generator import TokenGenerator

string_attribute = StringAttribute()

field_registry = (
    FieldRegistry.Builder.from_defaults()
    .register("MotherLastName", StringAttribute, string_attribute)
    .register("FatherLastName", StringAttribute, string_attribute)
    .build()
)

generator = TokenGenerator(TokenDefinition(), tokenizer, field_registry=field_registry)
```

Then reference the new field IDs in a token definition, both backed by the same `StringAttribute` class:

```python
AttributeExpression(StringAttribute, "T|U", field_id="MotherLastName"),
AttributeExpression(StringAttribute, "T|U", field_id="FatherLastName"),
```

Because entries are looked up by field ID string, `"MotherLastName"` and `"FatherLastName"` stay distinct even though both resolve to `StringAttribute` behavior — any number of fields can share the same attribute class this way.

To generate tokens with a custom `FieldRegistry`, use `get_all_tokens_via_field_id(person_attributes)` and `get_all_token_signatures_via_field_id(person_attributes)` on `TokenGenerator`, passing a person-attributes dict keyed by field ID string. See [Python API Reference](python-api.md) for full method signatures.

> **Note:** The `openlinktoken_pyspark` bridge package (`TokenBuilder`, `CustomTokenDefinition`) uses the class-keyed API and continues to work unchanged.

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

| Type                   | Location                                                                                                                                                                                                                                                          |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Attribute classes      | [lib/java/openlinktoken/src/main/java/org/openlinktoken/attributes/](https://github.com/TruvetaPublic/OpenLinkToken/tree/main/lib/java/openlinktoken/src/main/java/org/openlinktoken/attributes)                                                                  |
| Token classes          | [lib/java/openlinktoken/src/main/java/org/openlinktoken/tokens/definitions/](https://github.com/TruvetaPublic/OpenLinkToken/tree/main/lib/java/openlinktoken/src/main/java/org/openlinktoken/tokens/definitions)                                                  |
| Attribute service file | [lib/java/openlinktoken/src/main/resources/META-INF/services/org.openlinktoken.attributes.Attribute](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/lib/java/openlinktoken/src/main/resources/META-INF/services/org.openlinktoken.attributes.Attribute) |
| Token service file     | [lib/java/openlinktoken/src/main/resources/META-INF/services/org.openlinktoken.tokens.Token](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/lib/java/openlinktoken/src/main/resources/META-INF/services/org.openlinktoken.tokens.Token)                 |

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
org.openlinktoken.attributes.person.SexAttribute
org.openlinktoken.attributes.person.BirthDateAttribute  # Should be sorted
```

❌ **Blank lines or comments in service file**

```
org.openlinktoken.attributes.person.BirthDateAttribute

# This comment breaks ServiceLoader
org.openlinktoken.attributes.person.FirstNameAttribute
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
