---
layout: default
---

# Quickstarts

This page is the single “Start here” hub for getting OpenToken running end-to-end.

## Who This Is For

- Data engineers and analysts who need privacy-preserving linkage inputs
- Platform/infra engineers integrating deterministic token generation into pipelines
- Java and Python teams who need identical outputs across languages

## What You’ll Do

1. Prepare an input file with person attributes (CSV or Parquet)
2. Run OpenToken to generate tokens (encrypted or hash-only)
3. Inspect the token output and the `.metadata.json` audit artifact

## Choose Your Path

| If you want…                         | Start with…                               | Why                                                   |
| ------------------------------------ | ----------------------------------------- | ----------------------------------------------------- |
| The fastest “just run it” experience | [CLI Quickstart](cli-quickstart.md)       | Uses Docker scripts (recommended) or the CLI directly |
| Python-first workflow or integration | [Python Quickstart](python-quickstart.md) | Uses the Python CLI and shows programmatic API usage  |
| Java-first workflow or integration   | [Java Quickstart](java-quickstart.md)     | Builds the Java CLI and shows programmatic API usage  |

## 30-Second Overview

OpenToken reads person attributes (for example: first/last name, birthdate, sex, postal code, SSN) and emits deterministic token fingerprints plus, by default, encrypted `ot.V1` match tokens for privacy-preserving exchange.

After you run a quickstart:

- `output.csv` contains 5 tokens (T1–T5) per input record
- `output.metadata.json` captures processing stats and SHA-256 hashes of secrets (not the secrets)

## Quickstart Pages

- [CLI Quickstart](cli-quickstart.md)
- [Python Quickstart](python-quickstart.md)
- [Java Quickstart](java-quickstart.md)

## Test Your Data

Generate mock input data:

```bash
cd tools/mockdata

# Create 100 test records
python data_generator.py 100 0.05 test_data.csv
```

## Next Steps

- **Understand matching**: Read [Concepts: Token Rules](../concepts/token-rules.md)
- **Explore input formats**: See [Configuration](../config/configuration.md)
- **Decrypt tokens**: See [Decrypting Tokens](../operations/decrypting-tokens.md)
- **Advanced: PySpark**: See [Spark or Databricks](../operations/spark-or-databricks.md)
- **Troubleshooting**: See [Running OpenToken](../running-opentoken/index.md)

## Input File Requirements

Your CSV must have these columns (any of the listed aliases work):

| Column     | Aliases                      | Required | Example                                         |
| ---------- | ---------------------------- | -------- | ----------------------------------------------- |
| FirstName  | GivenName                    | Yes      | John                                            |
| LastName   | Surname                      | Yes      | Doe                                             |
| BirthDate  | DateOfBirth                  | Yes      | 1975-03-15 or 03/15/1975                        |
| Sex        | Gender                       | Yes      | Male, Female, M, F                              |
| PostalCode | ZipCode, ZIP3, ZIP4, ZIP5    | Yes      | 98004                                           |
| SSN        | NationalIdentificationNumber | Yes      | 123-45-6789 (digits-only values are normalized) |
| RecordId   | Id                           | Optional | patient_id_123                                  |

**Note**: RecordId is optional. If omitted, a unique UUID is auto-generated for each record.

See [Configuration](../config/configuration.md) for detailed column mapping and format options.

---

## Common Issues

**"Encryption key not provided"**  
→ Either add `-e "YourKey"` or use `--hash-only` for hash-only mode.

**"Invalid BirthDate"**  
→ Use YYYY-MM-DD format or one of the accepted formats. Date must be between 1910-01-01 and today.

**"Docker image not found"**  
→ The script builds it automatically. Make sure you have Docker running.

For more troubleshooting, see [Running OpenToken](../running-opentoken/index.md).
