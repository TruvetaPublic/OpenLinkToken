---
layout: default
---

# Java Quickstart

For a high-level overview and other entry points, see [Quickstarts](index.md).

Use the OpenToken Java library to generate tokens programmatically from your Java application.

## Prerequisites

- **Java 21+** (OpenJDK or Oracle JDK)
- **Maven 3.8+**

Verify your installation:

```bash
java -version   # Should show 21 or higher
mvn -version    # Should show 3.8 or higher
```

## Maven Dependency

Add the OpenToken library to your project's `pom.xml`:

```xml
<dependency>
    <groupId>com.truveta</groupId>
    <artifactId>opentoken</artifactId>
    <version>2.0.0-alpha</version>
</dependency>
```

## Using the Java API Programmatically

The example below shows how to tokenize a single person record — normalizing attributes, hashing them, and optionally encrypting the resulting tokens.

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

String recordId = "patient_123";

// Person attributes are represented as a map keyed by Attribute class.
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

TokenGeneratorResult result = generator.getAllTokens(personAttributes);
if (!result.getInvalidAttributes().isEmpty()) {
  System.out.println("Invalid attributes: " + result.getInvalidAttributes());
}

result.getTokens().forEach((ruleId, token) ->
  System.out.println(recordId + "," + ruleId + "," + token)
);
```

### Hash-Only (No Encryption)

To tokenize without encryption, omit `EncryptTokenTransformer` from the transformer list:

```java
List<TokenTransformer> transformers = List.of(
  new HashTokenTransformer("HashingSecret")
);
```

## Troubleshooting

### "UnsupportedClassVersionError"

You need Java 21+. Check with `java -version`.

### "Could not find artifact"

Run `mvn clean install` from `lib/java` to build the local modules.

### Build Fails with Checkstyle Errors

Run `mvn checkstyle:check` to see specific style violations, then fix them.

## Next Steps

- [Python Quickstart](python-quickstart.md) - Generate tokens using the Python CLI
- [CLI Reference](../reference/cli.md) - All command options for the Python CLI
- [Java API Reference](../reference/java-api.md) - Full Java API documentation
