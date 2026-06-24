# Open Link Token

Privacy-preserving tokenization and matching library for secure PII-based person linkage. Open Link Token generates deterministic, cryptographically secure tokens from person attributes (name, birthdate, SSN, etc.) so datasets can be matched without exposing raw identifiers.

## Introduction

Our approach to record linkage relies on building a set of matching tokens (or token signatures) per person which are derived from deterministic person data but preserve privacy by using cryptographically secure hashing algorithms.

- [Open Link Token](#open-link-token)
  - [Introduction](#introduction)
  - [Highlights](#highlights)
  - [Demo](#demo)
  - [Overview](#overview)
  - [Why Open Link Token](#why-open-link-token)
  - [Quickstart](#quickstart)
  - [Key Matching Ideas](#key-matching-ideas)
  - [Running Open Link Token](#running-open-link-token)
  - [Security Notes](#security-notes)
  - [Contributing \& Community](#contributing--community)
  - [Documentation](#documentation)

## Highlights

- Multi-language Support
- Cryptographically Secure encryption that prevents re-identification
- Enables straightforward person-matching by comparing 5 deterministic and unique hash values (after decryption), providing a high degree of confidence in matches

## Demo

New to Open Link Token? Start with the **[PPRL Superhero Demo](demos/pprl-superhero-example/)** — a beginner-friendly, end-to-end walkthrough showing how two parties (hospital and pharmacy) can privately find matching records without exposing raw identifiers.

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

## Why Open Link Token

- Practical validation and normalization for common PII-derived attributes (names, birthdates, SSN, postal codes, sex)
- Secure pipeline: SHA-256 → HMAC-SHA256 → AES-256 (or hash-only mode)
- Multiple token rules (T1–T5) to increase match confidence across varied data quality

## Quickstart

**Self-contained executable (easiest):**

Download the binary for your platform from the [latest release](https://github.com/TruvetaPublic/OpenLinkToken/releases):

| Platform                      | Asset                           |
| ----------------------------- | ------------------------------- |
| Linux                         | `olt-vX.Y.Z-linux-x86_64`       |
| macOS (Intel + Apple Silicon) | `olt-vX.Y.Z-macos-universal`    |
| Windows                       | `olt-vX.Y.Z-windows-x86_64.exe` |

Each asset has a matching `.sha256` file you can use to verify the download.

```bash
# Linux
chmod +x olt-v*-linux-x86_64
mv olt-v*-linux-x86_64 olt

# macOS — make executable, clear Gatekeeper quarantine, and rename
chmod +x olt-v*-macos-universal
xattr -d com.apple.quarantine olt-v*-macos-universal
mv olt-v*-macos-universal olt
```

Then run:

```bash
# Linux/macOS
# Simulate receiving the recipient's public key (in practice, your partner provides this)
./olt generate-key-pair --name recipient
# Create the exchange config using the recipient's public key
./olt initiate-exchange --public-key "$HOME/.openlinktoken/recipient.public.pem"
./olt package -i ./resources/sample.csv

# Windows
# Simulate receiving the recipient's public key (in practice, your partner provides this)
.\olt.exe generate-key-pair --name recipient
# Create the exchange config using the recipient's public key
.\olt.exe initiate-exchange --public-key "$HOME/.openlinktoken/recipient.public.pem"
.\olt.exe package -i .\resources\sample.csv
```

**Docker convenience scripts (Linux/macOS and Windows):**

```bash
# Linux/macOS
./run-openlinktoken.sh generate-key-pair --name recipient
./run-openlinktoken.sh initiate-exchange --public-key "$HOME/.openlinktoken/recipient.public.pem"
./run-openlinktoken.sh package \
  -i ./resources/sample.csv -o ./resources/output.zip \
  --exchange-config ./resources/openlinktoken.exchange.json \
  --private-key "$HOME/.openlinktoken/recipient.private.pem"

# Windows
.\run-openlinktoken.ps1 generate-key-pair --name recipient
.\run-openlinktoken.ps1 initiate-exchange --public-key "$HOME\.openlinktoken\recipient.public.pem"
.\run-openlinktoken.ps1 package `
  -i .\resources\sample.csv -o .\resources\output.zip `
  --exchange-config .\resources\openlinktoken.exchange.json `
  --private-key "$HOME\.openlinktoken\recipient.private.pem"
```

**Available Commands:**

- `olt package` - Generate and encrypt tokens in one step using the exchange config
- `olt tokenize` - Generate internal hashed tokens using the exchange config, or use `--mode hash-only` for deterministic SHA-256 output without an exchange config
- `olt encrypt` - Encrypt existing hashed tokens using the exchange config
- `olt decrypt` - Decrypt encrypted tokens using the exchange config
- `olt initiate-exchange` - Create the exchange config consumed by later commands
- `olt help [command]` - Show help for a specific command

See <a href="https://truvetapublic.github.io/OpenLinkToken/quickstarts/" target="_blank" rel="noopener noreferrer">Quickstarts</a> for Python CLI and detailed setup instructions.

## Key Matching Ideas

- **Token rules**: Five rules (T1–T5) combine attributes in different ways — see <a href="https://truvetapublic.github.io/OpenLinkToken/concepts/token-rules.html" target="_blank" rel="noopener noreferrer">Token Rules</a>
- **Normalization**: Names, dates, postal codes normalized before tokenization — see <a href="https://truvetapublic.github.io/OpenLinkToken/concepts/normalization-and-validation.html" target="_blank" rel="noopener noreferrer">Normalization and Validation</a>
- **Metadata**: Processing statistics and audit trail — see <a href="https://truvetapublic.github.io/OpenLinkToken/reference/metadata-format.html" target="_blank" rel="noopener noreferrer">Metadata Format</a>

## Running Open Link Token

- **CLI subcommands** (`olt` binary or Docker convenience scripts):
  - `tokenize` - Internal hashed token generation (`--mode hash-only` is available for deterministic SHA-256 output)
  - `encrypt` - Encrypt existing hashed tokens
  - `decrypt` - Decrypt encrypted tokens
  - `package` - Tokenize + encrypt in one step (recommended)
  - `initiate-exchange` - Create an exchange config from a partner's public key
  - `generate-key-pair` - Generate an ECDH key pair
  - See <a href="https://truvetapublic.github.io/OpenLinkToken/running-openlinktoken/" target="_blank" rel="noopener noreferrer">Running Open Link Token</a>
- **Docker convenience scripts**: `run-openlinktoken.sh` (Linux/macOS) and `run-openlinktoken.ps1` (Windows) wrap Docker automatically — see <a href="https://truvetapublic.github.io/OpenLinkToken/quickstarts/" target="_blank" rel="noopener noreferrer">Quickstarts</a>
- **PySpark**: Distributed processing for large datasets — see <a href="https://truvetapublic.github.io/OpenLinkToken/operations/spark-or-databricks.html" target="_blank" rel="noopener noreferrer">Spark or Databricks</a>

## Security Notes

- **Crypto pipeline**: Token signature → SHA-256 → HMAC-SHA256 → AES-256 (or hash-only) — see <a href="https://truvetapublic.github.io/OpenLinkToken/security.html" target="_blank" rel="noopener noreferrer">Security</a>
- **`tokenize --mode hash-only`**: Deterministic SHA-256 output with no exchange config or secret. Useful for local exploration, but **not** for production or cross-organisation exchange
- **Secret management**: Handle hashing/encryption secrets securely; avoid committing secrets; prefer env/secret stores
- **Validation**: Reject placeholders and malformed attributes before tokenization

## Contributing & Community

- <a href="https://truvetapublic.github.io/OpenLinkToken/community/contributing.html" target="_blank" rel="noopener noreferrer">Contributing Guide</a> — Branching, PR expectations, coding standards
- <a href="https://truvetapublic.github.io/OpenLinkToken/community/code-of-conduct.html" target="_blank" rel="noopener noreferrer">Code of Conduct</a>

## Documentation

- <a href="https://truvetapublic.github.io/OpenLinkToken/" target="_blank" rel="noopener noreferrer">Documentation Index</a>
- <a href="https://truvetapublic.github.io/OpenLinkToken/quickstarts/" target="_blank" rel="noopener noreferrer">Quickstarts</a>
- <a href="https://truvetapublic.github.io/OpenLinkToken/specification.html" target="_blank" rel="noopener noreferrer">Specification</a>
- <a href="https://truvetapublic.github.io/OpenLinkToken/reference/cli.html" target="_blank" rel="noopener noreferrer">CLI Reference</a>
- <a href="https://truvetapublic.github.io/OpenLinkToken/reference/metadata-format.html" target="_blank" rel="noopener noreferrer">Metadata Format</a>

For issues or support, file an issue in this repository.

<!-- Re-run CI checks -->
