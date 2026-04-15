---
layout: default
---

# Reference: API Overview

Open Link Token provides three interfaces for generating privacy-preserving tokens: a Java library, a Python library, and a command-line interface (CLI). All three produce identical tokens for the same input, enabling cross-language and cross-platform workflows.

---

## Choosing the Right Interface

| Interface      | Best for                                                                    | Example use case                                                         |
| -------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **Java API**   | JVM-based pipelines, enterprise integrations, high-throughput batch jobs    | Embedding token generation in a Spring or Spark (Scala/Java) application |
| **Python API** | Python data workflows, PySpark, Databricks notebooks, rapid prototyping     | Tokenizing DataFrames in a Jupyter notebook or Databricks cluster        |
| **CLI**        | One-off batch processing, scripted pipelines, CI/CD jobs, Docker containers | Processing CSV/Parquet files from a shell script or scheduled job        |

---

## Java Library API

The Java API integrates directly into JVM applications.

**Key classes:**

- `TokenDefinition` — Loads the built-in T1–T5 rule definitions
- `TokenGenerator` — Validates/normalizes attribute values and generates tokens
- `SHA256Tokenizer` — Applies the SHA-256 digest step before transformations
- `HashTokenTransformer` / `EncryptTokenTransformer` — Optional post-processing (HMAC and/or AES-GCM)

**Quick example:**

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

List<TokenTransformer> transformers = List.of(
  new HashTokenTransformer(hashingSecret),
  new EncryptTokenTransformer(encryptionKey)
);

TokenGenerator tokenGenerator = new TokenGenerator(
  new TokenDefinition(),
  new SHA256Tokenizer(transformers)
);

Map<Class<? extends Attribute>, String> personAttributes = new HashMap<>();
personAttributes.put(FirstNameAttribute.class, "Elena");
personAttributes.put(LastNameAttribute.class, "Vasquez");
personAttributes.put(BirthDateAttribute.class, "1992-07-14");
personAttributes.put(SexAttribute.class, "Female");
personAttributes.put(PostalCodeAttribute.class, "30301");
personAttributes.put(SocialSecurityNumberAttribute.class, "452-38-7291");

TokenGeneratorResult result = tokenGenerator.getAllTokens(personAttributes);
result.getTokens().forEach((ruleId, token) -> System.out.println(ruleId + ": " + token));
```

**Full reference:** [Java API Reference](java-api.md)

---

## Python Library API

The Python API mirrors the Java API for cross-language parity.

**Key classes:**

- `TokenDefinition` — Loads the built-in T1–T5 rule definitions
- `TokenGenerator` — Validates/normalizes attribute values and generates tokens
- `SHA256Tokenizer` — Applies the SHA-256 digest step before transformations
- `HashTokenTransformer` / `EncryptTokenTransformer` — Optional post-processing (HMAC and/or AES-GCM)

**Quick example:**

```python
from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from openlinktoken.attributes.person.sex_attribute import SexAttribute
from openlinktoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
from openlinktoken.tokens.token_definition import TokenDefinition
from openlinktoken.tokens.token_generator import TokenGenerator
from openlinktoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from openlinktoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer

token_definition = TokenDefinition()
tokenizer = SHA256Tokenizer([
  HashTokenTransformer(hashing_secret),
  EncryptTokenTransformer(encryption_key),
])
token_generator = TokenGenerator(token_definition, tokenizer)

person_attributes = {
  FirstNameAttribute: "Elena",
  LastNameAttribute: "Vasquez",
  BirthDateAttribute: "1992-07-14",
  SexAttribute: "Female",
  PostalCodeAttribute: "30301",
  SocialSecurityNumberAttribute: "452-38-7291",
}

result = token_generator.get_all_tokens(person_attributes)
for rule_id, token in result.tokens.items():
  print(f"{rule_id}: {token}")
```

**Full reference:** [Python API Reference](python-api.md)

---

## Command-Line Interface (CLI)

The CLI processes CSV or Parquet files without writing code.

**Basic usage:**

```bash
olt package \
  -i input.csv -t csv -o output.csv \
  -h "HashingSecret" -e "EncryptionKey32Chars!!!!!!!!!!"
```

Or with Python:

```bash
python -m openlinktoken_cli.main package \
  -i input.csv -t csv -o output.csv \
  -h "HashingSecret" -e "EncryptionKey32Chars!!!!!!!!!!"
```

**Key options:**

| Flag                     | Purpose                        |
| ------------------------ | ------------------------------ |
| `-i` / `--input`         | Input file path                |
| `-o` / `--output`        | Output file path               |
| `-t` / `--type`          | File type (`csv` or `parquet`) |
| `-h` / `--hashingsecret` | HMAC-SHA256 secret             |
| `-e` / `--encryptionkey` | AES-256 key (32 chars)         |
| `tokenize`               | Tokenize without encryption    |

**Full reference:** [CLI Reference](cli.md)

---

## Metadata Output

Every token generation run produces a `.metadata.json` file alongside the token output. This file contains:

- Processing statistics (total rows, invalid records)
- SHA-256 hashes of secrets (for verification, not the secrets themselves)
- Timestamp and platform information

**Full reference:** [Metadata Format](metadata-format.md)

---

## Custom Token Registration

Open Link Token supports defining custom token rules beyond T1–T5. Custom rules can include additional attributes (e.g., MRN) or different attribute combinations.

**Full reference:** [Token Registration](token-registration.md)

---

## Additional Reference Pages

- [Java API Reference](java-api.md) — Complete Java class and method documentation
- [Python API Reference](python-api.md) — Complete Python class and method documentation
- [CLI Reference](cli.md) — All CLI flags, modes, and examples
- [Metadata Format](metadata-format.md) — Metadata file schema and fields
- [Token Registration](token-registration.md) — Adding custom token rules
- [Extension Author Reference](extensions.md) — Building CLI extensions: ABC contract, entry points, security model, and binary compatibility

---

## Related Documentation

- [Quickstarts](../quickstarts/index.md) — Get started in 5 minutes
- [Concepts: Token Rules](../concepts/token-rules.md) — How T1–T5 are composed
- [Concepts: Normalization](../concepts/normalization-and-validation.md) — Attribute standardization
- [Configuration](../config/configuration.md) — Environment variables and input formats
- [Security](../security.md) — Cryptographic details and key management
