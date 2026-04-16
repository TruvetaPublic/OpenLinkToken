# Open Link Token PySpark Bridge

A PySpark integration for the Open Link Token library, enabling distributed privacy-preserving token generation for large-scale record linkage workflows.

## Overview

The Open Link Token PySpark Bridge provides a seamless interface between PySpark DataFrames and the Open Link Token library, allowing you to generate cryptographically secure tokens for record linkage in a distributed computing environment.

## Features

- **Distributed Processing**: Leverage PySpark's distributed computing capabilities for large datasets
- **Simple API**: Easy-to-use interface that accepts PySpark DataFrames
- **Exchange-Config Ready**: Recommended initiate-exchange flow with direct-secret support when you manage raw secrets yourself
- **Flexible Column Names**: Supports multiple column name variants (e.g., FirstName/GivenName)
- **Jupyter Ready**: Includes example notebooks for interactive exploration

## Installation

### Prerequisites

- Python 3.10 or higher
- Open Link Token core library (automatically installed as dependency)
- Apache Spark or PySpark environment

### Version Compatibility

Open Link Token PySpark supports multiple Spark versions to accommodate different Java environments and cluster configurations:

| Spark Version | PySpark Version | PyArrow Version | Pandas Version | Java Version | Installation Extra            |
| ------------- | --------------- | --------------- | -------------- | ------------ | ----------------------------- |
| **4.0.x**     | >=4.0.1, <5.0   | >=17.0.0, <18.0 | >=2.0.0, <2.4  | **21**       | `[spark40]` **(Recommended)** |
| 4.1.x         | >=4.1.0, <5.0   | >=17.0.0, <18.0 | >=2.0.0, <2.4  | **21**       | `[spark41]`                   |
| 3.5.x         | >=3.5.0, <3.6   | >=15.0.0, <20   | >=1.5, <2.3    | 8-17         | `[spark35]`                   |
| 3.4.x         | >=3.4.0, <3.5   | >=10.0.0, <15   | >=1.5, <2.2    | 8-17         | `[spark34]`                   |

**Important:**

- PySpark 3.5.x and earlier are **NOT compatible** with Java 21
- If you're using Java 21, you **must** use PySpark 4.0.x+ or 4.1.x+ (Spark 4.0.x recommended)
- For managed clusters (Databricks, EMR, Azure Synapse), PySpark is typically pre-installed

### Installation Options

#### Option 1: Spark 4.0+ (Recommended - Java 21)

For local development or clusters with Java 21:

```bash
uv pip install openlinktoken-pyspark[spark40]
```

#### Option 2: Spark 3.5.x (Java 8-17)

For clusters still using Java 8-17 and Spark 3.5.x:

```bash
uv pip install openlinktoken-pyspark[spark35]
```

#### Option 3: Spark 3.4.x (Legacy)

For older Spark 3.4.x clusters:

```bash
uv pip install openlinktoken-pyspark[spark34]
```

#### Option 4: Managed Cluster Environments

For environments where PySpark is pre-installed (Databricks, EMR, etc.):

```bash
uv pip install openlinktoken-pyspark
```

This installs only the core dependencies without PySpark. You'll use the cluster's PySpark installation.

### Development Setup

For local development with editable install:

```bash
# Install Open Link Token core library first
cd lib/python/openlinktoken
uv pip install -e .

# Install PySpark bridge with Spark 4.0 dependencies
cd ../openlinktoken-pyspark
uv pip install -e .[spark40,dev]
```

The `dev` extra includes testing and notebook dependencies (pytest, jupyter, etc.).

## Quick Start

### Basic Usage (All Spark Versions)

The recommended production flow resolves hashing and transport secrets from an initiate-exchange config on the driver:

