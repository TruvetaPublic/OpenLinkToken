# OpenToken

Privacy-preserving tokenization and matching library for secure PII-based person linkage. OpenToken generates deterministic, cryptographically secure tokens from person attributes (name, birthdate, SSN, etc.) so datasets can be matched without exposing raw identifiers.

## Introduction

Our approach to person matching relies on building a set of matching tokens (or token signatures) per person which are derived from deterministic person data but preserve privacy by using cryptographically secure hashing algorithms.

- [OpenToken](#opentoken)
  - [Introduction](#introduction)
  - [Highlights](#highlights)
  - [Demo](#demo)
  - [Overview](#overview)
  - [Why OpenToken](#why-opentoken)
  - [Quickstart](#quickstart)
  - [Key Matching Ideas](#key-matching-ideas)
  - [Running OpenToken](#running-opentoken)
  - [Security Notes](#security-notes)
  - [Contributing \& Community](#contributing--community)
  - [Documentation](#documentation)

## Highlights

- Multi-language Support
- Cryptographically Secure encryption that prevents re-identification
- Enables straightforward person-matching by comparing 5 deterministic and unique hash values (after decryption), providing a high degree of confidence in matches

## Demo

New to OpenToken? Start with the **[PPRL Superhero Demo](demos/pprl-superhero-example/)** — a beginner-friendly, end-to-end walkthrough showing how two parties (hospital and pharmacy) can privately find matching records without exposing raw identifiers.

The demo includes:

- **Interactive Jupyter notebook** with step-by-step explanations
- **One-command runner** (`run_end_to_end.sh`) for quick execution
- Synthetic superhero dataset generation
- Token generation and overlap analysis examples

Perfect for understanding privacy-preserving record linkage concepts before diving into production use.

## Overview

- **Multi-language parity**: Java and Python implementations produce byte-identical hash outputs (decrypted values)
- **Deterministic matching values**: Same input always produces the same cryptographically secure hash for matching
- **Privacy-preserving**: Encrypted tokens cannot be reversed to recover original person data

## Why OpenToken

- Practical validation and normalization for common PII-derived attributes (names, birthdates, SSN, postal codes, sex)
- Secure pipeline: SHA-256 → HMAC-SHA256 → AES-256 (or hash-only mode)
- Multiple token rules (T1–T5) to increase match confidence across varied data quality

## Quickstart

**Docker/CLI workflow:**

```bash
./run-opentoken.sh \
  -i ./resources/sample.csv -t csv -o ./resources/output.csv \
  -h "HashingKey" -e "Secret-Encryption-Key-Goes-Here."
```

**Java CLI:**

```bash
cd lib/java && mvn clean install -DskipTests
java -jar opentoken-cli/target/opentoken-cli-*.jar \
  -i ../../resources/sample.csv -t csv -o ../../resources/output.csv \
  -h "HashingKey" -e "Secret-Encryption-Key-Goes-Here."
```

See <a href="https://truvetapublic.github.io/OpenToken/quickstarts/" target="_blank" rel="noopener noreferrer">Quickstarts</a> for Python CLI and detailed setup instructions.

## Key Matching Ideas

- **Token rules**: Five rules (T1–T5) combine attributes in different ways — see <a href="https://truvetapublic.github.io/OpenToken/concepts/token-rules.html" target="_blank" rel="noopener noreferrer">Token Rules</a>
- **Normalization**: Names, dates, postal codes normalized before tokenization — see <a href="https://truvetapublic.github.io/OpenToken/concepts/normalization-and-validation.html" target="_blank" rel="noopener noreferrer">Normalization and Validation</a>
- **Metadata**: Processing statistics and audit trail — see <a href="https://truvetapublic.github.io/OpenToken/reference/metadata-format.html" target="_blank" rel="noopener noreferrer">Metadata Format</a>

## Running OpenToken

- **CLI modes**: Encrypt (default), hash-only (`--hash-only`), decrypt (`-d`) — see <a href="https://truvetapublic.github.io/OpenToken/running-opentoken/" target="_blank" rel="noopener noreferrer">Running OpenToken</a>
- **Docker**: Convenience scripts for containerized runs — see <a href="https://truvetapublic.github.io/OpenToken/quickstarts/" target="_blank" rel="noopener noreferrer">Quickstarts</a>
- **PySpark**: Distributed processing for large datasets — see <a href="https://truvetapublic.github.io/OpenToken/operations/spark-or-databricks.html" target="_blank" rel="noopener noreferrer">Spark or Databricks</a>

## Security Notes

- **Crypto pipeline**: Token signature → SHA-256 → HMAC-SHA256 → AES-256 (or hash-only) — see <a href="https://truvetapublic.github.io/OpenToken/security.html" target="_blank" rel="noopener noreferrer">Security</a>
- **Secret management**: Handle hashing/encryption secrets securely; avoid committing secrets; prefer env/secret stores
- **Validation**: Reject placeholders and malformed attributes before tokenization

## Contributing & Community

- <a href="https://truvetapublic.github.io/OpenToken/community/contributing.html" target="_blank" rel="noopener noreferrer">Contributing Guide</a> — Branching, PR expectations, coding standards
- <a href="https://truvetapublic.github.io/OpenToken/community/code-of-conduct.html" target="_blank" rel="noopener noreferrer">Code of Conduct</a>

## Documentation

- <a href="https://truvetapublic.github.io/OpenToken/" target="_blank" rel="noopener noreferrer">Documentation Index</a>
- <a href="https://truvetapublic.github.io/OpenToken/quickstarts/" target="_blank" rel="noopener noreferrer">Quickstarts</a>
- <a href="https://truvetapublic.github.io/OpenToken/specification.html" target="_blank" rel="noopener noreferrer">Specification</a>
- <a href="https://truvetapublic.github.io/OpenToken/reference/cli.html" target="_blank" rel="noopener noreferrer">CLI Reference</a>
- <a href="https://truvetapublic.github.io/OpenToken/reference/metadata-format.html" target="_blank" rel="noopener noreferrer">Metadata Format</a>

For issues or support, file an issue in this repository.

<!-- Re-run CI checks -->
