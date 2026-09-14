---
layout: default
---

# Python Quickstart

For a high-level overview and other entry points, see [Quickstarts](index.md).

Install the Python packages and run the Open Link Token CLI with a virtual environment.
After installation, use the `olt` command directly.

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

Run the following from any directory — the `olt` console script is installed into your virtualenv. The examples below assume you are in the project root (`/path/to/OpenLinkToken`) so the `./resources/...` paths work.

Create a local exchange config once before running the consumer commands:

```bash
# Simulate receiving the recipient's public key (in practice, your partner provides this)
olt generate-key-pair --name recipient
# Create the exchange config using the recipient's public key
olt initiate-exchange --public-key ~/.openlinktoken/recipient.public.pem
```

### Package Command (Tokenize + Encrypt)

By default, `package` writes a self-contained `<input>_packaged.zip` bundle (tokens + metadata + exchange config), ready to share. For valid records, the Python CLI includes T1–T5 plus one ML1 row by default; add `--disable-inferencing` for T1–T5 only. Pass `-o tokens.csv` if you want a plain CSV instead:

```bash
olt package -i ./resources/sample.csv -o tokens.csv
```

### Tokenize Command (HMAC hash, no encryption)

Produces deterministic HMAC-SHA256 tokens — useful for internal analysis when both sides hold the same exchange config.

```bash
olt tokenize -i ./resources/sample.csv -o tokens.csv
```

### Parquet Format

```bash
olt package -i input.parquet -o tokens.parquet
```

### Decrypt Command

```bash
olt decrypt -i tokens.csv -o decrypted.csv
```

### Generate ECDH Key Pair

```bash
olt generate-key-pair --curve P-256 --name my-key
```

This writes `~/.openlinktoken/my-key.private.pem` and `~/.openlinktoken/my-key.public.pem`. Add `--force` to overwrite existing files.

## Getting Help

```bash
# Show all available commands
olt --help

# Show help for specific command
olt help package
olt package --help
```

If the `olt` console script is unavailable, use the equivalent module form:

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
from openlinktoken.tokens.token_definition import TokenDefinition
from openlinktoken.tokens.token_generator import TokenGenerator
from openlinktoken.tokens.tokenizer.sha256_tokenizer import SHA256Tokenizer
from openlinktoken.tokentransformer.encrypt_token_transformer import EncryptTokenTransformer
from openlinktoken.tokentransformer.hash_token_transformer import HashTokenTransformer

record_id = "patient_123"

person_attributes = {
  "FirstName": "John",
  "LastName": "Doe",
  "BirthDate": "1980-01-15",
  "Sex": "Male",
  "PostalCode": "98004",
  "SocialSecurityNumber": "123-45-6789",
}

token_definition = TokenDefinition()
tokenizer = SHA256Tokenizer([
  HashTokenTransformer("HashingSecret"),
  EncryptTokenTransformer("0123456789abcdef0123456789abcdef"),
])

generator = TokenGenerator(token_definition, tokenizer)
result = generator.get_all_tokens_via_field_id(person_attributes)
if result.invalid_attributes:
  print(f"Invalid attributes: {sorted(result.invalid_attributes)}")

for rule_id, token in result.tokens.items():
  print(f"{record_id},{rule_id},{token}")
```

The direct library transformer returns a base64-encoded AES-GCM payload. The
CLI `package` workflow applies the `olt.V1.<JWE>` wrapper to encrypted package
output.

## Cross-Language Parity

Open Link Token guarantees that Java and Python produce **identical tokens** for the same input. This is verified by interoperability tests:

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

Open Link Token requires Python 3.10+. Check with `python --version`.

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

### "olt: command not found"

The console script is installed into the active environment. Re-activate your venv and reinstall the CLI package:

```bash
cd /path/to/OpenLinkToken
source .venv/bin/activate
cd lib/python/openlinktoken-cli
uv pip install -e .
```

## Development Setup

For contributing to Open Link Token:

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
