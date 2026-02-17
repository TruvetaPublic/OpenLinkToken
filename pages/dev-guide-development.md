---
layout: default
---

# OpenToken Development Guide

This guide centralizes contributor-facing information. It covers local setup, language-specific build instructions, development environment, versioning, and key contribution workflows.

> **For AI Coding Agents**: See the [Copilot Instructions](../.github/copilot-instructions.md) for comprehensive guidance on working with this codebase, including security guidelines, PR standards, and debugging tips.

## At a Glance

- Four packages: Java core (Maven), Java CLI (Maven), Python core, Python CLI, plus PySpark bridge
- Java uses multi-module Maven structure with parent POM at `lib/java/pom.xml`
- Core packages (`opentoken`) contain pure tokenization logic with minimal dependencies
- CLI packages (`opentoken-cli`) contain I/O implementations (CSV, Parquet, JSON) and command-line interface
- Deterministic token generation logic is equivalent across languages
- PySpark bridge enables large-scale distributed token generation & overlap analysis
- Use this guide for environment setup & day-to-day development
- Use the Token & Attribute Registration guide for extending functionality

## Contents

- [OpenToken Development Guide](#opentoken-development-guide)
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
  - [Token Processing Modes](#token-processing-modes)
  - [Token \& Attribute Registration](#token--attribute-registration)
    - [When to Use](#when-to-use)
    - [Java Registration (ServiceLoader SPI)](#java-registration-serviceloader-spi)
    - [Python Registration](#python-registration)
    - [Cross-language Parity Checklist](#cross-language-parity-checklist)
    - [Quick Reference](#quick-reference)
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

| Tool              | Recommended Version | Notes                                                                    |
| ----------------- | ------------------- | ------------------------------------------------------------------------ |
| Java JDK          | 21.x                | Required for Java module & CLI JAR (outputs Java 17 compatible bytecode) |
| Maven             | 3.8+                | Build Java artifacts (`mvn clean install`)                               |
| Python            | 3.10+               | For Python implementation & scripts                                      |
| pip / venv        | Latest              | Manage Python dependencies                                               |
| Docker (optional) | Latest              | Build container image                                                    |

## Project Layout

```text
lib/
  java/
    pom.xml            # Parent POM (multi-module Maven build)
    opentoken/         # Core tokenization library (pure logic, minimal dependencies)
    opentoken-cli/     # CLI application with I/O support (CSV, Parquet, JSON)
  python/
    opentoken/         # Core tokenization library
    opentoken-cli/     # CLI application with I/O support
    opentoken-pyspark/ # PySpark bridge for distributed processing
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

- Java 21 SDK or higher (JAR output is Java 17 compatible)
- Maven 3.8.8 or higher

Build all modules (from `lib/java`):

```shell
cd lib/java && mvn clean install
```

Build individual modules:

```shell
# Core library only
cd lib/java/opentoken && mvn clean install

# CLI only (requires core to be installed first)
cd lib/java/opentoken-cli && mvn clean install
```

Resulting JARs:

- Core library: `lib/java/opentoken/target/opentoken-*.jar`
- CLI application: `lib/java/opentoken-cli/target/opentoken-cli-*.jar`

Using as Maven dependencies:

```xml
<!-- Core library (tokenization logic only) -->
<dependency>
  <groupId>com.truveta</groupId>
  <artifactId>opentoken</artifactId>
  <version>${opentoken.version}</version>
</dependency>

<!-- CLI with I/O support (includes core as transitive dependency) -->
<dependency>
  <groupId>com.truveta</groupId>
  <artifactId>opentoken-cli</artifactId>
  <version>${opentoken.version}</version>
</dependency>
```

CLI usage:

```shell
cd lib/java && java -jar opentoken-cli/target/opentoken-cli-*.jar [OPTIONS]
```

Arguments:

- `-i, --input <path>` Input file
- `-t, --type <csv|parquet>` Input type
- `-o, --output <path>` Output file
- `-ot, --output-type <type>` Optional output type
- `-h, --hashingsecret <secret>` HMAC-SHA256 secret
- `-e, --encryptionkey <key>` AES-256 key

Example:

```shell
cd lib/java && java -jar opentoken-cli/target/opentoken-cli-*.jar \
  -i opentoken/src/test/resources/sample.csv -t csv -o opentoken-cli/target/output.csv \
  -h "HashingKey" -e "Secret-Encryption-Key-Goes-Here."
```

Programmatic API (simplified):

```java
List<TokenTransformer> transformers = Arrays.asList(
  new HashTokenTransformer("your-hashing-secret"),
  new EncryptTokenTransformer("your-encryption-key")
);
try (PersonAttributesReader reader = new PersonAttributesCSVReader("input.csv");
     PersonAttributesWriter writer = new PersonAttributesCSVWriter("output.csv")) {
  PersonAttributesProcessor.process(reader, writer, transformers, metadata);
}
```

Testing:

```shell
# Test all modules
cd lib/java && mvn test

# Test with coverage report
cd lib/java && mvn clean test jacoco:report
# Coverage reports: opentoken/target/site/jacoco/index.html and opentoken-cli/target/site/jacoco/index.html
```

Style & docs:

```shell
mvn checkstyle:check
mvn clean javadoc:javadoc
```

Notes:

- Large inputs may require additional heap (`-Xmx4g`).
- Unicode normalized to ASCII equivalents.

### Python

Prerequisites:

- Python 3.10+
- pip

Create & activate virtual environment (recommended):

```shell
cd lib/python/opentoken
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```shell
# Core library
pip install -r requirements.txt -r dev-requirements.txt

# For CLI support, also install opentoken-cli
cd ../opentoken-cli
pip install -r requirements.txt -r dev-requirements.txt
```

Editable install for local development:

```shell
# Install core library
cd lib/python/opentoken && pip install -e .

# Install CLI (includes core as dependency)
cd lib/python/opentoken-cli && pip install -e .
```

CLI usage (from project root):

```shell
# After installing opentoken-cli
python -m opentoken_cli.main [OPTIONS]
```

Arguments mirror Java implementation.

Example:

```shell
# After installing opentoken-cli
python -m opentoken_cli.main \
  -i resources/sample.csv -t csv -o lib/python/opentoken-cli/target/output.csv \
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
cd lib/python/opentoken
PYTHONPATH=src/main pytest src/test

# CLI tests
cd lib/python/opentoken-cli
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
- Keep tests in sync with Java changes.

### PySpark Bridge

The PySpark bridge (`lib/python/opentoken-pyspark`) provides a distributed processing interface for generating tokens and performing dataset overlap analysis using Spark DataFrames.

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
pip install -r lib/python/opentoken-pyspark/requirements.txt -r lib/python/opentoken-pyspark/dev-requirements.txt
pip install -e lib/python/opentoken-pyspark
```

Basic Usage:

```python
from pyspark.sql import SparkSession
from opentoken_pyspark import OpenTokenProcessor

spark = SparkSession.builder.master("local[2]").appName("OpenTokenExample").getOrCreate()
df = spark.read.csv("people.csv", header=True)
processor = OpenTokenProcessor("HashingKey", "Secret-Encryption-Key-Goes-Here.")
token_df = processor.process_dataframe(df)
token_df.show()
```

Custom Token Definitions (example adding T6):

```python
from opentoken_pyspark import OpenTokenProcessor
from opentoken_pyspark.notebook_helpers import TokenBuilder, CustomTokenDefinition

t6 = TokenBuilder("T6") \
  .add("last_name", "T|U") \
  .add("first_name", "T|U") \
  .add("birth_date", "T|D") \
  .build()

definition = CustomTokenDefinition().add_token(t6)
processor = OpenTokenProcessor(
  hashing_secret="HashingKey",
  encryption_key="Secret-Encryption-Key-Goes-Here.",
  token_definition=definition
)
token_df = processor.process_dataframe(df)
```

Testing:

```shell
cd lib/python/opentoken-pyspark
pytest src/test
```

Notebook Guides:

- See `lib/python/opentoken-pyspark/notebooks/` for example workflows (custom tokens & overlap analysis).
### Multi-Language Sync Tool

Java is the source of truth. The sync tool ([tools/java_language_syncer.py](https://github.com/TruvetaPublic/OpenToken/blob/main/tools/java_language_syncer.py)) evaluates changed Java files against enabled target languages (currently Python). It will fail PR workflows if any modified Java file lacks a corresponding, up-to-date target implementation.

Key concepts:

- Source-centric config: [tools/java-language-mappings.json](https://github.com/TruvetaPublic/OpenToken/blob/main/tools/java-language-mappings.json) defines `critical_java_files` (with optional priorities/manual review) and `directory_roots` for broad coverage.
- Language overrides: Target-specific adjustments live under `target_languages.<lang>.overrides.critical_files`.
- Auto-generation: If `auto_generate_unmapped` is true, unmapped Java files still produce inferred target paths via handlers.
- Sync status logic: A target file is considered synced if it was modified after the Java file (timestamp) or, in simplified mode, if both were touched in the PR.
- Disabled scaffolds: C# handlers exist; enabling them requires setting `enabled: true` and supplying base path + conventions.

Usage examples:

```bash
python3 tools/java_language_syncer.py --format console
python3 tools/java_language_syncer.py --format github-checklist --since origin/main
python3 tools/java_language_syncer.py --health-check
```

CI enforcement: The GitHub Actions workflow (`java-language-sync.yml`) posts a checklist and fails if completion < total.

When adding attributes/tokens: update Java first, run sync tool, then implement Python parity before merging.

### Cross-language Tips

| Task            | Java Command                                             | Python Command                     |
| --------------- | -------------------------------------------------------- | ---------------------------------- |
| Build / Package | `cd lib/java && mvn clean install`                       | `pip install -e .`                 |
| Run Tests       | `mvn test`                                               | `pytest src/test`                  |
| Lint / Style    | `mvn checkstyle:check`                                   | (pep8 / flake8 if configured)      |
| Run CLI         | `java -jar opentoken-cli/target/opentoken-cli-*.jar ...` | `python -m opentoken_cli.main ...` |
| Add Token       | SPI entry & class                                        | new module in `tokens/definitions` |
| Add Attribute   | SPI entry & class                                        | class + loader import              |

Maintain the same functional behavior and normalization between languages.

## Token Processing Modes

OpenToken supports three processing modes across Java, Python, and the PySpark bridge. These modes determine how raw token signatures are transformed:

| Mode      | Secrets Required                     | Transform Pipeline                                | Output Example (T1)                  | Deterministic Across Runs | Recommended Use                                                   |
| --------- | ------------------------------------ | ------------------------------------------------- | ------------------------------------ | ------------------------- | ----------------------------------------------------------------- |
| Plain     | None (not currently exposed via CLI) | Concatenate normalized attribute expressions only | `DOE\|JOHN\|1990-01-15\|MALE\|98101` | Yes (given same input)    | Debugging, rule design, docs demos                                |
| Hash-only | Hashing secret only                  | HMAC-SHA256(signature)                            | 64 hex chars (SHA-256 digest)        | Yes                       | Internal overlap analysis against decrypted partner token outputs |
| Encrypted | Hashing secret + encryption key      | HMAC-SHA256 f AES-256-GCM (random IV per token)  | Base64 blob (length varies)          | Yes (post-decrypt hash)   | Production / privacy-preserving use and external token exchange   |

Notes:

- The underlying signature (before hashing) is produced by ordered attribute expressions for each token rule (e.g., T1fT5 or custom T6+). Plain mode exposes this directly for inspection.
- Encryption uses AES-256-GCM with a random IV; identical hashed inputs yield different encrypted outputs each run. Matching encrypted tokens across datasets therefore requires either: (a) decryption with the shared key (to reach the hash-only representation) or (b) generating hash-only tokens specifically for overlap workflows. Do NOT attempt to match encrypted blobs directly.
- Tokenizer polymorphism: Java & Python `TokenGenerator` accept an injectable tokenizer. Defaults to SHA-256; when plain mode is active a `PassthroughTokenizer` is used so downstream transformers (if any) receive the raw signature.
- Security: Plain and hash-only modes reduce protection. Never use plain mode for sharing PHI; hash-only may leak structural frequency information. Encrypted mode is required for external distribution; hash-only datasets should remain internal and are typically used to join against decrypted partner tokens for overlap analysis.

## Token & Attribute Registration

This section unifies Java and Python guidance for adding new Tokens and Attributes.

### When to Use

- Adding a new token generation rule (Token)
- Adding a new source person attribute (Attribute)
- Refactoring or renaming existing implementations

### Java Registration (ServiceLoader SPI)

Java uses the standard `ServiceLoader` discovery mechanism.

Steps (Token example):

1. Create class in `com.truveta.opentoken.tokens.definitions` extending `Token`.
2. Implement required abstract methods (identifier, definition, etc.).
3. Add fully qualified class name to: `lib/java/opentoken/src/main/resources/META-INF/services/com.truveta.opentoken.tokens.Token` (one per line).
4. Run `mvn clean install` and add/adjust tests.

Attribute steps are identical except:

- Class extends `com.truveta.opentoken.attributes.Attribute` (e.g., in `attributes.person`).
- Register in: `lib/java/opentoken/src/main/resources/META-INF/services/com.truveta.opentoken.attributes.Attribute`.

Guidelines:

- No blank lines or comments in service files.
- Keep entries sorted alphabetically (recommended for diffs).
- Update service file if class is renamed/moved.

Troubleshooting:

- Not loading? Check for: typo in service file, missing no-arg constructor, class not public, duplicate class names.

### Python Registration

Python uses two mechanisms:

1. Dynamic discovery for Tokens in `opentoken/tokens/definitions`.
2. Explicit inclusion for Attributes via `attribute_loader.py`.

Add a Token:

1. Create `lib/python/opentoken/src/main/opentoken/tokens/definitions/t6_token.py` (example).
2. Define a class inheriting `Token` with `get_identifier()` & `get_definition()`.
3. Ensure file and class names are unique and public.
4. Run `pytest src/test` to verify auto-discovery.

Add an Attribute:

1. Create module, e.g., `opentoken/attributes/person/middle_name_attribute.py`.
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
# Java (builds both core and CLI modules)
(cd lib/java && mvn clean install)

# Python core
(cd lib/python/opentoken && pytest src/test)

# Python CLI
(cd lib/python/opentoken-cli && pytest src/test)

# PySpark Bridge
(cd lib/python/opentoken-pyspark && pytest src/test)
```

### Docker Image

```shell
docker build . -t opentoken
```

## Running the Tool (CLI)

The CLI is provided by the `opentoken-cli` package in both Java and Python.

Minimum required arguments:

```shell
# Java
java -jar lib/java/opentoken-cli/target/opentoken-cli-*.jar -i input.csv -t csv -o output.csv -h HashingKey -e Secret-Encryption-Key-Goes-Here.

# Python
python -m opentoken_cli.main -i input.csv -t csv -o output.csv -h HashingKey -e Secret-Encryption-Key-Goes-Here.
```

Arguments:

| Flag                  | Description                                     |
| --------------------- | ----------------------------------------------- |
| `-t, --type`          | Input file type (`csv` or `parquet`)            |
| `-i, --input`         | Input file path                                 |
| `-o, --output`        | Output file path                                |
| `-ot, --output-type`  | (Optional) Output file type (defaults to input) |
| `-h, --hashingsecret` | Hashing secret for HMAC-SHA256                  |
| `-e, --encryptionkey` | AES-256 encryption key                          |

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
- [ ] Followed style guidelines (Checkstyle / Python conventions)
- [ ] Added registration entries (Java SPI files) or loader entries (Python) if new Token/Attribute
- [ ] Bumped version with `bump2version`

## Troubleshooting

| Issue                            | Hint                                                                                |
| -------------------------------- | ----------------------------------------------------------------------------------- |
| Java class not discovered        | Confirm fully qualified name in `META-INF/services/*` file & no trailing spaces     |
| Python attribute not loaded      | Ensure it is imported & added in `attribute_loader.py`                              |
| Token mismatch between languages | Verify hashing & encryption secrets are identical and normalization logic unchanged |
| Build fails on Checkstyle        | Run `mvn -q checkstyle:check` locally & fix warnings                                |


---
Maintainers: Keep this guide updated when changing build, versioning, or extension workflows.