```python
import sys
import os
from pyspark.sql import SparkSession
from openlinktoken_pyspark import OpenLinkTokenProcessor

# Create Spark session (PySpark 4.0.1+ handles Java 21 natively)
spark = SparkSession.builder \
    .appName("OpenLinkTokenExample") \
    .master("local[*]") \
    .config("spark.executorEnv.PYTHONPATH", os.pathsep.join(sys.path)) \
    .getOrCreate()

# Load your data
df = spark.read.csv("data.csv", header=True)

# Initialize the processor from an initiate-exchange config
processor = OpenLinkTokenProcessor.from_exchange_config(
    exchange_config_path="initiate-exchange-config.json",
    private_key_path="participant-private-key.pem",
)

# Generate tokens
tokens_df = processor.process_dataframe(df)

# View results
tokens_df.show()
```

`from_exchange_config(...)` resolves the exchange config and private key on the driver, then Spark workers receive only the derived byte payloads needed for token generation.

### Azure Key Vault Example

When your Spark job runs on Azure, keep the vault lookup on the driver and pass the resolved inputs into
`from_exchange_config(...)`. In the PySpark bridge, the direct inputs are still the initiate-exchange config JSON plus the
participant private key. The sender and recipient public keys are already embedded in the generated exchange config payload,
so you normally keep them in Key Vault for exchange creation, rotation, or validation rather than passing them directly to
`OpenLinkTokenProcessor`.

```python
import os

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from openlinktoken_pyspark import OpenLinkTokenProcessor

vault = SecretClient(
    vault_url=os.environ["AZURE_KEY_VAULT_URL"],
    credential=DefaultAzureCredential(),
)

exchange_config_json = vault.get_secret("openlinktoken-initiate-exchange-config").value
participant_private_key_pem = vault.get_secret("openlinktoken-participant-private-key-pem").value

# Optional: keep the public keys in Key Vault for exchange creation/rotation or validation.
sender_public_key_pem = vault.get_secret("openlinktoken-sender-public-key-pem").value
recipient_public_key_pem = vault.get_secret("openlinktoken-recipient-public-key-pem").value

processor = OpenLinkTokenProcessor.from_exchange_config(
    exchange_config_value=exchange_config_json,
    private_key_value=participant_private_key_pem,
)
```

If Azure Key Vault is your system of record for the public keys, use those values when you create or rotate the
initiate-exchange config upstream. The PySpark bridge does not take public-key arguments directly.

### Java 8-17 Setup (PySpark 3.5.x)

If you're using Java 8-17 and cannot upgrade to Java 21:

```python
import sys
import os
from pyspark.sql import SparkSession
from openlinktoken_pyspark import OpenLinkTokenProcessor

# Create Spark session (PySpark 3.5.x with PyArrow <20)
spark = SparkSession.builder \
    .appName("OpenLinkTokenExample") \
    .master("local[*]") \
    .config("spark.executorEnv.PYTHONPATH", os.pathsep.join(sys.path)) \
    .getOrCreate()

# Load your data
df = spark.read.csv("data.csv", header=True)

# Initialize the processor from an initiate-exchange config
processor = OpenLinkTokenProcessor.from_exchange_config(
    exchange_config_path="initiate-exchange-config.json",
    private_key_path="participant-private-key.pem",
)

# Generate tokens
tokens_df = processor.process_dataframe(df)

# View results
tokens_df.show()
```

**Note:** Ensure you have PyArrow <20 installed: `uv pip install 'pyarrow>=15.0.0,<20'`

### Databricks Example

```python
from openlinktoken_pyspark import OpenLinkTokenProcessor

# Load data from Delta table or CSV
df = spark.read.table("my_database.person_records")

# Resolve private key material on the driver before processing
participant_private_key_pem = dbutils.secrets.get(
    "openlinktoken",
    "participant_private_key_pem",
)

processor = OpenLinkTokenProcessor.from_exchange_config(
    exchange_config_path="/dbfs/FileStore/openlinktoken/initiate-exchange-config.json",
    private_key_value=participant_private_key_pem,
)

# Generate tokens
tokens_df = processor.process_dataframe(df)

# Save results
tokens_df.write.mode("overwrite").saveAsTable("my_database.person_tokens")
```

