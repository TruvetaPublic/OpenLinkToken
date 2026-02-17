---
layout: default
---

# Java Quickstart

For a high-level overview and other entry points, see [Quickstarts](index.md).

Build and run the Java CLI to generate OpenToken outputs from local files.

## Prerequisites

- **Java 21+** (OpenJDK or Oracle JDK)
- **Maven 3.8+**

Verify your installation:

```bash
java -version   # Should show 21 or higher
mvn -version    # Should show 3.8 or higher
```

## Build the CLI

```bash
# Clone and navigate to the repository
cd /path/to/OpenToken/lib/java

# Build both opentoken core and CLI modules
mvn clean install

# The CLI JAR is at:
# opentoken-cli/target/opentoken-cli-*.jar
```

### Skip Tests (Faster Build)

```bash
mvn clean install -DskipTests
```

## Run Token Generation

### Basic Encrypted Tokens

```bash
java -jar opentoken-cli/target/opentoken-cli-*.jar \
  -i ../../resources/sample.csv \
  -t csv \
  -o ../../resources/output.csv \
  -h "YourHashingSecret" \
  -e "YourEncryptionKey-32Chars-Here!"
```

### Hash-Only Mode (No Encryption)

```bash
java -jar opentoken-cli/target/opentoken-cli-*.jar \
  -i ../../resources/sample.csv \
  -t csv \
  -o ../../resources/output.csv \
  -h "YourHashingSecret" \
  --hash-only
```

### Parquet Format

```bash
java -jar opentoken-cli/target/opentoken-cli-*.jar \
  -i input.parquet \
  -t parquet \
  -o output.parquet \
  -h "YourHashingSecret" \
  -e "YourEncryptionKey-32Chars-Here!"
```

## Verify Output

```bash
# View token output
head ../../resources/output.csv

# View metadata
cat ../../resources/output.metadata.json
```

**Expected output.csv:**

```csv
RecordId,RuleId,Token
id1,T1,Gn7t1Zj16E5Qy+z9iINtczP6fRDYta6C0XFr...
id1,T2,pUxPgYL9+cMxkA+8928Pil+9W+dm9kISwHYP...
id1,T3,rwjfwIo5OcJUItTx8KCoSZMtr7tVGSyXsWv/...
id1,T4,9o7HIYZkhizczFzJL1HFyanlllzSa8hlgQWQ...
id1,T5,QpBpGBqaMhagfcHGZhVavn23ko03jkyS9Vo4...
```

## Using the Java API Programmatically

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

## Maven Dependency

To use OpenToken in your Java project:

```xml
<dependency>
    <groupId>com.truveta</groupId>
    <artifactId>opentoken</artifactId>
    <version>2.0.0-alpha</version>
</dependency>
```

## Troubleshooting

### "UnsupportedClassVersionError"

You need Java 21+. Check with `java -version`.

### "Could not find artifact"

Run `mvn clean install` from `lib/java` to build the local modules.

### Build Fails with Checkstyle Errors

Run `mvn checkstyle:check` to see specific style violations, then fix them.

### OutOfMemoryError

For large files, increase heap size:

```bash
java -Xmx4g -jar opentoken-cli-*.jar ...
```

## Next Steps

- [Python Quickstart](python-quickstart.md) - Cross-language parity
- [CLI Reference](../reference/cli.md) - All command options
- [Java API Reference](../reference/java-api.md) - Programmatic usage
