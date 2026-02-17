# OpenToken  <!-- omit in toc -->

## Introduction

Our approach to person matching relies on building a set of matching tokens (or token signatures) per person which are derived from deterministic person data but preserve privacy by using cryptographically secure hashing algorithms.

- [Introduction](#introduction)
- [Highlights](#highlights)
- [Overview](#overview)
- [Usage](#usage)
- [Quick Start](#quick-start)
    - [Using Convenience Scripts (Recommended)](#using-convenience-scripts-recommended)
    - [Manual Docker Commands](#manual-docker-commands)
- [Development \& Documentation](#development--documentation)
- [Contributing](#contributing)

## Highlights

- **Multi-language Support**: Java, Python, and Node.js implementations with identical token generation
- Cryptographically Secure encryption that prevents re-identification
- Enables straightforward person-matching by comparing 5 deterministic and unique tokens, providing a high degree of confidence in matches

## Overview

### Library <!-- omit in toc -->

This project, `OpenToken`, provides common utilities, models, and services used across the person matching system. It is designed to support the development of applications and services that require person matching capabilities, ensuring consistency and efficiency.

### Token Generation <!-- omit in toc -->

Tokens are cryptographically secure hashes computed from multiple deterministic person attributes. Tokens are created based on a set of `token generation rules`. We use multiple distinct token generation rules that define a set of person attributes and which parts of those attributes to use for token generation.

### Sample Token Generation Rules <!-- omit in toc -->

| Rule ID | Rule Definition                                          |
| ------- | -------------------------------------------------------- |
| T1      | `U(last-name)\|U(first-name-1)\|U(sex)\|birth-date`      |
| T2      | `U(last-name)\|U(first-name)\|birth-date\|postal-code-3` |
| T3      | `U(last-name)\|U(first-name)\|U(sex)\|birth-date`        |
| T4      | `social-security-number\|U(sex)\|birth-date`             |
| T5      | `U(last-name)\|U(first-name-3)\|U(sex)`                  |

> U(X) = uppercase(X)<br>
> attribute-N = take first N characters from the `attribute`

### Token Encryption Process <!-- omit in toc -->

A token signature is generated first for every token generation rule. The token signature is then cryptographically hashed and hex encoded to generate the token.

> $Token(R) = Hex(Sha256(TokenSignature(R)))$ where R is the rule ID.<br>
> The token is then transformed further using the formula below:<br>
> $Base64(AESEncrypt(Base64(HMACSHA256(Token(R)))))$<br>

### Example <!-- omit in toc -->

Given a person with the following attributes:

```csv
RecordId,FirstName,LastName,PostalCode,Sex,BirthDate,SocialSecurityNumber
891dda6c-961f-4154-8541-b48fe18ee620,John,Doe,98004,Male,2000-01-01,123-45-6789
```

**Note:** No attribute value can be empty to be considered valid.

The token generation rules above generate the following token signatures:

| Rule ID | Token Signature               | Token                                                                                              |
| ------- | ----------------------------- | -------------------------------------------------------------------------------------------------- |
| T1      | `DOE\|J\|MALE\|2000-01-01`    | `Gn7t1Zj16E5Qy+z9iINtczP6fRDYta6C0XFrQtpjnVQSEZ5pQXAzo02Aa9LS9oNMOog6Ssw9GZE6fvJrX2sQ/cThSkB6m91L` |
| T2      | `DOE\|JOHN\|2000-01-01\|980`  | `pUxPgYL9+cMxkA+8928Pil+9W+dm9kISwHYPdkZS+I2nQ/bQ/8HyL3FOVf3NYPW5NKZZO1OZfsz7LfKYpTlaxyzMLqMF2Wk7` |
| T3      | `DOE\|JOHN\|MALE\|2000-01-01` | `rwjfwIo5OcJUItTx8KCoSZMtr7tVGSyXsWv/hhCWmD2pBO5JyfmujsosvwYbYeeQ4Vl1Z3eq0cTwzkvfzJVS/EKaRhtjMZz5` |
| T4      | `123456789\|MALE\|2000-01-01` | `9o7HIYZkhizczFzJL1HFyanlllzSa8hlgQWQ5gHp3Niuo2AvEGcUwtKZXChzHmAa8Jm3183XVoacbL/bFEJyOYYS4EQDppev` |
| T5      | `DOE\|JOH\|MALE`              | `QpBpGBqaMhagfcHGZhVavn23ko03jkyS9Vo4qe78E4sKw+Zq2CIw4MMWG8VXVwInnsFBVk6NSDUI79wECf5DchV5CXQ9AFqR` |

**Note:** The tokens in the example above have been generated using the hash key `HashingKey` and encryption key `Secret-Encryption-Key-Goes-Here.`

### Data Flow  <!-- omit in toc -->

![open-token-data-flow](./docs/images/open-token-data-flow.jpg)

### Validation of Person Attributes  <!-- omit in toc -->

The person attributes are validated before normalization. The validation rules are as follows:

| Attribute Name         | Validation Rule                                                                                                                                                                                                                                                                                                                                        |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `FirstName`            | Cannot be a placeholder value (e.g., "Unknown", "Test", "NotAvailable", "Patient", "Sample", "Anonymous", "Missing", etc.). Must not be null or empty.                                                                                                                                                                                                 |
| `LastName`             | Must be at least 2 characters long. For 2-character names, must contain at least one vowel or be "Ng". Cannot be a placeholder value (e.g., "Unknown", "Test", "NotAvailable", "Patient", "Sample", "Anonymous", "Missing", etc.). Must not be null or empty.                                                                                          |
| `BirthDate`            | Must be after January 1, 1910. Cannot be in the future (after today's date). Must be in a valid date format.                                                                                                                                                                                                                                           |
| `PostalCode`           | Must be a valid US ZIP code (3, 4, 5, or 9 digits) or Canadian postal code (3, 4, 5, or 6 characters). **US ZIP codes:** `ddd` (ZIP-3, padded to `ddd00`), `dddd` (ZIP-4, padded to `dddd0`), `ddddd` or `ddddd-dddd`. **Canadian postal codes:** `AdA` (3-char, padded to `AdA 000`), `AdAd` or `AdA d` (4-char, padded to `AdA dA0`), `AdAdA` or `AdA dA` (5-char, padded to `AdA dA0`), or `AdA dAd` (full format). Invalid ZIP-3 codes: US `000`, `555`, `888`; Canadian `K1A`, `M7A`, `H0H`. Cannot be common placeholder values like `11111`, `12345`, `54321`, `98765` for US or `A1A 1A1`, `X0X 0X0` for Canadian codes. |
| `SocialSecurityNumber` | Area cannot be `000`, `666` or `900-999`. Group cannot be `00`. Serial cannot be `0000`. Cannot be one of the following invalid sequences: `111-11-1111`, `222-22-2222`, `333-33-3333`, `444-44-4444`, `555-55-5555`, `777-77-7777`, `888-88-8888`.                                                                                                    |

### Normalization of Person Attributes  <!-- omit in toc -->

All attribute values get normalized as part of their processing after validation. The normalization process includes:

**FirstName normalization:**

- Removes titles (e.g., "Dr. John" → "John")
- Removes middle initials (e.g., "John J" → "John")
- Removes trailing periods (e.g., "John J." → "John")
- Removes generational suffixes (e.g., "Henry IV" → "Henry")
- Removes non-alphabetic characters (e.g., "Anne-Marie" → "AnneMarie")
- Normalizes diacritics (e.g., "José" → "Jose")

**LastName normalization:**

- Removes generational suffixes (e.g., "Warner IV" → "Warner")
- Removes non-alphabetic characters (e.g., "O'Keefe" → "OKeefe")
- Normalizes diacritics (e.g., "García" → "Garcia")

| Attribute Name           | Normalized Format                                                                                            |
| ------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `record-id`              | Any unique string identifier (optional - auto-generated UUID if not provided)                                |
| `first-name`             | Any string (after normalization as described above)                                                          |
| `last-name`              | Any string (after normalization as described above)                                                          |
| `postal-code`            | US: `ddddd` where `d` is a numeric digit (0-9). Canadian: `AdA dAd` where `A` is a letter and `d` is a digit. Partial postal codes are automatically padded during normalization: US ZIP-3 (`ddd` → `ddd00`), ZIP-4 (`dddd` → `dddd0`); Canadian 3-char (`AdA` → `AdA 000`), 4-char (`AdAd` → `AdA dA0`), 5-char (`AdAdA` → `AdA dA0`). |
| `sex`                    | `Male\|Female`                                                                                               |
| `birth-date`             | `YYYY-MM-DD` where `MM` is (01-12), `DD` is (01-31)                                                          |
| `social-security-number` | `ddddddddd` where `d` is a numeric digit (0-9) |

### How Token Matching Works  <!-- omit in toc -->

This library focuses primarily on token generation. Even though the person matching process is beyond the scope of this library, this document discusses how these tokens work in a person matching system.

As noted above, N distinct tokens are generated for each person using this library. The output of this process is below for three person records r1, r2, and r3:

| RecordId | RuleId | Token(RecordId, RuleId) |
| -------- | ------ | ----------------------- |
| r1       | T1     | Token(r1,T1)            |
| r1       | T2     | Token(r1,T2)            |
| r1       | T3     | Token(r1,T3)            |
| r1       | T4     | Token(r1,T4)            |
| r1       | T5     | Token(r1,T5)            |
| r2       | T1     | Token(r2,T1)            |
| r2       | T2     | Token(r2,T2)            |
| r2       | T3     | Token(r2,T3)            |
| r2       | T4     | Token(r2,T4)            |
| r2       | T5     | Token(r2,T5)            |
| r3       | T1     | Token(r3,T1)            |
| r3       | T2     | Token(r3,T2)            |
| r3       | T3     | Token(r3,T3)            |
| r3       | T4     | Token(r3,T4)            |
| r3       | T5     | Token(r3,T5)            |

If tokens are generated for persons from multiple data sources, person matching systems can identify a person match if the tokens for a person from one data source matches tokens for another person from a different data source. In the picture below, all tokens for **r3** and **r4** match, and as such r3 and r4 are considered a match.

![open-token-system](./docs/images/open-token-system.jpg)

## Usage

### Arguments  <!-- omit in toc -->

The driver accepts multiple command line arguments:

- `-t | --type`: This argument is used to specify the input file type. You can provide the file type as a string. Types `csv` or `parquet` are supported.

- `-i | --input`: This argument is used to specify the input file path. You can provide the path to an input file containing the sample data for person matching.

- `-o | --output`: This argument is used to specify the output file path. The generated tokens will be written to this file.

- `-ot | --output-type`: Optional. This argument is used to specify the output file type. If not provided, the input type will be used as output type. You can provide the file type as a string. Types `csv` or `parquet` are supported.

- `-h | --hashingsecret`: This argument is used to specify the hashing secret for the `HMAC-SHA256` digest. The generated tokens are hashed using this digest.

- `-e | --encryptionkey`: This argument is used to specify the encryption key for the `AES-256` symmetric encryption. The generated tokens are encrypted using this key.

The encryption logic is: 
> $Base64(AES-Encrypt(HMAC-SHA256(Hex(Sha256(token-signature)))))$

### Accepted input  <!-- omit in toc -->

The input file (in csv format) must contain at least the following columns and values (one each):

| Accepted Column Names                              | Required | Accepted Values                                                                                                       |
| -------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------- |
| RecordId, Id                                       | Optional | Any unique string identifier. If not provided, a unique UUID will be automatically generated for each row.           |
| FirstName, GivenName                               | Required | Any string value                                                                                                      |
| LastName, Surname                                  | Required | Any string value                                                                                                      |
| PostalCode, ZipCode, ZIP3, ZIP4, ZIP5                    | Required | US: 3 (ZIP-3), 4, 5, or 9 digit ZIP code `ddd`, `ddddd` or `ddddd-dddd`. Canadian: 3 (ZIP-3) or 6 character postal code `AdA` or `AdAdAd` (with or without space). ZIP-3 codes are automatically padded to full length. |
| Sex, Gender                                        | Required | `Male`, `M`, `Female`, `F`                                                                                            |
| BirthDate, DateOfBirth                             | Required | Dates in either format: `yyyy/MM/dd`, `MM/dd/yyyy`, `MM-dd-yyyy`, `dd.MM.yyyy`                                        |
| SocialSecurityNumber, NationalIdentificationNumber | Required | 9 digit number, with or without dashes, e.g. `ddd-dd-dddd`                                                            |

**Note 1:** RecordId is optional. When not provided in the input file, the system automatically generates a unique UUID for each record in the output. Auto-generated UUIDs are suitable for initial overlap analysis, but for linkage of actual data records, providing real RecordIds from your source data is recommended.

**Note 2:** No attribute values (other than RecordId) can be empty to be considered valid.

**Note 3:** Commas are only used for separation of field values, not for within values.

The output file (in csv format) contains the following columns:

- RecordId
- TokenId
- Token

### Metadata  <!-- omit in toc -->

The library generates a metadata file containing information about the token generation process, including processing statistics, system information, and secure hashes of the secrets used. The metadata file is written to the same directory as the output file with the suffix `.metadata.json`.

The metadata includes key fields such as:

- Processing statistics (total records, valid/invalid counts)
- System information (Java version, library version, timestamp)
- Security hashes (SHA-256 hashes of the hashing secret and encryption key)
- Input/output file paths

For complete details about all metadata fields, examples, and security considerations, see the [Metadata Format Documentation](./docs/metadata-format.md).

## Quick Start

### Java  <!-- omit in toc -->

```shell
cd lib/java/opentoken
mvn clean install
java -jar target/opentoken-*.jar \
  -i ../../../resources/sample.csv -t csv -o target/output.csv \
  -h "HashingKey" -e "Secret-Encryption-Key-Goes-Here."
```

### Python  <!-- omit in toc -->

```shell
cd lib/python/opentoken
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r dev-requirements.txt -e .
PYTHONPATH=src/main python src/main/opentoken/main.py \
  -i ../../../resources/sample.csv -t csv -o ../../../resources/output.csv \
  -h "HashingKey" -e "Secret-Encryption-Key-Goes-Here."
```

### Node.js  <!-- omit in toc -->

```shell
cd lib/nodejs/opentoken
npm install
npm run build
npm start -- \
  -i ../../../resources/sample.csv -o ../../../resources/output.csv \
  -k "HashingKey" -e "Secret-Encryption-Key-Goes-Here."
```

### Docker  <!-- omit in toc -->

#### Using Convenience Scripts (Recommended)

Use the provided scripts to automatically build and run OpenToken via Docker:

**Bash (Linux/Mac):**
```bash
./run-opentoken.sh -i /path/to/input.csv -o /path/to/output.csv -t csv \
  -h "HashingKey" -e "Secret-Encryption-Key-Goes-Here."
```

**PowerShell (Windows):**
```powershell
.\run-opentoken.ps1 -i D:\Data\input.csv -o D:\Data\output.csv -FileType csv `
  -h "HashingKey" -e "Secret-Encryption-Key-Goes-Here."
```

These scripts automatically:
- Build the Docker image (if needed)
- Mount input/output directories
- Handle path conversions for your OS
- Support both CSV and Parquet formats

Run with `--help` (Bash) or `-Help` (PowerShell) for all options, including:
- `-t` or `-FileType` for format selection (csv/parquet)
- `-s` or `-SkipBuild` to skip rebuilding the image
- `-v` or `-Verbose` for detailed output

#### Manual Docker Commands

Alternatively, build and run using Docker manually (from repository root):

```shell
# Build the Docker image
docker build -t opentoken:latest .

# Run with sample data
docker run --rm -v $(pwd)/resources:/app/resources \
  opentoken:latest \
  -i /app/resources/sample.csv -t csv -o /app/resources/output.csv \
  -h "HashingKey" -e "Secret-Encryption-Key-Goes-Here."
```

**Note:** These commands must be run from the repository root directory.
The Docker container mounts the `resources` directory to access input files and write output files.
If running in a dev container environment, use the absolute path: `-v /workspaces/OpenToken/resources:/app/resources`

## Development & Documentation

Central reference: [Development Guide](docs/dev-guide-development.md) (setup, build, testing, versioning, dev container, registration, contribution checklist).

Key anchors in the guide:

- Language Development: [Java & Python](docs/dev-guide-development.md#3-language-development-java--python)
- Registration: [Token & Attribute Registration](docs/dev-guide-development.md#4-token--attribute-registration)

Quick parity note: Java and Python implementations produce identical tokens for the same normalized input values.

### Project Structure <!-- omit in toc -->

```
lib/
├── java/        # Java implementation (Maven)
├── python/      # Python implementation (pip)
tools/           # Utility scripts and tools
docs/            # Documentation
.devcontainer/   # Development container configuration
```

### Development Environment  <!-- omit in toc -->

Use the Dev Container for a reproducible setup (Java, Maven, Python). See the [Development Guide](docs/dev-guide-development.md#7-development-container) for details.

### Test Data  <!-- omit in toc -->

You can generate mock person data in the expected format for testing purposes.

#### Prerequisites  <!-- omit in toc -->

- Python3
- [faker](https://pypi.org/project/Faker/)

#### Generating Mock Data  <!-- omit in toc -->

Navigate to `tools/mockdata/` to find the data generation script. Run it with pre-configured defaults:

```shell
./generate.sh
```

You can modify the parameters when running the script directly. The script will repeat a percentage of the record values using a different record ID.

```shell
# python data_generator.py <number of records> <percentage of repeated records> <output file name>
python data_generator.py 100 0.05 test_data.csv
```

The script generates fake person data and optionally repeats a percentage of records with different record IDs to simulate duplicate persons.

## Contributing

We welcome contributions including features, bug fixes, documentation updates, and more. Key areas for improvement include:

1. **File Format Support**: The library currently supports CSV and Parquet. Additional readers/writers for other formats are highly desired.
2. **Test Coverage**: Expanding unit tests and integration tests.
3. **Language Implementations**: Adding support for additional programming languages.

### Before Contributing  <!-- omit in toc -->

Please ensure you follow the project's coding standards:

- **Java**: Follow Checkstyle rules and add Javadoc for public APIs
- **Version Bumping**: Use `bump2version` for all PRs (required)
- **Testing**: Run `mvn clean install` to ensure everything works

See the [contribution guidelines](.github/copilot-instructions.md) for detailed requirements.