### Direct Secret Usage

If you already inject raw secrets into your Spark application, the direct constructor remains supported:

```python
from openlinktoken_pyspark import OpenLinkTokenProcessor

processor = OpenLinkTokenProcessor(
    hashing_secret="your-hashing-secret",
    encryption_key="0123456789abcdef0123456789abcdef",
)
```

Use this path only when you intentionally manage raw secrets yourself. New integrations should prefer `from_exchange_config(...)`.

## Input DataFrame Requirements

Your input DataFrame must contain the following columns (alternative names are supported):

| Standard Name        | Alternative Names            | Description                                                   |
| -------------------- | ---------------------------- | ------------------------------------------------------------- |
| RecordId             | Id                           | Unique identifier (optional - auto-generated if not provided) |
| FirstName            | GivenName                    | Person's first name                                           |
| LastName             | Surname                      | Person's last name                                            |
| BirthDate            | DateOfBirth                  | Date of birth in YYYY-MM-DD format                            |
| Sex                  | Gender                       | Sex/Gender (Male, Female, M, F)                               |
| PostalCode           | ZipCode                      | US ZIP code or Canadian postal code                           |
| SocialSecurityNumber | NationalIdentificationNumber | SSN or national ID number                                     |

## Output Format

The output DataFrame contains:

- **RecordId**: The original record identifier
- **RuleId**: Token rule identifier (T1, T2, T3, T4, T5)
- **Token**: Encrypted match token in `ot.V1.<JWE>` format (or base64-encoded HMAC in hash-only flows)

Each input record produces multiple output rows (one per token rule).

## Using Custom Token Definitions

You can define custom tokens using the `openlinktoken_pyspark.notebook_helpers` module and pass them to the processor:

```python
from openlinktoken_pyspark import (
    CustomTokenDefinition,
    OpenLinkTokenProcessor,
    TokenBuilder,
    quick_token_from_exchange_config,
)

# Method 1: Using TokenBuilder
custom_token = TokenBuilder("T6") \
    .add("last_name", "T|U") \
    .add("first_name", "T|U") \
    .add("birth_date", "T|D") \
    .add("postal_code", "T|S(0,3)") \
    .add("sex", "T|U") \
    .build()

custom_definition = CustomTokenDefinition().add_token(custom_token)

# Create a processor with the custom definition
processor = OpenLinkTokenProcessor.from_exchange_config(
    exchange_config_path="initiate-exchange-config.json",
    private_key_path="participant-private-key.pem",
    token_definition=custom_definition,
)

# Process DataFrame - will use T6 instead of default T1-T5
tokens_df = processor.process_dataframe(df)

# For one-off notebook exploration, the package root also exports
# create_token_generator_from_exchange_config(...) and quick_token_from_exchange_config(...)
generator = quick_token_from_exchange_config(
    "T7",
    [("last_name", "T|U"), ("first_name", "T|U"), ("birth_date", "T|D")],
    exchange_config_path="initiate-exchange-config.json",
    private_key_path="participant-private-key.pem",
)
```

For more examples and interactive experimentation with custom tokens, see the [Custom Token Definition Guide](notebooks/Custom_Token_Definition_Guide.ipynb).

## Example Notebooks

See the included Jupyter notebooks for complete examples:

**Basic Usage:**

```bash
cd notebooks
jupyter notebook OpenToken_PySpark_Example.ipynb
```

**Custom Token Definitions:**

```bash
cd notebooks
jupyter notebook Custom_Token_Definition_Guide.ipynb
```

**Dataset Overlap Analysis:**

```bash
cd notebooks
jupyter notebook Dataset_Overlap_Analysis_Guide.ipynb
```

## Dataset Overlap Analysis

The `OpenLinkTokenOverlapAnalyzer` class helps identify matching records between two tokenized datasets by decrypting tokens to deterministic values before comparison.

### Basic Usage

