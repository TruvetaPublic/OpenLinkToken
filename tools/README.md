# Development Tools

- [Development Tools](#development-tools)
  - [Decryptor Tools](#decryptor-tools)
  - [Exchange Tools](#exchange-tools)
  - [Hash Tools](#hash-tools)
  - [Mock Data Tools](#mock-data-tools)
  - [Interoperability Tools](#interoperability-tools)
  - [Multi-Language Sync Tool](#multi-language-sync-tool)
    - [Overview](#overview)
    - [Usage](#usage)
      - [Command Line Interface](#command-line-interface)
      - [Shell Wrapper](#shell-wrapper)
      - [GitHub Actions Integration](#github-actions-integration)
    - [Configuration](#configuration)
    - [Output Formats](#output-formats)
      - [Console Format (Default)](#console-format-default)
      - [GitHub Checklist Format](#github-checklist-format)
      - [JSON Format](#json-format)
    - [Workflow Integration](#workflow-integration)
    - [Related Files](#related-files)

## Decryptor Tools

### CSV Token Decryptor

Use `tools/decryptor/decryptor.py` to decrypt token CSV files for inspection or
interoperability checks. The script supports both legacy base64 AES-GCM tokens
and canonical `olt.V1.` JWE-wrapped tokens.

```bash
python tools/decryptor/decryptor.py \
  --encryption-key "$ENCRYPTION_KEY" \
  --input-file encrypted_tokens.csv \
  --output-file decrypted_tokens.csv
```

Input CSV files are expected to contain `RuleId`, `Token`, and `RecordId`
columns. The tool depends on `pycryptodome`, and JWE token support also
requires `jwcrypto`.

## Exchange Tools

### Initiating an Exchange

Use `olt initiate-exchange` to create an encrypted exchange artifact for
the sender key and the partner's public key.

```bash
# Read the partner public key from a file
olt initiate-exchange \
  --public-key partner.public.pem \
  --name sender-q2

# Read the same partner public key from stdin instead
cat partner.public.pem | olt initiate-exchange \
  --public-key-stdin \
  --name sender-q2

# Read both keys by environment-variable reference in one command
OLT_PARTNER_PUBLIC_KEY="$(az keyvault secret show --vault-name my-vault --name partner-public-key --query value -o tsv)" \
OLT_SENDER_PRIVATE_KEY="$(az keyvault secret show --vault-name my-vault --name sender-private-key --query value -o tsv)" \
olt initiate-exchange \
  --public-key-env OLT_PARTNER_PUBLIC_KEY \
  --sender-private-key-env OLT_SENDER_PRIVATE_KEY \
  --name sender-q2

# Read a pre-existing hashing secret from an environment variable instead of argv
OLT_HASHING_SECRET="$(az keyvault secret show --vault-name my-vault --name hashing-secret --query value -o tsv)" \
olt initiate-exchange \
  --public-key partner.public.pem \
  --hashingsecret-env OLT_HASHING_SECRET \
  --name sender-q2
```

`--public-key-stdin` is an alternative to `--public-key PATH`, not a
replacement for the existing file-based flow.

`--public-key-env ENV_VAR` and `--sender-private-key-env ENV_VAR` let you pass
two independent key references in one command without relying on a shared stdin
stream. When `--sender-private-key-env` is used, the sender key stays in memory
for the command run and Open Link Token does not write local sender key files.

For pre-existing hashing secrets, prefer `--hashingsecret-env ENV_VAR` or
`--hashingsecret-stdin` over `--hashingsecret` so the secret does not appear in
shell history or process arguments. Because stdin can only be consumed once per
command, `--hashingsecret-stdin` cannot be combined with `--public-key-stdin`.

### Exchange Secret Validation

Use `tools/exchange/validate_exchange_secret.py` to verify that an
`olt initiate-exchange` exchange artifact can actually be decrypted with
either matching private key.

```bash
# Let the validator resolve a matching sender or recipient private key from ~/.openlinktoken/
python tools/exchange/validate_exchange_secret.py \
  --exchange-config sender-q2.exchange.json

# Validate with an explicit sender or recipient private key PEM
python tools/exchange/validate_exchange_secret.py \
  --exchange-config sender-q2.exchange.json \
  --private-key ~/.openlinktoken/recipient-org.private.pem

# Validate with the same private key PEM provided on stdin instead
cat ~/.openlinktoken/recipient-org.private.pem | \
  python tools/exchange/validate_exchange_secret.py \
    --exchange-config sender-q2.exchange.json \
    --private-key-stdin
```

The exchange artifact is a version 1 multi-recipient JWE JSON envelope with
top-level `version`, `protected`, `iv`, `ciphertext`, `tag`, and `recipients`
fields.
The validator accepts `--expected-secret` for an explicit pass/fail comparison
after decryption. If `--private-key` is omitted, it scans `~/.openlinktoken/` for a
private key whose fingerprint-derived `kid` matches one of the JWE recipients.
`--private-key-stdin` is an alternative to `--private-key PATH`, so both the
existing file-based option and stdin-based secret handling remain supported.

## Hash Tools

### Secret Hash Calculator

Use `tools/hash/hash_calculator.py` to compute the SHA-256 secret hashes that
Open Link Token includes in metadata output.

```bash
python tools/hash/hash_calculator.py \
  --hashing-secret "$HASHING_SECRET" \
  --encryption-key "$ENCRYPTION_KEY" \
  --output-format json
```

Supported output formats are `table`, `json`, and `simple`. The companion
`tools/hash/test_hash_calculator.py` script exercises the calculator against
known values and command-line execution behavior.

## Mock Data Tools

### CSV Test Data Generator

Use `tools/mockdata/data_generator.py` to generate CSV files with realistic
person-like records for local testing.

```bash
python tools/mockdata/data_generator.py 1000 0.05 test_data.csv
```

Arguments are:

- number of rows to generate
- repeat probability for duplicate-person scenarios
- output CSV path

For the default quick-start flow, `tools/mockdata/generate.sh` runs the
generator through `uv` with `faker` provided automatically.

## Interoperability Tools

The `tools/interoperability/` directory contains cross-language validation
checks for the Java core library and the Python implementation.

### CLI Parity Test

Use `tools/interoperability/cli_parity_test.py` to confirm the Python CLI still
exposes the expected commands, help output, and version behavior.

```bash
python tools/interoperability/cli_parity_test.py
```

### Multi-Language Token Interoperability Test

Use `tools/interoperability/multi_language_interoperability_test.py` to compare
Python tokenization output against the Java core-library harness and verify
known deterministic fixture values.

```bash
cd lib/java
mvn -pl openlinktoken -DskipTests test-compile
cd ..
python tools/interoperability/multi_language_interoperability_test.py
```

For more detail on these checks, see `tools/interoperability/README.md`.

## Multi-Language Sync Tool

### Overview

The multi-language sync tool detects changes in any supported language (Java, Python, or Node.js) and identifies corresponding files in the other languages that need updating. It tracks sync progress across commits in a PR and posts checklists to GitHub PRs via GitHub Actions.

Use this tool to ensure parity between Java, Python, and future language implementations as they evolve.

### Usage

#### Command Line Interface

```bash
# Basic sync check (compares against HEAD~1)
python3 tools/multi_language_syncer.py

# Check against specific branch/commit
python3 tools/multi_language_syncer.py --since origin/main

# Generate GitHub-style checklist
python3 tools/multi_language_syncer.py --format github-checklist

# Output as JSON for automation
python3 tools/multi_language_syncer.py --format json

# Run health check
python3 tools/multi_language_syncer.py --health-check
```

#### Shell Wrapper

`sync-check.sh` wraps the Python tool with convenience options and optional GitHub issue creation:

```bash
# Basic usage
./tools/sync-check.sh

# Check PR against main branch with checklist output
./tools/sync-check.sh --since origin/main --format github-checklist

# Check only Java/Python sync
./tools/sync-check.sh --languages java,python --since origin/main

# Generate JSON report
./tools/sync-check.sh --format json --since origin/main

# Create GitHub issue with sync tasks (requires gh CLI)
./tools/sync-check.sh --issue --format github-checklist --since origin/main

# Quiet mode for scripting
./tools/sync-check.sh --quiet --format json
```

#### GitHub Actions Integration

The tool runs automatically on pull requests via `.github/workflows/multi-language-sync.yml`:

- **Triggers**: On PR open, synchronize, or reopen
- **Scope**: Changes to Java files in `lib/java/` or Python files in `lib/python/`
- **Output**: Automated PR comments with progress tracking and checklists
- **Permissions**: Requires `issues: write` and `pull-requests: write` permissions

### Configuration

Language paths are defined directly in `multi_language_syncer.py`:

```python
LANGUAGES = {
    'java':   {'path': 'lib/java/openlinktoken/src/main/java/org/openlinktoken/', ...},
    'python': {'path': 'lib/python/openlinktoken/src/main/openlinktoken/', ...},
}
```

An optional `tools/multi-language-mapping.json` file can supply `ignore_patterns`:

```json
{
  "ignore_patterns": ["**/generated/**", "**/target/**", "**/__pycache__/**"]
}
```

### Output Formats

#### Console Format (Default)

```text
Multi-Language Sync Report
============================================================

JAVA: 1 files changed
PYTHON: 0 files changed

============================================================
Sync Requirements:

Source: lib/java/openlinktoken/src/main/java/org/openlinktoken/TokenGenerator.java
  → python: ✓ lib/python/openlinktoken/src/main/openlinktoken/token_generator.py
  → nodejs: ✗ lib/nodejs/openlinktoken/src/TokenGenerator.ts
```

#### GitHub Checklist Format

```markdown
## Multi-Language Sync Required (1/2 completed)

### 🔹 From JAVA

#### 📁 `lib/java/openlinktoken/src/.../TokenGenerator.java`

- [x] **✓🔄 PYTHON**: `lib/python/openlinktoken/src/main/openlinktoken/token_generator.py`
- [ ] **✗⏳ NODEJS**: `lib/nodejs/openlinktoken/src/TokenGenerator.ts`

✅ **Progress**: 1 of 2 items completed
```

#### JSON Format

```json
{
  "sync_requirements": [...],
  "all_changes": {
    "java": ["lib/java/openlinktoken/.../TokenGenerator.java"],
    "python": [],
    "nodejs": []
  }
}
```

### Workflow Integration

The `.github/workflows/multi-language-sync.yml` workflow provides:

1. **Change Detection**: Compares against PR base branch for accurate change detection
2. **Progress Tracking**: Tracks completion across multiple commits in the same PR
3. **Comment Management**: Replaces previous sync comments to keep PR history clean
4. **Non-blocking**: Posts informational comments without hard-failing the workflow

### Related Files

- `tools/multi_language_syncer.py` - Main tool implementation
- `tools/multi-language-mapping.json` - Optional configuration (ignore patterns)
- `tools/sync-check.sh` - Shell wrapper script for CI and local use
- `.github/workflows/multi-language-sync.yml` - GitHub Actions workflow
