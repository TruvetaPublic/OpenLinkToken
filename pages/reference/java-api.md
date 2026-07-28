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

import org.openlinktoken.tokens.TokenDefinition;
import org.openlinktoken.tokens.TokenGenerator;
import org.openlinktoken.tokens.TokenGeneratorResult;
import org.openlinktoken.tokens.tokenizer.SHA256Tokenizer;
import org.openlinktoken.tokentransformer.EncryptTokenTransformer;
import org.openlinktoken.tokentransformer.HashTokenTransformer;
import org.openlinktoken.tokentransformer.TokenTransformer;
```

## Person Attribute Map

Open Link Token's Java library represents a person's values as a map keyed by field ID:

```java
Map<String, String> personAttributes = new HashMap<>();
personAttributes.put("FirstName", "John");
personAttributes.put("LastName", "Doe");
personAttributes.put("BirthDate", "1980-01-15");
personAttributes.put("Sex", "Male");
personAttributes.put("PostalCode", "98004");
personAttributes.put("SocialSecurityNumber", "123-45-6789");
```

Field IDs like `"FirstName"` and `"LastName"` are resolved to attribute behavior (normalization and validation) through `FieldRegistry`. Built-in field IDs work out of the box via `FieldRegistry.createDefault()`, which `TokenGenerator` uses internally. To register custom field IDs — for example, when multiple person fields share the same underlying attribute type — see [FieldRegistry and Field IDs](token-registration.md#fieldregistry-and-field-ids).

## TokenDefinition

`TokenDefinition` encapsulates the built-in T1–T5 rule definitions.

```java
TokenDefinition tokenDefinition = new TokenDefinition();
```

## TokenGenerator

`TokenGenerator` validates/normalizes inputs and produces token signatures and tokens.

### Methods

| Method                                                 | Return Type            | Description                                                                               |
| ------------------------------------------------------ | ---------------------- | ----------------------------------------------------------------------------------------- |
| `getAllTokenSignaturesViaFieldId(Map<String, String>)` | `Map<String, String>`  | Generates signatures for all rules using a field-ID-keyed map (debug/logging)             |
| `getAllTokensViaFieldId(Map<String, String>)`          | `TokenGeneratorResult` | Generates tokens for all rules using a field-ID-keyed map and captures invalid/blank info |

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

TokenGeneratorResult result = generator.getAllTokensViaFieldId(personAttributes);
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
// Returns: Open Link Token encrypted match token string (olt.V1.<JWE compact serialization>)
```

## Complete Example

```java
import java.util.HashMap;
import java.util.List;
import java.util.Map;

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

        Map<String, String> personAttributes = new HashMap<>();
        personAttributes.put("FirstName", "John");
        personAttributes.put("LastName", "Doe");
        personAttributes.put("BirthDate", "1980-01-15");
        personAttributes.put("Sex", "Male");
        personAttributes.put("PostalCode", "98004");
        personAttributes.put("SocialSecurityNumber", "123-45-6789");

        List<TokenTransformer> transformers = List.of(
            new HashTokenTransformer("HashingSecret"),
            new EncryptTokenTransformer("Secret-Encryption-Key-Goes-Here.")
        );

        TokenGenerator generator = new TokenGenerator(
            new TokenDefinition(),
            new SHA256Tokenizer(transformers)
        );

        TokenGeneratorResult result = generator.getAllTokensViaFieldId(personAttributes);
        result.getTokens().forEach((ruleId, token) ->
            System.out.printf("%s,%s,%s%n", recordId, ruleId, token)
        );
    }
}
```

## Data Integration

The Java library focuses on in-memory token generation. It does not include CSV, Parquet, or other file I/O helper classes.

Use your application's reader or writer layer to map each record into `Map<String, String>` keyed by field ID, then pass that map to `TokenGenerator`.

```java
Map<String, String> personAttributes = new HashMap<>();
personAttributes.put("FirstName", row.get("FirstName"));
personAttributes.put("LastName", row.get("LastName"));
// ...populate the remaining fields needed for your token rules

TokenGeneratorResult result = generator.getAllTokensViaFieldId(personAttributes);
```

## Thread Safety

All transformer classes are thread-safe and can be shared across threads:

```java
// Token generation is safe to parallelize across independent records.
// For best clarity, create the per-record attribute map inside the task.
ExecutorService executor = Executors.newFixedThreadPool(4);
for (Map<String, String> personAttributes : persons) {
    executor.submit(() -> {
        TokenGeneratorResult result = generator.getAllTokensViaFieldId(personAttributes);
        // ...
    });
}
```

## Maven Dependency

```xml
<dependency>
    <groupId>org.openlinktoken</groupId>
    <artifactId>openlinktoken</artifactId>
    <version>2.1.0</version>
</dependency>
```

## Next Steps

- [Python API Reference](python-api.md) - Cross-language parity
- [Token Registration](token-registration.md) - Add custom tokens
- [CLI Reference](cli.md) - Command-line usage
