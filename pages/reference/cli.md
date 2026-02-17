---
layout: default
---

# CLI Reference

Complete reference for OpenToken CLI arguments, modes, and examples. This page is the single source of truth for CLI flags and options; other documentation (such as Configuration) links here instead of duplicating them.

## Security Note

Treat generated token outputs and metadata as **sensitive**. In particular, `--hash-only` output is intended for internal use and should not be shared externally (for example, in tickets, chats, or public repos).

Hash-only mode is primarily used to build **internal overlap-analysis datasets** that can be joined against **encrypted tokens received from external partners** (after decryption). If you need to **exchange** tokens across organizations, use encrypted mode and follow a controlled exchange process: [Sharing Tokenized Data](../operations/sharing-tokenized-data.md).

## Command Syntax

```bash
# Java
java -jar opentoken-cli-*.jar [OPTIONS]

# Python
python -m opentoken_cli.main [OPTIONS]
```

## Required Arguments

| Argument          | Short | Description                         |
| ----------------- | ----- | ----------------------------------- |
| `--input`         | `-i`  | Path to input file (CSV or Parquet) |
| `--output`        | `-o`  | Path to output file                 |
| `--type`          | `-t`  | File type: `csv` or `parquet`       |
| `--hashingsecret` | `-h`  | Secret key for HMAC-SHA256 hashing  |

## Optional Arguments

| Argument          | Short | Description                               | Default                       |
| ----------------- | ----- | ----------------------------------------- | ----------------------------- |
| `--encryptionkey` | `-e`  | 32-character key for AES-256 encryption   | Required unless `--hash-only` |
| `--hash-only`     |       | Generate hashed tokens without encryption | `false`                       |
| `--output-type`   | `-ot` | Output file type if different from input  | Same as input                 |
| `--decrypt`       | `-d`  | Decrypt mode (input must be encrypted)    | `false`                       |

## Modes of Operation

### Encrypted Mode (Default)

Generates fully encrypted tokens using AES-256-GCM. Tokens can be decrypted later with the encryption key.

```bash
java -jar opentoken-cli-*.jar \
  -i input.csv -t csv -o output.csv \
  -h "HashingSecret" \
  -e "EncryptionKey-Exactly32Chars!!"
```

**Token Pipeline:**
```
Signature → SHA-256 → HMAC-SHA256 → AES-256-GCM → Base64
```

### Hash-Only Mode

Generates one-way hashed tokens. Faster but tokens cannot be decrypted.

```bash
java -jar opentoken-cli-*.jar \
  -i input.csv -t csv -o output.csv \
  -h "HashingSecret" \
  --hash-only
```

**Token Pipeline:**
```
Signature → SHA-256 → HMAC-SHA256 → Base64
```

## File Format Examples

### CSV Input

```csv
RecordId,FirstName,LastName,BirthDate,Sex,PostalCode,SSN
patient_001,John,Doe,1980-01-15,Male,98004,123-45-6789
patient_002,Jane,Smith,1975-03-22,Female,90210,987-65-4321
```

**Column Aliases Accepted:**

| Standard Name | Accepted Aliases                                   |
| ------------- | -------------------------------------------------- |
| RecordId      | Id                                                 |
| FirstName     | GivenName                                          |
| LastName      | Surname                                            |
| BirthDate     | DateOfBirth                                        |
| Sex           | Gender                                             |
| PostalCode    | ZipCode, ZIP3, ZIP4, ZIP5                          |
| SSN           | SocialSecurityNumber, NationalIdentificationNumber |

### CSV Output

```csv
RecordId,RuleId,Token
patient_001,T1,Gn7t1Zj16E5Qy+z9iINtczP6fRDYta6C0XFr...
patient_001,T2,pUxPgYL9+cMxkA+8928Pil+9W+dm9kISwHYP...
patient_001,T3,rwjfwIo5OcJUItTx8KCoSZMtr7tVGSyXsWv/...
patient_001,T4,9o7HIYZkhizczFzJL1HFyanlllzSa8hlgQWQ...
patient_001,T5,QpBpGBqaMhagfcHGZhVavn23ko03jkyS9Vo4...
```

### Parquet Schema

**Input:**
```
RecordId: string
FirstName: string
LastName: string
BirthDate: string (YYYY-MM-DD)
Sex: string
PostalCode: string
SSN: string
```

**Output:**
```
RecordId: string
RuleId: string
Token: string
```

## Metadata Output

Every run generates a `.metadata.json` file:

```json
{
  "Platform": "Java",
  "JavaVersion": "21.0.0",
  "OpenTokenVersion": "2.0.0-alpha",
  "TotalRows": 100,
  "TotalRowsWithInvalidAttributes": 3,
  "InvalidAttributesByType": {
    "BirthDate": 2,
    "SSN": 1
  },
  "BlankTokensByRule": {
    "T1": 2,
    "T4": 1
  },
  "HashingSecretHash": "e0b4e60b...",
  "EncryptionSecretHash": "a1b2c3d4..."
}
```

## Docker Script Options

### Bash (run-opentoken.sh)

```bash
./run-opentoken.sh \
  -i ./input.csv \
  -o ./output.csv \
  -t csv \
  -h "HashingKey" \
  -e "EncryptionKey" \
  [--skip-build] \
  [--verbose]
```

| Option         | Description               |
| -------------- | ------------------------- |
| `--skip-build` | Skip Docker image rebuild |
| `--verbose`    | Show detailed output      |
| `--help`       | Show help message         |

### PowerShell (run-opentoken.ps1)

```powershell
.\run-opentoken.ps1 `
  -i .\input.csv `
  -o .\output.csv `
  -FileType csv `
  -h "HashingKey" `
  -e "EncryptionKey" `
  [-SkipBuild] `
  [-Verbose]
```

## Error Messages

| Error                                  | Cause                          | Solution                            |
| -------------------------------------- | ------------------------------ | ----------------------------------- |
| "Encryption key not provided"          | Missing `-e` in encrypted mode | Add `-e "key"` or use `--hash-only` |
| "Encryption key must be 32 characters" | Key length wrong               | Use exactly 32 characters           |
| "Input file not found"                 | Invalid path                   | Check file exists                   |
| "Unknown file type"                    | Invalid `-t` value             | Use `csv` or `parquet`              |
| "Invalid attribute: BirthDate"         | Date validation failed         | Use YYYY-MM-DD format               |

## Exit Codes

| Code | Meaning           |
| ---- | ----------------- |
| 0    | Success           |
| 1    | Invalid arguments |
| 2    | File not found    |
| 3    | Processing error  |

## Performance Tips

- Use Parquet for large datasets (faster I/O, compression)
- Use `--hash-only` if decryption not needed (20-30% faster)
- For very large files, consider [PySpark integration](../operations/spark-or-databricks.md)

## Next Steps

- [Java API Reference](java-api.md) - Programmatic usage
- [Python API Reference](python-api.md) - Programmatic usage
- [Configuration](../config/configuration.md) - Advanced settings
- [Decrypting Tokens](../operations/decrypting-tokens.md) - Reverse encrypted tokens
