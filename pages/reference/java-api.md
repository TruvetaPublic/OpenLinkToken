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

import com.truveta.opentoken.attributes.Attribute;
import com.truveta.opentoken.attributes.person.BirthDateAttribute;
import com.truveta.opentoken.attributes.person.FirstNameAttribute;
import com.truveta.opentoken.attributes.person.LastNameAttribute;
import com.truveta.opentoken.attributes.person.PostalCodeAttribute;
import com.truveta.opentoken.attributes.person.SexAttribute;
import com.truveta.opentoken.attributes.person.SocialSecurityNumberAttribute;
import com.truveta.opentoken.tokens.TokenDefinition;
import com.truveta.opentoken.tokens.TokenGenerator;
import com.truveta.opentoken.tokens.TokenGeneratorResult;
import com.truveta.opentoken.tokens.tokenizer.SHA256Tokenizer;
import com.truveta.opentoken.tokentransformer.EncryptTokenTransformer;
import com.truveta.opentoken.tokentransformer.HashTokenTransformer;
import com.truveta.opentoken.tokentransformer.TokenTransformer;
```

## Person Attribute Map

OpenToken's Java library represents a person's values as a map keyed by attribute class:

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
// Returns: Base64-encoded encrypted token
```

## Complete Example

```java
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.truveta.opentoken.attributes.Attribute;
import com.truveta.opentoken.attributes.person.BirthDateAttribute;
import com.truveta.opentoken.attributes.person.FirstNameAttribute;
import com.truveta.opentoken.attributes.person.LastNameAttribute;
import com.truveta.opentoken.attributes.person.PostalCodeAttribute;
import com.truveta.opentoken.attributes.person.SexAttribute;
import com.truveta.opentoken.attributes.person.SocialSecurityNumberAttribute;
import com.truveta.opentoken.tokens.TokenDefinition;
import com.truveta.opentoken.tokens.TokenGenerator;
import com.truveta.opentoken.tokens.TokenGeneratorResult;
import com.truveta.opentoken.tokens.tokenizer.SHA256Tokenizer;
import com.truveta.opentoken.tokentransformer.EncryptTokenTransformer;
import com.truveta.opentoken.tokentransformer.HashTokenTransformer;
import com.truveta.opentoken.tokentransformer.TokenTransformer;

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

## I/O Classes (CLI Module)

For file processing, use classes from the CLI module:

```java
import java.util.Map;

import com.truveta.opentoken.attributes.Attribute;
import com.truveta.opentoken.cli.io.PersonAttributesReader;
import com.truveta.opentoken.cli.io.PersonAttributesWriter;
import com.truveta.opentoken.cli.io.csv.PersonAttributesCSVReader;
import com.truveta.opentoken.cli.io.csv.PersonAttributesCSVWriter;
import com.truveta.opentoken.cli.io.parquet.PersonAttributesParquetReader;
import com.truveta.opentoken.cli.io.parquet.PersonAttributesParquetWriter;
```

### CSV Example

```java
try (PersonAttributesReader reader = new PersonAttributesCSVReader("input.csv")) {
    while (reader.hasNext()) {
        Map<Class<? extends Attribute>, String> person = reader.next();
        // Process person...
    }
}
```

### Writing Output Rows

```java
try (PersonAttributesWriter writer = new PersonAttributesCSVWriter("output.csv")) {
    writer.writeAttributes(Map.of(
        "RecordId", "patient_001",
        "RuleId", "T1",
        "Token", "..."
    ));
}
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
    <groupId>com.truveta</groupId>
    <artifactId>opentoken</artifactId>
    <version>2.0.0-alpha</version>
</dependency>

<!-- For CLI/IO classes -->
<dependency>
    <groupId>com.truveta</groupId>
    <artifactId>opentoken-cli</artifactId>
    <version>2.0.0-alpha</version>
</dependency>
```

## Next Steps

- [Python API Reference](python-api.md) - Cross-language parity
- [Token Registration](token-registration.md) - Add custom tokens
- [CLI Reference](cli.md) - Command-line usage
