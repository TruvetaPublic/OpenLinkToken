---
layout: default
---

# Java API Reference

Document the Java classes and methods for programmatic token generation.

## Core Classes

```java
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.openlinktoken.attributes.Attribute;
import org.openlinktoken.attributes.person.BirthDateAttribute;
import org.openlinktoken.attributes.person.FirstNameAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;
import org.openlinktoken.attributes.person.PostalCodeAttribute;
import org.openlinktoken.attributes.person.SexAttribute;
import org.openlinktoken.attributes.person.SocialSecurityNumberAttribute;
import org.openlinktoken.tokens.TokenDefinition;
import org.openlinktoken.tokens.TokenGenerator;
import org.openlinktoken.tokens.TokenGeneratorResult;
import org.openlinktoken.tokens.tokenizer.SHA256Tokenizer;
import org.openlinktoken.tokentransformer.EncryptTokenTransformer;
import org.openlinktoken.tokentransformer.HashTokenTransformer;
import org.openlinktoken.tokentransformer.TokenTransformer;
```

## Person Attribute Map

OpenLinkToken's Java library represents a person's values as a map keyed by attribute class:

```java
Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
personAttributes.put(FirstNameAttribute.class, "John");
personAttributes.put(LastNameAttribute.class, "Doe");
personAttributes.put(BirthDateAttribute.class, "1980-01-15");
personAttributes.put(SexAttribute.class, "Male");
personAttributes.put(PostalCodeAttribute.class, "98004");
personAttributes.put(SocialSecurityNumberAttribute.class, "123-45-6789");
```

Normalization and validation are handled internally by `TokenGenerator` using the attribute implementations loaded via `AttributeLoader`.

## TokenDefinition

`TokenDefinition` encapsulates the built-in T1–T5 rule definitions.

```java
TokenDefinition tokenDefinition = new TokenDefinition();
```

## TokenGenerator

`TokenGenerator` validates/normalizes inputs and produces token signatures and tokens.

### Methods

| Method                                                                | Return Type            | Description                                                    |
| --------------------------------------------------------------------- | ---------------------- | -------------------------------------------------------------- |
| `getAllTokenSignatures(Map<Class<? extends Attribute>, String>)`      | `Map<String, String>`  | Generates signatures for all rules (debug/logging)             |
| `getAllTokens(Map<Class<? extends Attribute>, String>)`               | `TokenGeneratorResult` | Generates tokens for all rules and captures invalid/blank info |
| `getInvalidPersonAttributes(Map<Class<? extends Attribute>, String>)` | `Set<String>`          | Validates all provided attribute values                        |

### Example

```java
List<TokenTransformer> transformers = List.of(
    new HashTokenTransformer("HashingSecret"),
    new EncryptTokenTransformer("Secret-Encryption-Key-Goes-Here.")
);

TokenGenerator generator = new TokenGenerator(
    new TokenDefinition(),
    new SHA256Tokenizer(transformers)
);

var invalid = generator.getInvalidPersonAttributes(personAttributes);
if (!invalid.isEmpty()) {
    System.out.println("Invalid attributes: " + invalid);
}

TokenGeneratorResult result = generator.getAllTokens(personAttributes);
result.getTokens().forEach((ruleId, token) -> System.out.println(ruleId + ": " + token));
```

## Token Transformers

Transform token signatures into encrypted or hashed tokens.

### HashTokenTransformer

One-way hashing without encryption.

```java
HashTokenTransformer hasher = new HashTokenTransformer("YourHashingSecret");

String signature = "DOE|J|MALE|1980-01-15";
String hashedToken = hasher.transform(signature);
// Returns: Base64-encoded HMAC-SHA256 hash
```

### EncryptTokenTransformer

Full encryption with AES-256-GCM.

