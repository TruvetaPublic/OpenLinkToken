---
layout: default
---

# Python API Reference

Document the Python modules and functions for programmatic token generation.

## Core Modules

```python
from openlinktoken.tokens.token_definition import TokenDefinition
from openlinktoken.tokens.token_generator import TokenGenerator
from openlinktoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from openlinktoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer
```

## Person Attribute Dict

Open Link Token's Python library represents a person's values as a dict keyed by field ID:

```python
person_attributes = {
    "FirstName": "John",
    "LastName": "Doe",
    "BirthDate": "1980-01-15",
    "Sex": "Male",
    "PostalCode": "98004",
    "SocialSecurityNumber": "123-45-6789",
}
```

Field IDs like `"FirstName"` and `"LastName"` are resolved to attribute behavior (normalization and validation) through `FieldRegistry`. Built-in field IDs work out of the box via `FieldRegistry.create_default()`, which `TokenGenerator` uses internally. To register custom field IDs — for example, when multiple person fields share the same underlying attribute type — see [FieldRegistry and Field IDs](token-registration.md#fieldregistry-and-field-ids-1).

## TokenDefinition

`TokenDefinition` encapsulates the built-in T1–T5 rule definitions.

```python
token_definition = TokenDefinition()
```

## TokenGenerator

`TokenGenerator` validates/normalizes inputs and produces token signatures and tokens.

### Methods

| Method                                                     | Return Type            | Description                                                                                |
| ---------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------ |
| `get_all_token_signatures_via_field_id(person_attributes)` | `Dict[str, str]`       | Generates signatures for all rules using a field-ID-keyed dict (debug/logging)             |
| `get_all_tokens_via_field_id(person_attributes)`           | `TokenGeneratorResult` | Generates tokens for all rules using a field-ID-keyed dict and captures invalid/blank info |

### Example

```python
tokenizer = SHA256Tokenizer([
    HashTokenTransformer("HashingSecret"),
    EncryptTokenTransformer("Secret-Encryption-Key-Goes-Here."),
])

generator = TokenGenerator(TokenDefinition(), tokenizer)

result = generator.get_all_tokens_via_field_id(person_attributes)
for rule_id, token in result.tokens.items():
    print(f"{rule_id}: {token}")
```

## Token Transformers

Transform token signatures into encrypted or hashed tokens.

### HashTokenTransformer

One-way hashing without encryption.

```python
hasher = HashTokenTransformer("YourHashingSecret")

signature = "DOE|J|MALE|1980-01-15"
hashed_token = hasher.transform(signature)
# Returns: Base64-encoded HMAC-SHA256 hash
```

### EncryptTokenTransformer

Full encryption with AES-256-GCM.

```python
encryptor = EncryptTokenTransformer(
    encryption_key="Secret-Encryption-Key-Goes-Here."  # Exactly 32 chars
)

signature = "DOE|J|MALE|1980-01-15"
encrypted_token = encryptor.transform(signature)
# Returns: Open Link Token encrypted match token string (olt.V1.<JWE compact serialization>)
```

## Complete Example

```python
from openlinktoken.tokens.token_definition import TokenDefinition
from openlinktoken.tokens.token_generator import TokenGenerator
from openlinktoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from openlinktoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer

def generate_tokens():
    record_id = "patient_001"

    person_attributes = {
        "FirstName": "John",
        "LastName": "Doe",
        "BirthDate": "1980-01-15",
        "Sex": "Male",
        "PostalCode": "98004",
        "SocialSecurityNumber": "123-45-6789",
    }

    tokenizer = SHA256Tokenizer([
        HashTokenTransformer("HashingSecret"),
        EncryptTokenTransformer("Secret-Encryption-Key-Goes-Here."),
    ])
    generator = TokenGenerator(TokenDefinition(), tokenizer)

    result = generator.get_all_tokens_via_field_id(person_attributes)
    for rule_id, token in result.tokens.items():
        print(f"{record_id},{rule_id},{token}")

if __name__ == "__main__":
    generate_tokens()
```

## Batch Processing

For processing multiple records:

```python
import csv
from openlinktoken.tokens.token_definition import TokenDefinition
from openlinktoken.tokens.token_generator import TokenGenerator
from openlinktoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from openlinktoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer

def process_csv(input_path, output_path, hashing_secret, encryption_key):
    tokenizer = SHA256Tokenizer([
        HashTokenTransformer(hashing_secret),
        EncryptTokenTransformer(encryption_key),
    ])
    generator = TokenGenerator(TokenDefinition(), tokenizer)

    with open(input_path, 'r') as infile, open(output_path, 'w', newline='') as outfile:
        reader = csv.DictReader(infile)
        writer = csv.writer(outfile)
        writer.writerow(['RecordId', 'RuleId', 'Token'])

        for row in reader:
            record_id = row.get('RecordId', '')

            person_attributes = {
                "FirstName": row.get('FirstName', ''),
                "LastName": row.get('LastName', ''),
                "BirthDate": row.get('BirthDate', ''),
                "Sex": row.get('Sex', ''),
                "PostalCode": row.get('PostalCode', ''),
                "SocialSecurityNumber": row.get('SSN', ''),
            }

            result = generator.get_all_tokens_via_field_id(person_attributes)
            for rule_id, token in result.tokens.items():
                writer.writerow([record_id, rule_id, token])
```

## PySpark Integration

For distributed processing on Spark, use the `openlinktoken_pyspark` bridge:

```python
from openlinktoken_pyspark import OpenLinkTokenProcessor

processor = OpenLinkTokenProcessor(
    hashing_secret="HashingSecret",
    encryption_key="EncryptionKey-32Characters-Here",
)

# df must include the standard person columns (or aliases), e.g.:
# RecordId, FirstName, LastName, BirthDate, Sex, PostalCode, SSN
df_tokens = processor.process_dataframe(df)

df_tokens.show()
```

For overlap analysis between two tokenized datasets, use:

```python
from openlinktoken_pyspark import OpenLinkTokenOverlapAnalyzer

analyzer = OpenLinkTokenOverlapAnalyzer("EncryptionKey-32Characters-Here")
results = analyzer.analyze_overlap(tokens_df1, tokens_df2, ["T1", "T2"])
analyzer.print_summary(results)
```

See [Spark or Databricks](../operations/spark-or-databricks.md) for end-to-end PySpark examples.

## Cross-Language Parity

Open Link Token guarantees identical output between Java and Python:

```python
# This Python code produces the exact same tokens as equivalent Java code
person_attributes = {
    "FirstName": "John",
    "LastName": "Doe",
    "BirthDate": "1980-01-15",
    "Sex": "Male",
    "PostalCode": "98004",
    "SocialSecurityNumber": "123-45-6789",
}
```

Verify parity with:

```bash
cd tools/interoperability
python multi_language_interoperability_test.py
```

## Error Handling

```python
try:
    tokenizer = SHA256Tokenizer([
        HashTokenTransformer("HashingSecret"),
        EncryptTokenTransformer("Secret-Encryption-Key-Goes-Here."),
    ])
    generator = TokenGenerator(TokenDefinition(), tokenizer)

    person_attributes = {
        "FirstName": "",  # Empty - will be invalid
        "LastName": "Doe",
        "BirthDate": "invalid-date",  # Bad format
        "Sex": "Unknown",  # Not Male/Female
        "PostalCode": "98004",
        "SocialSecurityNumber": "123-45-6789",
    }

    result = generator.get_all_tokens_via_field_id(person_attributes)
    if result.invalid_attributes:
        raise ValueError(f"Invalid attributes: {sorted(result.invalid_attributes)}")

except ValueError as e:
    print(f"Validation error: {e}")
```

## Installation

```bash
# From repository
cd lib/python/openlinktoken
uv pip install -e .

# Development dependencies
uv pip install -r dev-requirements.txt
```

## Next Steps

- [Java API Reference](java-api.md) - Cross-language reference
- [Token Registration](token-registration.md) - Add custom tokens
- [CLI Reference](cli.md) - Command-line usage
- [Spark Integration](../operations/spark-or-databricks.md) - Distributed processing
