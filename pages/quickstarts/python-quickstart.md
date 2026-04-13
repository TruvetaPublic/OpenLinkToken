---
layout: default
---

# Python Quickstart

For a high-level overview and other entry points, see [Quickstarts](index.md).

Install the Python packages and run the OpenLinkToken CLI with a virtual environment.
After installation, use the `openlinktoken` command directly.

## Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** (fast Python package manager)

Install uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify your installation:

```bash
python --version   # Should show 3.10 or higher
uv --version
```

## Setup Virtual Environment

**Important:** The virtual environment should be created at the repository root.

```bash
cd /path/to/OpenLinkToken

# Create virtual environment at repo root
uv venv .venv

# Activate (Linux/Mac)
source .venv/bin/activate

# Activate (Windows)
.\.venv\Scripts\activate
```

## Install Dependencies

```bash
# Install core library
cd lib/python/openlinktoken
uv pip install -r requirements.txt -e .

# Install CLI
cd ../openlinktoken-cli
uv pip install -r requirements.txt -e .
```

## Run Token Generation

### Package Command (Tokenize + Encrypt)

```bash
openlinktoken package \
  -i ../../../resources/sample.csv \
  -t csv \
  -o ../../../resources/output.csv \
  -h "YourHashingSecret" \
  -e "YourEncryptionKey-32Chars-Here!"
```

### Tokenize Command (Hash-Only, No Encryption)

```bash
openlinktoken tokenize \
  -i ../../../resources/sample.csv \
  -t csv \
  -o ../../../resources/output.csv \
  -h "YourHashingSecret"
```

### Parquet Format

```bash
openlinktoken package \
  -i input.parquet \
  -t parquet \
  -o output.parquet \
  -h "YourHashingSecret" \
  -e "YourEncryptionKey-32Chars-Here!"
```

### Decrypt Command

```bash
openlinktoken decrypt \
  -i ../../../resources/output.csv \
  -t csv \
  -o ../../../resources/decrypted.csv \
  -e "YourEncryptionKey-32Chars-Here!"
```

### Generate ECDH Key Pair

```bash
openlinktoken generate-key-pair \
  --curve P-256 \
  --name my-key
```

This writes `~/.openlinktoken/my-key.private.pem` and `~/.openlinktoken/my-key.public.pem`. Add `--force` to overwrite
existing files.

## Getting Help

```bash
# Show all available commands
openlinktoken --help

# Show help for specific command
openlinktoken help package
openlinktoken package --help
```

If needed, you can still run the module form directly:

```bash
python -m openlinktoken_cli.main --help
```

## Verify Output

```bash
# View token output
head ../../../resources/output.csv

# View metadata
cat ../../../resources/output.metadata.json
```

## Using the Python API Programmatically

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

record_id = "patient_123"

person_attributes = {
  FirstNameAttribute: "John",
  LastNameAttribute: "Doe",
  BirthDateAttribute: "1980-01-15",
  SexAttribute: "Male",
  PostalCodeAttribute: "98004",
  SocialSecurityNumberAttribute: "123-45-6789",
}

token_definition = TokenDefinition()
tokenizer = SHA256Tokenizer([
  HashTokenTransformer("HashingSecret"),
  EncryptTokenTransformer("Secret-Encryption-Key-Goes-Here."),
])

generator = TokenGenerator(token_definition, tokenizer)
result = generator.get_all_tokens(person_attributes)
if result.invalid_attributes:
  print(f"Invalid attributes: {sorted(result.invalid_attributes)}")

for rule_id, token in result.tokens.items():
  print(f"{record_id},{rule_id},{token}")
```

## Cross-Language Parity

OpenLinkToken guarantees that Java and Python produce **identical tokens** for the same input. This is verified by interoperability tests:

```bash
cd tools/interoperability
uv pip install -r requirements.txt
python multi_language_interoperability_test.py
```

The test:

1. Generates tokens using the Java core library
2. Generates tokens using Python CLI
3. Compares all tokens byte-by-byte
4. Fails if any mismatch is found

## PySpark Integration

For distributed processing on Spark or Databricks:

```bash
cd lib/python/openlinktoken-pyspark
uv pip install -r requirements.txt -e .
```

See [Spark or Databricks](../operations/spark-or-databricks.md) for usage.

## Troubleshooting

### "ModuleNotFoundError: No module named 'openlinktoken'"

Make sure you installed with `-e .` (editable mode) from the correct directory.

### "Python version not supported"

OpenLinkToken requires Python 3.10+. Check with `python --version`.

### Virtual Environment Not Activated

If commands fail, ensure venv is active:

```bash
cd /path/to/OpenLinkToken
source .venv/bin/activate
```

### Import Errors After Updates

Reinstall the packages:

```bash
uv pip install -e . --reinstall
```

### "openlinktoken: command not found"

The console script is installed into the active environment. Re-activate your venv and reinstall the CLI package:

```bash
cd /path/to/OpenLinkToken
source .venv/bin/activate
cd lib/python/openlinktoken-cli
uv pip install -e .
```

## Development Setup

For contributing to OpenLinkToken:

```bash
# Install development dependencies
uv pip install -r dev-requirements.txt

# Run tests
pytest

# Run with coverage
pytest --cov=openlinktoken --cov-report=html
```

## Next Steps

- [Java Quickstart](java-quickstart.md) - Cross-language reference
- [CLI Reference](../reference/cli.md) - All command options
- [Python API Reference](../reference/python-api.md) - Programmatic usage
- [Spark Integration](../operations/spark-or-databricks.md) - Distributed processing
