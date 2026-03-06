---
layout: default
---

# Spark or Databricks

How to use the PySpark bridge for distributed token generation on Spark clusters or Databricks.

---

## When to Use PySpark

- **Large datasets**: Millions of records across multiple files
- **Distributed processing**: Leverage cluster computing
- **Overlap analysis**: Find matching records across datasets at scale
- **Cost-effective**: Process on cloud infrastructure (AWS, GCP, Azure)

---

## Installation

### Version Compatibility

| Spark Version | PySpark Version | Java Version | Installation Extra            |
| ------------- | --------------- | ------------ | ----------------------------- |
| **4.0.x**     | >=4.0.1, <5.0   | **21**       | `[spark40]` **(Recommended)** |
| 3.5.x         | >=3.5.0, <3.6   | 8-17         | `[spark35]`                   |
| 3.4.x         | >=3.4.0, <3.5   | 8-17         | `[spark34]`                   |

**Important:** PySpark 3.5.x and earlier are **NOT compatible** with Java 21. If using Java 21, you **must** use PySpark 4.0.1+.

### Local Development

```bash
source /workspaces/OpenToken/.venv/bin/activate

cd lib/python/opentoken-pyspark
uv pip install -e .[spark40]  # For Java 21
# or
uv pip install -e .[spark35]  # For Java 8-17
```

### Managed Clusters (Databricks, EMR, Azure Synapse)

For environments where PySpark is pre-installed:

```bash
uv pip install opentoken-pyspark
```

---

## Basic Usage

### Standard Spark Cluster

```python
import sys
import os
from pyspark.sql import SparkSession
from opentoken_pyspark import OpenTokenProcessor

# Create Spark session
spark = SparkSession.builder \
    .appName("OpenToken") \
    .master("local[*]") \
    .config("spark.executorEnv.PYTHONPATH", os.pathsep.join(sys.path)) \
    .getOrCreate()

# Load your data
df = spark.read.csv("data.csv", header=True)

# Initialize processor with your secrets
processor = OpenTokenProcessor(
    hashing_secret="your-hashing-secret",
    encryption_key="your-encryption-key-32-chars!!"
)

# Generate tokens
tokens_df = processor.process_dataframe(df)

# View results
tokens_df.show()

# Write output
tokens_df.write.mode("overwrite").csv("output/tokens")
```

### Databricks Example

```python
from opentoken_pyspark import OpenTokenProcessor

# Load data from Delta table or CSV
df = spark.read.table("my_database.person_records")

# Initialize processor using Databricks secrets
processor = OpenTokenProcessor(
    hashing_secret=dbutils.secrets.get("opentoken", "hashing_secret"),
    encryption_key=dbutils.secrets.get("opentoken", "encryption_key")
)

# Generate tokens
tokens_df = processor.process_dataframe(df)

# Save results to Delta table
tokens_df.write.mode("overwrite").saveAsTable("my_database.person_tokens")
```

---

## Input DataFrame Requirements

Your DataFrame must contain these columns (alternative names supported):

| Standard Name        | Alternatives                 | Required |
| -------------------- | ---------------------------- | -------- |
| FirstName            | GivenName                    | Yes      |
| LastName             | Surname                      | Yes      |
| BirthDate            | DateOfBirth                  | Yes      |
| Sex                  | Gender                       | Yes      |
| PostalCode           | ZipCode                      | Yes      |
| SocialSecurityNumber | NationalIdentificationNumber | Yes      |
| RecordId             | Id                           | Optional |

---

## Output Format

Each input record produces multiple output rows (one per token rule):

| Column   | Description                     |
| -------- | ------------------------------- |
| RecordId | Original record identifier      |
| RuleId   | Token rule (T1, T2, T3, T4, T5) |
| Token    | Generated cryptographic token   |

---

## Dataset Overlap Analysis

Find matching records between two tokenized datasets:

```python
from opentoken_pyspark import OpenTokenOverlapAnalyzer

# Initialize with encryption key (same key used for token generation)
analyzer = OpenTokenOverlapAnalyzer("encryption-key-32-characters!!")

# Analyze overlap - match on T1 and T2 (both must match)
results = analyzer.analyze_overlap(
    tokens_df1,
    tokens_df2,
    matching_rules=["T1", "T2"],
    dataset1_name="Hospital_A",
    dataset2_name="Hospital_B"
)

# Print summary
analyzer.print_summary(results)

# Access results
print(f"Total records in dataset 1: {results['total_records_dataset1']}")
print(f"Matching records: {results['matching_records_dataset1']}")
print(f"Overlap percentage: {results['overlap_percentage']:.2f}%")

# Get matched pairs
matches_df = results['matches']
matches_df.show()
```

### Compare with Multiple Rule Sets