```java
EncryptTokenTransformer encryptor = new EncryptTokenTransformer(
    "Secret-Encryption-Key-Goes-Here."  // Exactly 32 chars
);

String signature = "DOE|J|MALE|1980-01-15";
String encryptedToken = encryptor.transform(signature);
// Returns: OpenLinkToken encrypted match token string (ot.V1.<JWE compact serialization>)
```

## Complete Example

```java
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.openlinktoken.attributes.Attribute;
import org.openlinktoken.attributes.person.BirthDateAttribute;
import org.openlinktoken.attributes.person.FirstNameAttribute;
import org.openlinktoken.attributes.person.LastNameAttribute;
import org.openlinktoken.attributes.person.PostalCodeAttribute;
import org.openlinktoken.attributes.person.SexAttribute;
import org.openlinktoken.attributes.person.SocialSecurityNumberAttribute;
import org.openlinktoken.tokens.TokenDefinition;
import org.openlinktoken.tokens.TokenGenerator;
import org.openlinktoken.tokens.TokenGeneratorResult;
import org.openlinktoken.tokens.tokenizer.SHA256Tokenizer;
import org.openlinktoken.tokentransformer.EncryptTokenTransformer;
import org.openlinktoken.tokentransformer.HashTokenTransformer;
import org.openlinktoken.tokentransformer.TokenTransformer;

public class TokenGenerator {
    public static void main(String[] args) {
        String recordId = "patient_001";

        Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
        personAttributes.put(FirstNameAttribute.class, "John");
        personAttributes.put(LastNameAttribute.class, "Doe");
        personAttributes.put(BirthDateAttribute.class, "1980-01-15");
        personAttributes.put(SexAttribute.class, "Male");
        personAttributes.put(PostalCodeAttribute.class, "98004");
        personAttributes.put(SocialSecurityNumberAttribute.class, "123-45-6789");

        List<TokenTransformer> transformers = List.of(
            new HashTokenTransformer("HashingSecret"),
            new EncryptTokenTransformer("Secret-Encryption-Key-Goes-Here.")
        );

        TokenGenerator generator = new TokenGenerator(
            new TokenDefinition(),
            new SHA256Tokenizer(transformers)
        );

        var invalid = generator.getInvalidPersonAttributes(personAttributes);
        if (!invalid.isEmpty()) {
            System.err.println("Invalid attributes: " + invalid);
            return;
        }

        TokenGeneratorResult result = generator.getAllTokens(personAttributes);
        result.getTokens().forEach((ruleId, token) ->
            System.out.printf("%s,%s,%s%n", recordId, ruleId, token)
        );
    }
}
```

## Data Integration

The Java library focuses on in-memory token generation. It does not include CSV, Parquet, or other file I/O helper classes.

Use your application's reader or writer layer to map each record into `Map<Class<? extends Attribute>, String>`, then pass that map to `TokenGenerator`.

```java
Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
personAttributes.put(FirstNameAttribute.class, row.get("FirstName"));
personAttributes.put(LastNameAttribute.class, row.get("LastName"));
// ...populate the remaining attributes needed for your token rules

TokenGeneratorResult result = generator.getAllTokens(personAttributes);
```

## Thread Safety

All transformer classes are thread-safe and can be shared across threads:

```java
// Token generation is safe to parallelize across independent records.
// For best clarity, create the per-record attribute map inside the task.
ExecutorService executor = Executors.newFixedThreadPool(4);
for (Map<Class<? extends Attribute>, String> personAttributes : persons) {
    executor.submit(() -> {
        TokenGeneratorResult result = generator.getAllTokens(personAttributes);
        // ...
    });
}
```

## Maven Dependency

```xml
<dependency>
    <groupId>org.openlinktoken</groupId>
    <artifactId>openlinktoken</artifactId>
    <version>2.0.0-alpha</version>
</dependency>
```

## Next Steps

- [Python API Reference](python-api.md) - Cross-language parity
- [Token Registration](token-registration.md) - Add custom tokens
- [CLI Reference](cli.md) - Command-line usage
