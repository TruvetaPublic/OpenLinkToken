---
layout: default
---

# Python API Reference

Document the Python modules and functions for programmatic token generation.

## Core Modules

```python
from opentoken.attributes.person.birth_date_attribute import BirthDateAttribute
from opentoken.attributes.person.first_name_attribute import FirstNameAttribute
from opentoken.attributes.person.last_name_attribute import LastNameAttribute
from opentoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from opentoken.attributes.person.sex_attribute import SexAttribute
from opentoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
from opentoken.tokens.token_definition import TokenDefinition
from opentoken.tokens.token_generator import TokenGenerator
from opentoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from opentoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from opentoken.tokentransformer.hash_token_transformer import HashTokenTransformer
```

## Person Attribute Dict

OpenToken's Python library represents a person's values as a dict keyed by attribute class:

```python
person_attributes = {
    FirstNameAttribute: "John",
    LastNameAttribute: "Doe",
    BirthDateAttribute: "1980-01-15",
    SexAttribute: "Male",
    PostalCodeAttribute: "98004",
    SocialSecurityNumberAttribute: "123-45-6789",
}
```

Normalization and validation are handled internally by `TokenGenerator` using the attribute implementations loaded via `AttributeLoader`.

## TokenDefinition

`TokenDefinition` encapsulates the built-in T1–T5 rule definitions.

```python
token_definition = TokenDefinition()
```

## TokenGenerator

`TokenGenerator` validates/normalizes inputs and produces token signatures and tokens.

### Methods

| Method                                             | Return Type            | Description                                                    |
| -------------------------------------------------- | ---------------------- | -------------------------------------------------------------- |
| `get_all_token_signatures(person_attributes)`      | `Dict[str, str]`       | Generates signatures for all rules (debug/logging)             |
| `get_all_tokens(person_attributes)`                | `TokenGeneratorResult` | Generates tokens for all rules and captures invalid/blank info |
| `get_invalid_person_attributes(person_attributes)` | `Set[str]`             | Validates all provided attribute values                        |

### Example

```python
tokenizer = SHA256Tokenizer([
    HashTokenTransformer("HashingSecret"),
    EncryptTokenTransformer("Secret-Encryption-Key-Goes-Here."),
])

generator = TokenGenerator(TokenDefinition(), tokenizer)

invalid = generator.get_invalid_person_attributes(person_attributes)
if invalid:
    print(f"Invalid attributes: {sorted(invalid)}")

result = generator.get_all_tokens(person_attributes)
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
# Returns: OpenToken encrypted match token string (ot.V1.<JWE compact serialization>)
```

## Complete Example

```python
from opentoken.attributes.person.birth_date_attribute import BirthDateAttribute
from opentoken.attributes.person.first_name_attribute import FirstNameAttribute
from opentoken.attributes.person.last_name_attribute import LastNameAttribute
from opentoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from opentoken.attributes.person.sex_attribute import SexAttribute
from opentoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
from opentoken.tokens.token_definition import TokenDefinition
from opentoken.tokens.token_generator import TokenGenerator
from opentoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from opentoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from opentoken.tokentransformer.hash_token_transformer import HashTokenTransformer

def generate_tokens():
    record_id = "patient_001"

    person_attributes = {
        FirstNameAttribute: "John",
        LastNameAttribute: "Doe",
        BirthDateAttribute: "1980-01-15",
        SexAttribute: "Male",
        PostalCodeAttribute: "98004",
        SocialSecurityNumberAttribute: "123-45-6789",
    }

    tokenizer = SHA256Tokenizer([
        HashTokenTransformer("HashingSecret"),
        EncryptTokenTransformer("Secret-Encryption-Key-Goes-Here."),
    ])
    generator = TokenGenerator(TokenDefinition(), tokenizer)

    invalid = generator.get_invalid_person_attributes(person_attributes)
    if invalid:
        print(f"Invalid attributes: {sorted(invalid)}")
        return

    result = generator.get_all_tokens(person_attributes)
    for rule_id, token in result.tokens.items():
        print(f"{record_id},{rule_id},{token}")

if __name__ == "__main__":
    generate_tokens()
```

## Batch Processing

For processing multiple records:

```python
import csv
from opentoken.attributes.person.birth_date_attribute import BirthDateAttribute
from opentoken.attributes.person.first_name_attribute import FirstNameAttribute
from opentoken.attributes.person.last_name_attribute import LastNameAttribute
from opentoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from opentoken.attributes.person.sex_attribute import SexAttribute
from opentoken.attributes.person.social_security_number_attribute import SocialSecurityNumberAttribute
from opentoken.tokens.token_definition import TokenDefinition
from opentoken.tokens.token_generator import TokenGenerator
from opentoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from opentoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from opentoken.tokentransformer.hash_token_transformer import HashTokenTransformer

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
                FirstNameAttribute: row.get('FirstName', ''),
                LastNameAttribute: row.get('LastName', ''),
                BirthDateAttribute: row.get('BirthDate', ''),
                SexAttribute: row.get('Sex', ''),
                PostalCodeAttribute: row.get('PostalCode', ''),
                SocialSecurityNumberAttribute: row.get('SSN', ''),
            }

            invalid = generator.get_invalid_person_attributes(person_attributes)
            if invalid:
                continue

            result = generator.get_all_tokens(person_attributes)
            for rule_id, token in result.tokens.items():
                writer.writerow([record_id, rule_id, token])
```

## PySpark Integration

For distributed processing on Spark, use the `opentoken_pyspark` bridge:

```python
from opentoken_pyspark import OpenTokenProcessor

processor = OpenTokenProcessor(
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
from opentoken_pyspark import OpenTokenOverlapAnalyzer

analyzer = OpenTokenOverlapAnalyzer("EncryptionKey-32Characters-Here")
results = analyzer.analyze_overlap(tokens_df1, tokens_df2, ["T1", "T2"])
analyzer.print_summary(results)
```

See [Spark or Databricks](../operations/spark-or-databricks.md) for end-to-end PySpark examples.

## Cross-Language Parity

OpenToken guarantees identical output between Java and Python:

```python
# This Python code produces the exact same tokens as equivalent Java code
person_attributes = {
    FirstNameAttribute: "John",
    LastNameAttribute: "Doe",
    BirthDateAttribute: "1980-01-15",
    SexAttribute: "Male",
    PostalCodeAttribute: "98004",
    SocialSecurityNumberAttribute: "123-45-6789",
}
```

Verify parity with:
```bash
cd tools/interoperability
python java_python_interoperability_test.py
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
        FirstNameAttribute: "",  # Empty - will be invalid
        LastNameAttribute: "Doe",
        BirthDateAttribute: "invalid-date",  # Bad format
        SexAttribute: "Unknown",  # Not Male/Female
        PostalCodeAttribute: "98004",
        SocialSecurityNumberAttribute: "123-45-6789",
    }

    invalid = generator.get_invalid_person_attributes(person_attributes)
    if invalid:
        raise ValueError(f"Invalid attributes: {sorted(invalid)}")
        
except ValueError as e:
    print(f"Validation error: {e}")
```

## Installation

```bash
# From repository
cd lib/python/opentoken
pip install -e .

# Development dependencies
pip install -r dev-requirements.txt
```

## Next Steps

- [Java API Reference](java-api.md) - Cross-language reference
- [Token Registration](token-registration.md) - Add custom tokens
- [CLI Reference](cli.md) - Command-line usage
- [Spark Integration](../operations/spark-or-databricks.md) - Distributed processing
