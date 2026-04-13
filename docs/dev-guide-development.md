# OpenLinkToken Development Guide

This guide centralizes contributor-facing information. It covers local setup, language-specific build instructions, development environment, versioning, and key contribution workflows.

> **For AI Coding Agents**: See the [Copilot Instructions](../.github/copilot-instructions.md) for comprehensive guidance on working with this codebase, including security guidelines, PR standards, and debugging tips.

## At a Glance

- Three packages: Java core (Maven), Python core, Python CLI, plus PySpark bridge
- Java uses multi-module Maven structure with parent POM at `lib/java/pom.xml`
- Core packages (`openlinktoken`) contain pure tokenization logic with minimal dependencies
- Python CLI package (`openlinktoken-cli`) contains I/O implementations (CSV, Parquet, JSON) and command-line interface
- Deterministic token generation logic is equivalent across languages
- PySpark bridge enables large-scale distributed token generation & overlap analysis
- Use this guide for environment setup & day-to-day development
- Use the Token & Attribute Registration guide for extending functionality

## Contents

- [OpenLinkToken Development Guide](#openlinktoken-development-guide)
  - [At a Glance](#at-a-glance)
  - [Contents](#contents)
  - [Prerequisites](#prerequisites)
  - [Project Layout](#project-layout)
  - [Language Development (Java, Python \& PySpark)](#language-development-java-python--pyspark)
    - [Java](#java)
    - [Python](#python)
    - [PySpark Bridge](#pyspark-bridge)
    - [Multi-Language Sync Tool](#multi-language-sync-tool)
    - [Cross-language Tips](#cross-language-tips)
  - [Coding Standards](#coding-standards)
    - [Java Style Guidelines](#java-style-guidelines)
    - [Python Style Guidelines](#python-style-guidelines)
    - [Self-Explanatory Code \& Comments](#self-explanatory-code--comments)
    - [Security Best Practices](#security-best-practices)
  - [Token Processing Modes](#token-processing-modes)
  - [Token \& Attribute Registration](#token--attribute-registration)
    - [When to Use](#when-to-use)
    - [Java Registration (ServiceLoader SPI)](#java-registration-serviceloader-spi)
    - [Python Registration](#python-registration)
    - [Cross-language Parity Checklist](#cross-language-parity-checklist)
    - [Quick Reference](#quick-reference)
      - [Common Generic Attributes (ready to reuse)](#common-generic-attributes-ready-to-reuse)
  - [Building \& Testing](#building--testing)
    - [Full Multi-language Build](#full-multi-language-build)
    - [Docker Image](#docker-image)
  - [Running the Tool (CLI)](#running-the-tool-cli)
  - [Development Container](#development-container)
  - [Version Bumping Policy](#version-bumping-policy)
  - [Contributing Checklist](#contributing-checklist)
  - [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Tool              | Recommended Version | Notes                                                                                                |
| ----------------- | ------------------- | ---------------------------------------------------------------------------------------------------- |
| Java JDK          | 21.x                | Required for Java core library builds (outputs Java 17 compatible bytecode); the CLI is Python-based |
| Maven             | 3.8+                | Build Java artifacts (`mvn clean install`)                                                           |
| Python            | 3.10+               | For Python implementation & scripts                                                                  |
| uv                | Latest              | Manage Python dependencies (install: `curl -LsSf https://astral.sh/uv/install.sh \| sh`)             |
| Docker (optional) | Latest              | Build container image                                                                                |

## Project Layout

```text
lib/
  java/
    pom.xml            # Parent POM (multi-module Maven build)
    openlinktoken/         # Core tokenization library (pure logic, minimal dependencies)
  python/
    openlinktoken/         # Core tokenization library
    openlinktoken-cli/     # CLI application with I/O support
    openlinktoken-pyspark/ # PySpark bridge for distributed processing
resources/             # Sample and test data
tools/                 # Utility scripts (hash calculator, mock data, etc.)
docs/                  # All developer documentation (this file!)
```

Key Docs:

- Development processes below

## Language Development (Java, Python & PySpark)

This section combines the previous standalone Java and Python development sections for easier cross-language parity review.

### Java

Prerequisites:

- Java 21 SDK or higher (core library JAR output is Java 17 compatible)
- Maven 3.8.8 or higher

Build all modules (from `lib/java`):

```shell
cd lib/java && mvn clean install
```

Build individual modules:

```shell
# Core library only
cd lib/java/openlinktoken && mvn clean install
```

Resulting JARs:

- Core library: `lib/java/openlinktoken/target/openlinktoken-*.jar`

Using as Maven dependencies:

```xml
<!-- Core library (tokenization logic only) -->
<dependency>
  <groupId>org.openlinktoken</groupId>
  <artifactId>openlinktoken</artifactId>
  <version>${openlinktoken.version}</version>
</dependency>
```

Programmatic API (simplified):

```java
List<TokenTransformer> transformers = Arrays.asList(
  new HashTokenTransformer("your-hashing-secret"),
  new EncryptTokenTransformer("your-encryption-key")
);
TokenGenerator generator = new TokenGenerator(new TokenDefinition(), new SHA256Tokenizer(transformers));
TokenGeneratorResult result = generator.getAllTokens(personAttributes);
```

Testing:

```shell
# Test all modules
cd lib/java && mvn test

# Test with coverage report
cd lib/java && mvn clean test jacoco:report
# Coverage report: openlinktoken/target/site/jacoco/index.html
```

Style & docs:

```shell
mvn checkstyle:check
mvn clean javadoc:javadoc
```

Notes:

- Unicode normalized to ASCII equivalents.

### Python

Prerequisites:

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

Create & activate virtual environment (at repository root):

```shell
uv venv .venv
source .venv/bin/activate
```

Install dependencies:

```shell
# Core library
cd lib/python/openlinktoken
uv pip install -r requirements.txt -r dev-requirements.txt

# For CLI support, also install openlinktoken-cli
cd ../openlinktoken-cli
uv pip install -r requirements.txt -r dev-requirements.txt
```

Editable install for local development:

```shell
# Install core library
cd lib/python/openlinktoken && uv pip install -e .

# Install CLI (includes core as dependency)
cd lib/python/openlinktoken-cli && uv pip install -e .
```

#### Build a Self-Contained CLI Locally

For parity with the release artifacts, build the PyInstaller executable with Python 3.11. PyInstaller bundles the
interpreter used at build time, and `.github/workflows/build-openlinktoken-cli.yml` currently builds the published
artifacts with Python 3.11.

From the repository root, activate your virtual environment (`.\.venv\Scripts\Activate.ps1` on Windows PowerShell)
and install the build dependencies:

```shell
uv pip install -e lib/python/openlinktoken
uv pip install -r lib/python/openlinktoken-cli/pyinstaller-requirements.txt
uv pip install -r lib/python/openlinktoken-cli/requirements.txt
uv pip install -e lib/python/openlinktoken-cli --no-deps
```

Build the executable:

```shell
# Linux / Windows
pyinstaller --clean --noconfirm lib/python/openlinktoken-cli/openlinktoken-cli.spec

# macOS universal2 (Intel + Apple Silicon)
pyinstaller --clean --noconfirm --target-arch universal2 lib/python/openlinktoken-cli/openlinktoken-cli.spec
```

The built executable is written to `dist/openlinktoken` (`dist/openlinktoken.exe` on Windows). Intermediate files are written
to `build/`.

Smoke-test the local build before packaging it:

```shell
mkdir -p smoke
cp resources/sample.csv smoke/input.csv
./dist/olt tokenize -i smoke/input.csv -t csv -o smoke/out.csv -h secret
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path smoke | Out-Null
Copy-Item resources\sample.csv smoke\input.csv
.\dist\openlinktoken.exe tokenize -i smoke\input.csv -t csv -o smoke\out.csv -h secret
```

If you also want the same ZIP and checksum bundle produced by the release workflow, run:

```shell
python -m openlinktoken_cli.util.release_assets \
  --version 2.0.0-alpha \
  --runner-os Linux \
  --dist-dir dist \
  --output-dir release-assets
```

Use `--runner-os macOS` or `--runner-os Windows` for those platforms. The helper writes the updater-ready raw binary,
the downloadable ZIP, and `.sha256` sidecars to `release-assets/`.

CLI usage (from project root):

```shell
# After installing openlinktoken-cli
python -m openlinktoken_cli.main package [OPTIONS]
```

Arguments are consistent with the Java core library's tokenization logic.

Example:

```shell
# After installing openlinktoken-cli
python -m openlinktoken_cli.main package \
  -i resources/sample.csv -t csv -o resources/output.csv \
  -h "HashingKey" -e "Secret-Encryption-Key-Goes-Here."
```

Programmatic API (simplified):

```python
transformers = [
    HashTokenTransformer("your-hashing-secret"),
    EncryptTokenTransformer("your-encryption-key")
]
with PersonAttributesCSVReader("input.csv") as reader, \
     PersonAttributesCSVWriter("output.csv") as writer:
    PersonAttributesProcessor.process(reader, writer, transformers, metadata)
```

Testing:

```shell
# Core library tests
cd lib/python/openlinktoken
PYTHONPATH=src/main pytest src/test

# CLI tests
cd lib/python/openlinktoken-cli
PYTHONPATH=src/main pytest src/test
```

Key dependencies:

- Core: cryptography
- CLI: pandas, pyarrow (for Parquet)

Parity notes:

- Outputs identical tokens to Java for the same normalized input & secrets.
- Maintain consistency when adding new token or attribute logic.

Contributing notes:

- Follow PEP 8, add type hints.
- Keep normalization and token logic in sync with Java core library.

### PySpark Bridge

The PySpark bridge (`lib/python/openlinktoken-pyspark`) provides a distributed processing interface for generating tokens and performing dataset overlap analysis using Spark DataFrames.

Purpose:

- Efficient token generation on large datasets (partitioned execution)
- Supports custom token definitions in Spark pipelines
- Provides overlap analysis utilities (`OverlapAnalyzer`) for measuring cohort intersection

Prerequisites:

- Python 3.10+

**Version Compatibility (choose based on your Java version):**

| Java Version | PySpark Version | PyArrow Version | Notes                                           |
| ------------ | --------------- | --------------- | ----------------------------------------------- |
| **Java 21**  | **4.0.1+**      | **17.0.0+**     | **Recommended** - Native Java 21 support        |
| Java 8-17    | 3.5.x           | <20             | Legacy support - use if you cannot upgrade Java |

Install (from repo root):

```shell
uv pip install -r lib/python/openlinktoken-pyspark/requirements.txt -r lib/python/openlinktoken-pyspark/dev-requirements.txt
uv pip install -e lib/python/openlinktoken-pyspark
```

Basic Usage:

```python
from pyspark.sql import SparkSession
from openlinktoken_pyspark import OpenLinkTokenProcessor

spark = SparkSession.builder.master("local[2]").appName("OpenLinkTokenExample").getOrCreate()
df = spark.read.csv("people.csv", header=True)
processor = OpenLinkTokenProcessor("HashingKey", "Secret-Encryption-Key-Goes-Here.")
token_df = processor.process_dataframe(df)
token_df.show()
```

Custom Token Definitions (example adding T6):

```python
from openlinktoken_pyspark import OpenLinkTokenProcessor
from openlinktoken_pyspark.notebook_helpers import TokenBuilder, CustomTokenDefinition

t6 = TokenBuilder("T6") \
  .add("last_name", "T|U") \
  .add("first_name", "T|U") \
  .add("birth_date", "T|D") \
  .build()

definition = CustomTokenDefinition().add_token(t6)
processor = OpenLinkTokenProcessor(
  hashing_secret="HashingKey",
  encryption_key="Secret-Encryption-Key-Goes-Here.",
  token_definition=definition
)
token_df = processor.process_dataframe(df)
```

Testing:

```shell
cd lib/python/openlinktoken-pyspark
pytest src/test
```

Notebook Guides:

- See `lib/python/openlinktoken-pyspark/notebooks/` for example workflows (custom tokens & overlap analysis).

### Multi-Language Sync Tool

The sync tool ([tools/multi_language_syncer.py](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/tools/multi_language_syncer.py)) detects changes across all supported languages (Java, Python, Node.js) and produces a cross-language checklist showing which corresponding files need updating. It is bidirectional — changes originating in any language trigger sync items for the others.

Key concepts:

- Language paths are configured directly in `multi_language_syncer.py` under the `LANGUAGES` dict.
- An optional [tools/multi-language-mapping.json](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/tools/multi-language-mapping.json) supplies `ignore_patterns`.
- Sync status logic: A target file is considered up-to-date if it was modified after the source file within the same PR (commit timestamp comparison).
- Progress is tracked across all commits in a PR so the checklist reflects incremental work.

Usage examples:

```bash
python3 tools/multi_language_syncer.py --format console
python3 tools/multi_language_syncer.py --format github-checklist --since origin/main
python3 tools/multi_language_syncer.py --health-check
```

CI integration: The GitHub Actions workflow (`.github/workflows/multi-language-sync.yml`) posts an informational checklist comment on PRs. It does not hard-fail; it tracks progress.

When adding attributes/tokens: update all applicable language implementations, run the sync tool to verify, and ensure the checklist shows complete before merging.

### Cross-language Tips

| Task            | Java Command                       | Python Command                     |
| --------------- | ---------------------------------- | ---------------------------------- |
| Build / Package | `cd lib/java && mvn clean install` | `uv pip install -e .`              |
| Run Tests       | `mvn test`                         | `pytest src/test`                  |
| Lint / Style    | `mvn checkstyle:check`             | (pep8 / flake8 if configured)      |
| Run CLI         | N/A (use Python CLI)               | `olt package ...`                  |
| Add Token       | SPI entry & class                  | new module in `tokens/definitions` |
| Add Attribute   | SPI entry & class                  | class + loader import              |

Maintain the same functional behavior and normalization between languages.

## Coding Standards

This project follows established coding conventions to ensure consistency, maintainability, and security across the
codebase. Detailed guidelines are maintained in `.github/instructions/` and automatically applied by AI coding
assistants.

### Java Style Guidelines

**Core Principles:**

- **Always use direct imports**: Never use fully qualified class names in code (e.g., `new SHA256Tokenizer()` instead
  of `new org.openlinktoken.tokens.tokenizer.SHA256Tokenizer()`). Add import statements at the top of the file.
- **Follow Google's Java Style Guide**: Use `UpperCamelCase` for classes, `lowerCamelCase` for methods/variables,
  `UPPER_SNAKE_CASE` for constants, `lowercase` for packages.
- **Leverage Lombok**: Use `@Builder`, `@NonNull`, `@Data`, `@Value`, `@Slf4j` to reduce boilerplate.
- **Prefer immutability**: Make classes and fields `final` where possible. Use `List.of()`, `Map.of()`,
  `Stream.toList()` for immutable collections.
- **Use modern Java features**: Pattern matching for `instanceof`, `var` for local variables (when type is clear),
  `Optional<T>` instead of null.

**Verification:**

```bash
# Run Checkstyle checks
cd lib/java && mvn checkstyle:check

# Generate Javadoc
mvn clean javadoc:javadoc
```

**Common Issues:**

- Resource management: Always use try-with-resources for closeable resources
- Equality checks: Use `.equals()` or `Objects.equals()` for object comparison (not `==`)
- Avoid magic numbers: Extract repeated values to named constants

**See:** [`.github/instructions/java.instructions.md`](../.github/instructions/java.instructions.md) for complete
guidelines.

### Python Style Guidelines

**Core Principles:**

- **Follow PEP 8**: Maximum line length 120 characters (extended for PySpark chains), 4-space indentation.
- **Type hints required**: Use `typing` module for all function signatures (e.g., `List[str]`, `Dict[str, int]`,
  `Optional[T]`).
- **Docstrings required**: Follow PEP 257 conventions with Args, Returns, and Raises sections.
- **Clean imports**: Remove unused imports/variables, organize in groups (standard library → third-party → local).
- **PySpark-specific**: Always use direct imports (`from pyspark.sql.functions import col, lit, when`) instead of
  `import pyspark.sql.functions as F`.

**PySpark Method Chaining:**

```python
# CORRECT - additional indentation for chained methods
result_df = (
    source_df
        .select(USER_ID, ORDER_ID, PRODUCT_ID)
        .withColumn(STATUS_CODE, lit(DEFAULT_STATUS))
        .filter(col(IS_ACTIVE) == True)
)
```

**Verification:**

```bash
# Run tests with coverage
cd lib/python/openlinktoken && pytest --cov=openlinktoken --cov-report=term

# Auto-remove unused imports (if needed)
autoflake --remove-all-unused-imports --remove-unused-variables --in-place file.py
```

**See:** [`.github/instructions/python.instructions.md`](../.github/instructions/python.instructions.md) for complete
guidelines.

### Self-Explanatory Code & Comments

**Core Principle:** Write code that speaks for itself. Comment only when necessary to explain WHY, not WHAT.

**When to comment:**

- ✅ **Complex business logic** — Explain the reasoning behind non-obvious calculations or algorithms
- ✅ **Regex patterns** — Describe what the pattern matches
- ✅ **API constraints** — Document external limitations or gotchas
- ✅ **Public APIs** — Use JavaDoc/docstrings for all public methods
- ✅ **Annotations** — Use `TODO`, `FIXME`, `SECURITY`, `WARNING`, etc. for important notes

**When NOT to comment:**

- ❌ **Obvious statements** — Don't repeat what the code clearly does
- ❌ **Redundant explanations** — If a good variable/method name makes it clear, no comment needed
- ❌ **Outdated information** — Remove comments that no longer match the code
- ❌ **Dead code** — Delete commented-out code instead of leaving it in
- ❌ **Changelog entries** — Use git history, not inline comments

**Examples:**

```java
// GOOD: Explains WHY this specific calculation
// Apply progressive tax brackets: 10% up to 10k, 20% above
final tax = calculateProgressiveTax(income, List.of(0.1, 0.2), List.of(10000));

// BAD: States the obvious
counter++; // Increment counter by one
```

**See:** [`.github/instructions/self-explanatory-code-commenting.instructions.md`](../.github/instructions/self-explanatory-code-commenting.instructions.md) for detailed examples.

### Security Best Practices

**Based on OWASP Top 10:**

1. **Access Control (A01):** Deny by default, enforce least privilege, validate all access checks
2. **Cryptographic Failures (A02):**
   - Use Argon2/bcrypt for password hashing (never MD5/SHA-1)
   - Always use HTTPS for network requests
   - Encrypt data at rest with AES-256
   - **Never hardcode secrets** — Use environment variables or secrets management services
3. **Injection (A03):**
   - Use parameterized queries for SQL (never string concatenation)
   - Sanitize command-line input
   - Context-aware output encoding for XSS prevention (prefer `.textContent` over `.innerHTML`)
4. **Security Misconfiguration (A05-A06):**
   - Disable verbose error messages in production
   - Set security headers: `Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options`
   - Keep dependencies up-to-date, run vulnerability scanners (`npm audit`, `pip-audit`, Snyk)
5. **Authentication Failures (A07):** Secure session management, rate limiting, account lockout
6. **Data Integrity (A08):** Avoid insecure deserialization, validate untrusted data

**OpenLinkToken-specific:**

- Hashing and encryption keys must only appear in test files with dummy values
- SSN validation logic is public, but never log actual SSN values
- Metadata files contain SHA-256 hashes of secrets (for audit), not the secrets themselves

**See:** [`.github/instructions/security-and-owasp.instructions.md`](../.github/instructions/security-and-owasp.instructions.md) for comprehensive security guidelines.

## Token Processing Modes

OpenLinkToken supports three processing modes across Java, Python, and the PySpark bridge. These modes determine how raw token signatures are transformed:

| Mode      | Secrets Required                | Transform Pipeline                                | Output Example (T1)                  | Deterministic Across Runs | Recommended Use                                                   |
| --------- | ------------------------------- | ------------------------------------------------- | ------------------------------------ | ------------------------- | ----------------------------------------------------------------- |
| Plain     | None (`tokenize --demo-mode`)   | Concatenate normalized attribute expressions only | `DOE\|JOHN\|1990-01-15\|MALE\|98101` | Yes (given same input)    | Debugging, rule design, docs demos                                |
| Tokenize  | Hashing secret only             | HMAC-SHA256(signature)                            | 64 hex chars (SHA-256 digest)        | Yes                       | Internal overlap analysis against decrypted partner token outputs |
| Encrypted | Hashing secret + encryption key | HMAC-SHA256 → AES-256-GCM (random IV per token)   | Base64 blob (length varies)          | Yes (post-decrypt hash)   | Production / privacy-preserving use and external token exchange   |

Notes:

- The underlying signature (before hashing) is produced by ordered attribute expressions for each token rule (e.g., T1→T5 or custom T6+). Plain mode exposes this directly for inspection.
- Encryption uses AES-256-GCM with a random IV; identical hashed inputs yield different encrypted outputs each run. Matching encrypted tokens across datasets therefore requires either: (a) decryption with the shared key (to reach the tokenized representation) or (b) using the `tokenize` subcommand specifically for overlap workflows. Do NOT attempt to match encrypted blobs directly.
- Tokenizer polymorphism: Java & Python `TokenGenerator` accept an injectable tokenizer. Defaults to SHA-256; when plain mode is active a `PassthroughTokenizer` is used so downstream transformers (if any) receive the raw signature.
- Security: Plain and tokenized modes reduce protection. Never use plain mode for sharing PHI; tokenized output may leak structural frequency information. Encrypted mode is required for external distribution; tokenized datasets should remain internal and are typically used to join against decrypted partner tokens for overlap analysis.

## Token & Attribute Registration

This section unifies Java and Python guidance for adding new Tokens and Attributes.

### When to Use

- Adding a new token generation rule (Token)
- Adding a new source person attribute (Attribute)
- Refactoring or renaming existing implementations

### Java Registration (ServiceLoader SPI)

Java uses the standard `ServiceLoader` discovery mechanism.

Steps (Token example):

1. Create class in `org.openlinktoken.tokens.definitions` extending `Token`.
2. Implement required abstract methods (identifier, definition, etc.).
3. Add fully qualified class name to: `lib/java/openlinktoken/src/main/resources/META-INF/services/org.openlinktoken.tokens.Token` (one per line).
4. Run `mvn clean install` and add/adjust tests.

Attribute steps are identical except:

- Class extends `org.openlinktoken.attributes.Attribute` (e.g., in `attributes.person`).
- Register in: `lib/java/openlinktoken/src/main/resources/META-INF/services/org.openlinktoken.attributes.Attribute`.

Guidelines:

- No blank lines or comments in service files.
- Keep entries sorted alphabetically (recommended for diffs).
- Update service file if class is renamed/moved.

Troubleshooting:

- Not loading? Check for: typo in service file, missing no-arg constructor, class not public, duplicate class names.

### Python Registration

Python uses two mechanisms:

1. Dynamic discovery for Tokens in `openlinktoken/tokens/definitions`.
2. Explicit inclusion for Attributes via `attribute_loader.py`.

Add a Token:

1. Create `lib/python/openlinktoken/src/main/openlinktoken/tokens/definitions/t6_token.py` (example).
2. Define a class inheriting `Token` with `get_identifier()` & `get_definition()`.
3. Ensure file and class names are unique and public.
4. Run `pytest src/test` to verify auto-discovery.

Add an Attribute:

1. Create module, e.g., `openlinktoken/attributes/person/middle_name_attribute.py`.
2. Implement subclass of `Attribute`.
3. In `attribute_loader.py`, import the class and add an instance inside `AttributeLoader.load()`.

Python Troubleshooting:

- If a Token isn’t picked up: ensure directory has `__init__.py` and class file matches naming conventions.
- If an Attribute isn’t loaded: confirm it’s imported and added to the returned set.

### Cross-language Parity Checklist

- Same normalization logic unaffected.
- Matching token definitions (order & components) across Java & Python.
- Tests confirming identical hash/encryption output for shared fixtures.

### Quick Reference

| Operation             | Java File(s)                     | Python File(s)                                              |
| --------------------- | -------------------------------- | ----------------------------------------------------------- |
| Add Token             | `META-INF/services/...Token`     | `tokens/definitions/<new>_token.py`                         |
| Add Attribute         | `META-INF/services/...Attribute` | `attributes/.../<new>_attribute.py` + `attribute_loader.py` |
| Rename Implementation | Update service file entries      | Rename file & ensure loader/discovery still finds it        |

Maintain tests to guard consistency between languages.

#### Common Generic Attributes (ready to reuse)

Available in both Java and Python for custom rules:

- `Integer` – signed integers; trims whitespace; parse/stringify normalization.
- `Decimal` – floating point with optional scientific notation; trims then parses.
- `Year` – 4-digit calendar year; enforces regex then delegates to integer base.
- `Date` – normalizes to `yyyy-MM-dd` from common date inputs.
- `String` – trimmed non-empty strings.
- `RecordId` – identifier passthrough.

## Building & Testing

### Full Multi-language Build

(Useful in CI or before PR submission.)

```shell
# Java (builds core module)
(cd lib/java && mvn clean install)

# Python core
(cd lib/python/openlinktoken && pytest src/test)

# Python CLI
(cd lib/python/openlinktoken-cli && pytest src/test)

# PySpark Bridge
(cd lib/python/openlinktoken-pyspark && pytest src/test)
```

### Docker Image

```shell
docker build . -t openlinktoken
```

## Running the Tool (CLI)

The CLI is provided by the Python `openlinktoken-cli` package.

Minimum required arguments:

```shell
# Python
python -m openlinktoken_cli.main package -i input.csv -t csv -o output.csv --exchange-config ./openlinktoken-YYYY-MM-DD.exchange.json --private-key ~/.openlinktoken/openlinktoken-YYYY-MM-DD.private.pem
```

Arguments:

| Flag                 | Description                                     |
| -------------------- | ----------------------------------------------- |
| `-t, --type`         | Input file type (`csv` or `parquet`)            |
| `-i, --input`        | Input file path                                 |
| `-o, --output`       | Output file path                                |
| `-ot, --output-type` | (Optional) Output file type (defaults to input) |
| `--exchange-config`  | Exchange config JSON path                       |
| `--private-key`      | Private key PEM used to decrypt the config      |
| `--private-key-env`  | Environment variable containing the private key |

### Key Pair Generation

The `generate-key-pair` subcommand generates an ECDH public/private key pair:

```shell
olt generate-key-pair --curve P-256 --name my-key
```

Writes:

- `~/.openlinktoken/<name>.private.pem` — PKCS#8 PEM (permissions `600`)
- `~/.openlinktoken/<name>.public.pem` — SubjectPublicKeyInfo PEM (permissions `644`)

`--curve` options: `P-256` (default), `P-384`, `P-521`. Use `--force` to overwrite existing keys.

## Local Extension Development

The `openlinktoken-ext-hello-world` package in `lib/python/openlinktoken_ext_hello_world/` is the canonical reference extension. Use it as your starting point when developing a new extension locally.

### Setup

Install the hello-world extension in editable mode so the CLI discovers it via the `openlinktoken.extensions` entry-point group:

```shell
source /home/vscode/.local/share/openlinktoken/.venv/bin/activate

# Install the CLI in editable mode (if not already)
cd lib/python/openlinktoken-cli && uv pip install -e .

# Install the reference extension in editable mode
cd lib/python/openlinktoken_ext_hello_world && uv pip install -e .
```

After the editable install, the entry point is registered in the active Python environment. The CLI discovers it at startup with no further configuration.

### Manual testing: editable install (fast path)

The editable install registers the entry point immediately — no build step required.

```shell
cd lib/python/openlinktoken_ext_hello_world
uv pip install -e .

# Verify it appears in help and the extension list
olt --help
olt extension list

# Run it
olt hello-world hello --name Alice
# → Hello, Alice
olt hello-world bye --name Bob
# → Bye, Bob
```

### Manual testing: wheel install (full pipeline)

Use this to test the complete `extension install` flow, including download, unpacking, and registry write.

```shell
cd lib/python/openlinktoken_ext_hello_world

# Build the wheel
pip install build && python -m build

# Install via the extension command (--yes skips the security prompt; use an absolute path)
olt extension install file://$(pwd)/dist/openlinktoken_ext_hello_world-1.0.0-py3-none-any.whl --yes

# Confirm it appears in the registry
olt extension list

# Run it
olt hello-world hello --name Alice
# → Hello, Alice
olt hello-world bye --name Bob
# → Bye, Bob
```

### Run the extension tests

```shell
cd lib/python/openlinktoken_ext_hello_world && pytest src/test
```

### Developing your own extension

1. Create a new directory for your extension package (mirror the `openlinktoken-hello-world` structure).
2. Implement `OpenLinkTokenExtension` from `openlinktoken_cli.extension`:
   ```python
   from openlinktoken_cli.extension import OpenLinkTokenExtension
   ```
3. Declare the `openlinktoken.extensions` entry point in your `pyproject.toml`:
   ```toml
   [project.entry-points."openlinktoken.extensions"]
   my-ext = "my_package.extension:MyExtension"
   ```
4. Install in editable mode (`uv pip install -e .`) — the CLI picks it up on next invocation.
5. Package with `python -m build` and distribute as a `.whl`.
6. End users install via `olt extension install <url-or-file://path>`.

See `lib/python/openlinktoken_ext_hello_world/README.md` for the full lifecycle walkthrough and `pages/quickstarts/extension-quickstart.md` for a step-by-step guide.

### Extension tests in `openlinktoken-cli`

The loader, registry, and command tests live in:

```
lib/python/openlinktoken-cli/src/test/openlinktoken_cli/extension/
lib/python/openlinktoken-cli/src/test/openlinktoken_cli/commands/test_extension_command.py
```

Run them with:

```shell
cd lib/python/openlinktoken-cli && pytest src/test/openlinktoken_cli/extension src/test/openlinktoken_cli/commands/test_extension_command.py -v
```

## Development Container

A Dev Container configuration provides a reproducible environment with:

- JDK 21
- Maven
- Python & tooling

Open the repository in VS Code and select: "Reopen in Container".

## Version Bumping Policy

All PRs MUST bump the version via `bump2version` (never edit versions manually):

- Bug fix / docs tweak: `bump2version patch`
- Backward-compatible feature: `bump2version minor`
- Breaking change: `bump2version major`

Ensure the working tree is clean before running the command.

## Contributing Checklist

Before opening a PR:

- [ ] Code compiles (`mvn clean install` for Java)
- [ ] Tests pass (Java & Python where changes apply)
- [ ] Added/updated docs if behavior changed
- [ ] Followed [Coding Standards](#coding-standards) (see also [PR Guidelines](../.github/instructions/pull-request.instructions.md))
  - [ ] Java: Direct imports, Checkstyle passing, Javadoc for public APIs
  - [ ] Python: PEP 8, type hints, docstrings, no unused imports
- [ ] Added registration entries (Java SPI files) or loader entries (Python) if new Token/Attribute
- [ ] Bumped version with `bump2version`

## Troubleshooting

| Issue                            | Hint                                                                                |
| -------------------------------- | ----------------------------------------------------------------------------------- |
| Java class not discovered        | Confirm fully qualified name in `META-INF/services/*` file & no trailing spaces     |
| Python attribute not loaded      | Ensure it is imported & added in `attribute_loader.py`                              |
| Token mismatch between languages | Verify hashing & encryption secrets are identical and normalization logic unchanged |
| Build fails on Checkstyle        | Run `mvn -q checkstyle:check` locally & fix warnings                                |
| Import errors or style issues    | See [Coding Standards](#coding-standards) for language-specific guidelines          |

---

Maintainers: Keep this guide updated when changing build, versioning, or extension workflows.