```python
from openlinktoken_pyspark import OpenLinkTokenOverlapAnalyzer

# Initialize from the same initiate-exchange config used for token generation
analyzer = OpenLinkTokenOverlapAnalyzer.from_exchange_config(
    exchange_config_path="initiate-exchange-config.json",
    private_key_path="participant-private-key.pem",
)

# Analyze overlap between two tokenized datasets
# Match on tokens T1 and T2 (both must match)
results = analyzer.analyze_overlap(
    tokens_df1,
    tokens_df2,
    matching_rules=["T1", "T2"],
    dataset1_name="Hospital_A",
    dataset2_name="Hospital_B"
)

# Print summary
analyzer.print_summary(results)

# Access detailed results
print(f"Total records in dataset 1: {results['total_records_dataset1']}")
print(f"Matching records: {results['matching_records_dataset1']}")
print(f"Overlap percentage: {results['overlap_percentage']:.2f}%")

# Get DataFrame of matched record pairs
matches_df = results['matches']
matches_df.show()
```

### Compare with Multiple Rule Sets

```python
# Compare overlap using different matching criteria
rule_sets = [
    ["T1"],              # Match on T1 only
    ["T1", "T2"],        # Match on T1 AND T2
    ["T1", "T2", "T3"]   # Match on T1 AND T2 AND T3
]

results = analyzer.compare_with_multiple_rules(
    tokens_df1, tokens_df2, rule_sets
)

# See how overlap changes with stricter rules
for result in results:
    print(f"Rules {result['matching_rules']}: "
          f"{result['overlap_percentage']:.2f}% overlap")
```

### Use Cases

- **Data Quality Assessment**: Identify duplicate records across datasets
- **Patient Matching**: Find matching patients between healthcare systems
- **Research Cohort Overlap**: Analyze overlap between research study populations
- **Data Sharing Analysis**: Assess data overlap before establishing data sharing agreements

### How It Works

1. Both datasets must contain tokenized records (RecordId, RuleId, Token columns)
2. Matching rules specify which token types must match (e.g., ["T1", "T2"])
3. Records are considered matching only if ALL specified token types match
4. The analyzer provides statistics and a DataFrame of matched record pairs
5. Uses the exchange-derived transport key that was used to generate the tokens, supporting both `ot.V1` JWE tokens and legacy encrypted token format

## Testing

Run the test suite:

```bash
# From the openlinktoken-pyspark directory
pytest
```

## Performance Considerations

- **Partitioning**: PySpark processes data in parallel across partitions. Adjust `spark.sql.shuffle.partitions` for your cluster size.
- **Memory**: Token generation is memory-efficient but ensure adequate executor memory for your data volume.
- **Secret Resolution**: Exchange configs and private keys are resolved on the driver; workers receive only the derived hashing/encryption bytes.
- **Secrets on Workers**: Derived secret bytes are still serialized to worker nodes, so ensure secure cluster configuration.

## Architecture

The PySpark bridge uses Pandas UDFs (User Defined Functions) to efficiently process batches of records:

1. Data is partitioned across the Spark cluster
2. Each partition is processed by a Pandas UDF
3. Within each batch, the Open Link Token library generates tokens
4. Results are collected back into a PySpark DataFrame

This architecture balances the benefits of distributed computing with the cryptographic requirements of token generation.

## Security Notes

- **Secrets Management**: Prefer initiate-exchange configs plus secure private-key delivery (for example AWS Secrets Manager or Azure Key Vault)
- **Network Security**: Ensure secure communication between Spark nodes
- **Data Privacy**: Generated tokens are cryptographically secure and cannot be reversed to original values

## Related Documentation

- [Open Link Token Core Library](../openlinktoken/) - Python core implementation
- [Open Link Token CLI](../openlinktoken-cli/) - Python CLI with I/O support (CSV, Parquet)
- [Main Open Link Token Documentation](../../../README.md) - Project overview and setup
- [Development Guide](../../../docs/dev-guide-development.md) - Contributor documentation