```python
rule_sets = [
    ["T1"],              # Match on T1 only
    ["T1", "T2"],        # Match on T1 AND T2
    ["T1", "T2", "T3"]   # Match on T1 AND T2 AND T3
]

results = analyzer.compare_with_multiple_rules(
    tokens_df1, tokens_df2, rule_sets
)

for result in results:
    print(f"Rules {result['matching_rules']}: {result['overlap_percentage']:.2f}% overlap")
```

---

## Custom Token Definitions

```python
from opentoken_pyspark import OpenTokenProcessor
from opentoken_pyspark.notebook_helpers import TokenBuilder, CustomTokenDefinition

# Define custom token rule
custom_token = TokenBuilder("T6") \
    .add("last_name", "T|U") \
    .add("first_name", "T|U") \
    .add("birth_date", "T|D") \
    .add("postal_code", "T|S(0,3)") \
    .add("sex", "T|U") \
    .build()

custom_definition = CustomTokenDefinition().add_token(custom_token)

# Create processor with custom definition
processor = OpenTokenProcessor(
    hashing_secret="your-hashing-secret",
    encryption_key="your-encryption-key-32-chars!!",
    token_definition=custom_definition
)

tokens_df = processor.process_dataframe(df)
```

---

## Performance Considerations

### Partitioning

Adjust `spark.sql.shuffle.partitions` for your cluster size:

```python
spark.conf.set("spark.sql.shuffle.partitions", "200")
```

### Memory

Token generation is memory-efficient but ensure adequate executor memory:

```python
spark = SparkSession.builder \
    .config("spark.executor.memory", "4g") \
    .getOrCreate()
```

### Output Format

Use Parquet for large outputs:

```python
tokens_df.write.mode("overwrite").parquet("output/tokens.parquet")
```

---

## Databricks-Specific Configuration

### Secrets Management

Store secrets in Databricks secrets:

```bash
# Create secret scope
databricks secrets create-scope --scope opentoken

# Add secrets
databricks secrets put --scope opentoken --key hashing_secret
databricks secrets put --scope opentoken --key encryption_key
```

### Cluster Libraries

Install via cluster UI or init script:

```bash
uv pip install opentoken-pyspark
```

### Unity Catalog + Secrets (Recommended)

Unity Catalog (UC) is the right place to govern **data access** (tables, volumes, external locations). For **secrets** (hashing/encryption keys), you typically still use **Databricks Secret Scopes** (optionally backed by a cloud secret manager) and lock down access with ACLs and cluster policies.

**Recommended pattern:**

- Store secrets in a secret scope (Databricks-backed, or backed by AWS Secrets Manager / Azure Key Vault / GCP Secret Manager depending on your workspace configuration).
- Restrict who can read secrets (scope ACLs) and which clusters can access them (cluster policies).
- Store token outputs in UC-managed Delta tables (or UC volumes) and grant access via UC privileges.

**Example: read secrets + write UC table**

```python
from opentoken_pyspark import OpenTokenProcessor

hashing_secret = dbutils.secrets.get("opentoken", "hashing_secret")
encryption_key = dbutils.secrets.get("opentoken", "encryption_key")

processor = OpenTokenProcessor(
    hashing_secret=hashing_secret,
    encryption_key=encryption_key,
)

df = spark.read.table("main.pprl.person_records")
tokens_df = processor.process_dataframe(df)

# Write to a UC-managed Delta table
tokens_df.write.mode("overwrite").format("delta").saveAsTable("main.pprl.person_tokens")
```

**Notes:**

- Prefer a dedicated UC schema (e.g., `main.pprl`) for tokenized outputs.
- Consider writing to separate tables per dataset/run to support auditing and reproducibility.
- For production: use cluster policies to prevent printing secrets, and avoid collecting token data to the driver.

---

## Example Notebooks

See the notebooks in `lib/python/opentoken-pyspark/notebooks/`:

- [Custom_Token_Definition_Guide.ipynb](https://github.com/TruvetaPublic/OpenToken/blob/main/lib/python/opentoken-pyspark/notebooks/Custom_Token_Definition_Guide.ipynb) – Define custom token rules
- [Dataset_Overlap_Analysis_Guide.ipynb](https://github.com/TruvetaPublic/OpenToken/blob/main/lib/python/opentoken-pyspark/notebooks/Dataset_Overlap_Analysis_Guide.ipynb) – Find overlapping records across datasets

---

## Security Notes

- **Secrets Management**: Use secure secrets management (Databricks Secrets, AWS Secrets Manager, Azure Key Vault)
- **Network Security**: Ensure secure communication between Spark nodes
- **Secrets Serialization**: Secrets are serialized to worker nodes; ensure secure cluster configuration

---

## Next Steps

- **Batch processing**: [Running Batch Jobs](running-batch-jobs.md)
- **Overlap analysis**: See the [Dataset_Overlap_Analysis_Guide.ipynb](https://github.com/TruvetaPublic/OpenToken/blob/main/lib/python/opentoken-pyspark/notebooks/Dataset_Overlap_Analysis_Guide.ipynb) example notebook
