---
layout: default
---

# Mock Data Workflows

How to generate and process mock datasets for testing OpenToken pipelines.

---

## Overview

OpenToken includes a mock data generator for testing and development. The tool creates realistic person records with configurable duplicate rates for overlap analysis testing.

---

## Mock Data Generator

Location: [tools/mockdata/data_generator.py](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/tools/mockdata/data_generator.py)

### Usage

```bash
cd tools/mockdata
python data_generator.py <num_lines> <repeat_probability> <output_file>
```

### Parameters

| Parameter            | Description                                       | Example         |
| -------------------- | ------------------------------------------------- | --------------- |
| `num_lines`          | Total number of records to generate               | `100`           |
| `repeat_probability` | Fraction of records that are duplicates (0.0–1.0) | `0.05`          |
| `output_file`        | Output CSV file path                              | `test_data.csv` |

### Examples

```bash
# Generate 100 records with 5% duplicates
python data_generator.py 100 0.05 test_data.csv

# Generate 10,000 records with 10% duplicates
python data_generator.py 10000 0.10 large_test.csv

# Generate 1,000 records with no duplicates
python data_generator.py 1000 0.0 unique_records.csv
```

### Default Values

If no arguments provided:
- `num_lines`: 100
- `repeat_probability`: 0.05 (5%)
- `output_file`: `test_data.csv`

---

## Output Format

Generated CSV files include all required OpenToken columns:

```csv
RecordId,BirthDate,FirstName,LastName,PostalCode,Sex,SocialSecurityNumber
550e8400-e29b-41d4-a716-446655440000,1985-03-15,John,Smith,98004,Male,123-45-6789
550e8400-e29b-41d4-a716-446655440001,1975-06-20,Jane,Doe,10001,Female,987-65-4321
...
```

### Generated Fields

| Field                | Generator                    | Example             |
| -------------------- | ---------------------------- | ------------------- |
| RecordId             | UUID4                        | `550e8400-e29b-...` |
| BirthDate            | Random date (0–90 years ago) | `1985-03-15`        |
| FirstName            | Faker first_name()           | `John`              |
| LastName             | Faker last_name()            | `Smith`             |
| PostalCode           | Faker zipcode()              | `98004`             |
| Sex                  | Random: Male/Female          | `Male`              |
| SocialSecurityNumber | Faker ssn()                  | `123-45-6789`       |

---

## Duplicate Records

Duplicates are created by copying existing records with new `RecordId` values. This simulates:

- Same person appearing multiple times in a dataset
- Overlap between datasets for testing matching algorithms

### How Duplicates Work

```
Total records: 100
Repeat probability: 0.05

Unique records generated: 95
Duplicates added: 5 (randomly selected from the 95)
Total output: 100 records (95 unique + 5 duplicates)
```

Duplicates have **different RecordIds** but **identical attributes**, so they produce **matching tokens**.

---

## Testing Workflows

### Basic Token Generation Test

```bash
# 1. Generate test data
cd tools/mockdata
python data_generator.py 100 0.05 test_data.csv

# 2. Process with OpenToken
cd ../../
./run-opentoken.sh \
  -i tools/mockdata/test_data.csv \
  -o resources/test_output.csv \
  -t csv \
  -h "HashingKey" \
  -e "Secret-Encryption-Key-Goes-Here."

# 3. Check output
cat resources/test_output.csv
cat resources/test_output.metadata.json
```

### Overlap Analysis Test

Generate two datasets with controlled overlap:

```bash
# Generate two datasets
cd tools/mockdata
python data_generator.py 1000 0.0 dataset_a.csv
python data_generator.py 1000 0.0 dataset_b.csv

# Add some common records manually or use a script
# Then process both with OpenToken using the same secrets
```

For automated overlap analysis, see [Spark or Databricks](spark-or-databricks.md).

---

## Sample Data Files

Pre-generated sample files are available in [resources/](https://github.com/TruvetaPublic/OpenLinkToken/tree/main/resources):

| File                                                                                                                    | Description                    |
| ----------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| [sample.csv](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/resources/sample.csv)                                 | Small test file for quickstart |
| [mockdata/test_data.csv](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/resources/mockdata/test_data.csv)         | 100 records with duplicates    |
| [mockdata/test_overlap1.csv](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/resources/mockdata/test_overlap1.csv) | Dataset for overlap testing    |
| [mockdata/test_overlap2.csv](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/resources/mockdata/test_overlap2.csv) | Dataset for overlap testing    |

---

## Requirements

The mock data generator requires:

```bash
pip install faker
```

Or install from the tools requirements:

```bash
cd tools
pip install -r requirements.txt
```

---

## Large-Scale Testing

For generating large test datasets:

```bash
# Generate 1 million records (takes a few minutes)
python data_generator.py 1000000 0.02 large_test.csv

# Progress is printed every 1000 records
# Writing record 0
# Writing record 1000
# Writing record 2000
# ...
```

**Tip:** For very large files, use Parquet format for processing:

```bash
# Convert CSV to Parquet (using pandas or spark)
python -c "
import pandas as pd
df = pd.read_csv('large_test.csv')
df.to_parquet('large_test.parquet')
"

# Process with OpenToken
java -jar opentoken-cli-*.jar \
  -i large_test.parquet -t parquet \
  -o tokens.parquet \
  -h "HashingKey" -e "EncryptionKey"
```

---

## Next Steps

- **Run OpenToken**: [Running Batch Jobs](running-batch-jobs.md)
- **Quickstart guide**: [Quickstarts](../quickstarts/index.md)
- **Overlap analysis**: [Spark or Databricks](spark-or-databricks.md)
