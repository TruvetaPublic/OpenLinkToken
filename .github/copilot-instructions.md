# OpenToken AI Coding Agent Instructions

## ⚠️ CRITICAL JAVA CODING RULE - READ FIRST

**NEVER use fully qualified class names in Java code.** ALWAYS add import statements and use short class names.

- ❌ **WRONG**: `new com.truveta.opentoken.tokens.tokenizer.SHA256Tokenizer(transformers)`
- ✅ **CORRECT**: Add `import com.truveta.opentoken.tokens.tokenizer.SHA256Tokenizer;` at top, then use `new SHA256Tokenizer(transformers)`

This rule applies to ALL Java code - constructors, method calls, type declarations, etc. See [Code Style Guidelines](#code-style-guidelines) for details.

## Overview

This document provides comprehensive guidance for AI coding agents working on the OpenToken project. Follow these instructions to ensure code quality, consistency, and compatibility across both Java and Python implementations.

### Task Suitability

**Good Tasks for AI Agents:**

- Adding new attributes (with validation/normalization)
- Adding new validation rules
- Bug fixes in existing attributes/validators
- Test coverage improvements
- Documentation updates
- Code refactoring within existing patterns

**Tasks Requiring Human Review:**

- Changes to core token generation logic
- Modifications to encryption/hashing algorithms
- Breaking API changes
- New token rules (T6+)
- Multi-language implementation changes

## Architecture Overview

**OpenToken** is a dual-implementation (Java/Python) library for privacy-preserving person matching using cryptographically secure token generation. Tokens are generated from deterministic person attributes (name, birthdate, SSN, etc.) using 5 distinct token rules (T1-T5). Both implementations must produce **identical tokens** for the same normalized input.

### Core Components

- **Attributes** (`lib/java/.../attributes/`, `lib/python/.../attributes/`): Person data fields with validation & normalization (e.g., `BirthDateAttribute`, `SocialSecurityNumberAttribute`)
- **Validators** (`validation/`): Composable validation rules (regex, date ranges, age ranges) applied during attribute processing
- **Tokens** (`tokens/`): Rules defining which attributes combine to form each of the 5 token types (T1-T5)
- **I/O Readers/Writers** (`opentoken-cli/.../io/`): CSV and Parquet file processors with streaming support (in CLI package)
- **Token Transformers** (`tokentransformer/`): HMAC-SHA256 hashing + AES-256 encryption pipeline

### Registration Pattern (Critical)

**Java uses ServiceLoader SPI** - new attributes/tokens require:

1. Implement interface (e.g., extend `BaseAttribute`)
2. Add fully-qualified class name to `lib/java/opentoken/src/main/resources/META-INF/services/com.truveta.opentoken.{attributes.Attribute|tokens.Token}`
3. Keep entries sorted alphabetically (one per line, no blank lines/comments)

**Python uses explicit imports** in loader files:

- `lib/python/opentoken/src/main/opentoken/attributes/attribute_loader.py` → add to `AttributeLoader.load()` set
- `lib/python/opentoken/src/main/opentoken/tokens/token_registry.py` → add to registry

**Both languages must be updated** or parity breaks. Use `tools/java_language_syncer.py` to verify cross-language sync.

## Development Workflows

### ⚠️ CRITICAL PYTHON ENVIRONMENT RULE

**The Python virtual environment (`.venv`) is located at the repository root (`/workspaces/OpenToken/.venv`).**

- ❌ **NEVER** create or activate a venv in any subdirectory (e.g., `lib/python/opentoken/.venv`)
- ❌ **NEVER** run `python -m venv .venv` from any folder other than the repo root
- ✅ **ALWAYS** activate the root venv: `source /workspaces/OpenToken/.venv/bin/activate`
- ✅ **ALWAYS** use absolute path or ensure you're at repo root before activating

```bash
# CORRECT - activate from anywhere using absolute path
source /workspaces/OpenToken/.venv/bin/activate

# CORRECT - navigate to repo root first
cd /workspaces/OpenToken && source .venv/bin/activate

# WRONG - never do this from lib/python or any subdirectory
cd lib/python/opentoken && python -m venv .venv  # ❌ DO NOT DO THIS
```

### Build & Test

```bash
# Java (from lib/java/): Maven handles compile, Checkstyle, JaCoCo coverage, sanity checks
# Builds both opentoken (core) and opentoken-cli modules
cd lib/java && mvn clean install

# Python: Activate root venv first, then run tests from package directories
source /workspaces/OpenToken/.venv/bin/activate

# Python core library tests:
cd /workspaces/OpenToken/lib/python/opentoken && pytest

# Python CLI tests:
cd /workspaces/OpenToken/lib/python/opentoken-cli && pytest

# Note: No unified build script exists - build each language separately
```

### Branch Management

**Required Branch Format:** `dev/<github-username>/<feature-description>` (e.g., `dev/mattwise-42/additional-attributes`)

**Automatic Branch Creation:**

When starting work on a new feature or task, always check if a feature branch exists. If not, create one automatically using this workflow:

1. **Get the GitHub username:**

   ```bash
   # Get authenticated user's GitHub username
   git config user.name  # Fallback if GitHub API unavailable
   ```

2. **Create feature branch (from `develop`):**

```bash
# Base branch for feature work is always develop (not main)
git checkout develop
git pull origin develop
# Format: dev/<username>/<feature-name>
# Example: dev/mattwise-42/add-middle-name-attribute
git checkout -b "dev/<username>/<feature-name>" develop
git push -u origin "dev/<username>/<feature-name>"
```

3. **Feature name conventions:**
   - Use kebab-case (lowercase with hyphens)
   - Be descriptive but concise (3-5 words)
   - Examples:
     - `add-middle-name-attribute`
     - `fix-ssn-validation-bug`
     - `update-birth-date-range`
     - `improve-test-coverage`

**Branch Creation & PR Target Decision Tree:**

- If on `develop` and starting new work → Create feature branch
- If on `main` → Switch to `develop` before creating feature branch
- If on existing feature branch for same task → Continue on current branch
- If on unrelated feature branch → `git stash` (if needed), switch to `develop`, then create new feature branch
- If branch name doesn't match format → Warn user and suggest proper rename/recreate
- Standard PR target: `develop` (never `main` for regular feature work)
- Exceptions: Release/hotfix processes may merge to `main` then sync back to `develop`

**PR Targeting Guidelines:**

- All feature / refactor / docs / test PRs target `develop`
- Do not open PRs directly against `main` unless performing an approved release or emergency hotfix
- After a hotfix merged to `main`, open sync PR from `main` → `develop`

**Example Workflow:**

```bash
# Check current branch
CURRENT_BRANCH=$(git branch --show-current)

# If on main and no feature branch exists
if [ "$CURRENT_BRANCH" = "main" ]; then
  USERNAME=$(git config user.name | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
  FEATURE_NAME="your-feature-description"
  NEW_BRANCH="dev/${USERNAME}/${FEATURE_NAME}"

  git checkout -b "$NEW_BRANCH"
  git push -u origin "$NEW_BRANCH"
  echo "Created and switched to branch: $NEW_BRANCH"
fi
```

## Project-Specific Conventions

### Attribute Development Pattern

1. **Extend `BaseAttribute`** (Java) or `SerializableAttribute` (Python)
2. **Validators are composable**: Pass list to super constructor (Java) or init validators in `__init__` (Python)
   - Example: `BirthDateAttribute` extends `DateAttribute` and adds `DateRangeValidator(LocalDate.of(1910, 1, 1), true)`
3. **Normalization happens before validation**: `normalize()` must handle edge cases (whitespace, case, diacritics)
4. **Thread-safety required**: Use `DateTimeFormatter` (Java) not `SimpleDateFormat`; avoid mutable shared state
5. **Test pattern**: Include serialization test, thread-safety test (100 threads), boundary value tests
6. **Code coverage**: New attributes must have ≥80% test coverage (see [Code Coverage Requirements](#code-coverage-requirements))

### Test Structure

- **Java**: JUnit 5, tests mirror `src/main/` structure in `src/test/`
  - Integration tests: `PersonAttributesProcessorIntegrationTest.java` validates full pipeline
  - Sanity checks: Maven Antrun plugin runs CSV/Parquet end-to-end after build
- **Python**: pytest, uses `test_*.py` naming, includes interoperability tests against Java output
  - Hash calculator tests: `tools/test_hash_calculator.py` ensures token computation matches Java

### Validation Rules (Critical Business Logic)

- **SSN**: Area ≠ `000|666|900-999`, Group ≠ `00`, Serial ≠ `0000`, reject common patterns (`111-11-1111`, etc.)
- **BirthDate**: Range `1910-01-01` to today, normalized to `yyyy-MM-dd`
- **Name normalization**: Remove titles/suffixes, strip diacritics, uppercase for token generation
- **PostalCode**: US ZIP (5/9 digits), Canadian (`A1A 1A1` format), reject placeholders (`00000`, `12345`)

### Metadata Generation

Every token generation run produces `.metadata.json` with:

- Processing stats (valid/invalid counts per attribute)
- SHA-256 hashes of secrets (for audit, NOT the secrets themselves)
- System info (Java version, library version, timestamp)
  See `docs/metadata-format.md` for schema.

### Cross-Language Parity Requirements

- Token outputs must be **byte-identical** for same input (verified by `tools/interoperability/` tests)
- Normalization logic must match exactly (e.g., diacritic removal, case conversion)
- Update `tools/java-language-mappings.json` when adding new classes (source-centric: `critical_java_files`, `directory_roots`, per-language `overrides`)
- Run `tools/sync-check.sh` before PR submission

## File Structure Patterns

```
lib/java/
├── pom.xml                     # Parent POM (multi-module Maven build)
├── opentoken/                  # Core tokenization library
│   └── src/main/java/com/truveta/opentoken/
│       ├── attributes/
│       │   ├── general/        # DateAttribute, StringAttribute, RecordIdAttribute
│       │   ├── person/         # BirthDateAttribute, SexAttribute, SSN, etc.
│       │   └── validation/     # RegexValidator, DateRangeValidator, AgeRangeValidator
│       ├── tokens/             # Token interface, TokenRegistry, definitions/ (T1-T5)
│       └── tokentransformer/   # HashTokenTransformer, EncryptTokenTransformer
└── opentoken-cli/              # CLI application with I/O support
    └── src/main/java/com/truveta/opentoken/
        ├── io/                 # CSV/Parquet readers & writers (streaming iterators)
        └── Main.java           # CLI entry point

lib/python/
├── opentoken/                  # Core tokenization library (mirrors Java structure)
├── opentoken-cli/              # CLI application with I/O support
└── opentoken-pyspark/          # PySpark bridge for distributed processing
```

## Common Pitfalls

1. **Using fully qualified class names**: NEVER use `com.truveta.opentoken.tokens.tokenizer.SHA256Tokenizer` in code - ALWAYS add import statement and use `SHA256Tokenizer`
2. **Forgetting service registration**: Java won't discover attributes without `META-INF/services` entry
3. **Python loader not updated**: `AttributeLoader.load()` returns hardcoded set, not auto-discovered
4. **Validation vs normalization order**: Always normalize first, then validate the normalized value
5. **Thread-safety in validators**: Pre-compile regex patterns, avoid mutable state
6. **Checkstyle failures**: Run `mvn checkstyle:check` separately to catch before full build

## Documentation Requirements

- **JavaDoc**: Required for all public classes/methods (Checkstyle enforces)
- **Python docstrings**: Follow Google style (Args, Returns, Raises)
- **README.md updates**: Add new attributes to acceptance table, update token rules if changed
- **CHANGELOG**: Implicit via PR descriptions and version bumps

## Security Guidelines

### Secrets and Sensitive Data

- **Never commit secrets**: Hashing keys and encryption keys must only appear in test files with dummy values
- **Test data only**: Use placeholder values like `"HashingKey"` or `"Secret-Encryption-Key-Goes-Here."` in examples
- **Metadata files**: Contain SHA-256 hashes of secrets (for audit), not the secrets themselves
- **Validation patterns**: SSN validation logic is public but never log/expose actual SSN values

### Dependency Management

- **Java dependencies**: Declared in `pom.xml`, must pass security scans via GitHub Dependabot
- **Python dependencies**: Managed in `requirements.txt` and `dev-requirements.txt`
- **Version pinning**: Pin major versions, allow minor/patch updates (`~=` for Python, ranges for Maven)
- **Vulnerability scanning**: Both implementations use automated security scans (see `.github/workflows/`)

## Code Style Guidelines

### Java (CRITICAL - Read First)

**⚠️ MANDATORY IMPORT RULE - NEVER VIOLATE THIS:**

- **ALWAYS add import statements and use short class names**:
  - ✅ CORRECT: Add `import com.truveta.opentoken.io.TokenWriter;` then use `TokenWriter`
  - ❌ WRONG: `com.truveta.opentoken.io.TokenWriter` (fully qualified name in code)
  - ✅ CORRECT: Add `import com.truveta.opentoken.tokens.tokenizer.SHA256Tokenizer;` then use `new SHA256Tokenizer()`
  - ❌ WRONG: `new com.truveta.opentoken.tokens.tokenizer.SHA256Tokenizer()` (fully qualified in code)
- **When editing Java code:**
  1. First, check existing imports at top of file
  2. If class not imported, add import statement in alphabetical order
  3. Then use short class name throughout the code
  4. NEVER write fully qualified class names in method bodies or constructors
- **Checkstyle compliance**: Run `mvn checkstyle:check` to validate (will catch style violations)
- **JavaDoc**: Required for all public classes and methods

### Python

- **PEP 8 compliance**: Follow Python style guidelines
- **Import organization**: Group imports (standard library, third-party, local)
- **Docstrings**: Use Google style (Args, Returns, Raises)

## Git Workflow & PR Standards

### Before Submitting

1. **Run all builds**: `mvn clean install` (Java) and `pytest` (Python)
2. **Check cross-language sync**: Run `tools/java_language_syncer.py`
3. **Code style**: Java Checkstyle must pass, Python follows PEP 8
4. **Test coverage**: Add tests for new code paths with **≥80% coverage** (see [Code Coverage Requirements](#code-coverage-requirements))
5. **Clear Jupyter notebook outputs**: Before committing or merging PRs, clear all cell outputs from notebooks to avoid committing execution results, large data, or secrets. Use "Clear All Outputs" in VS Code or `jupyter nbconvert --clear-output --inplace <notebook.ipynb>`

### PR Checklist

- [ ] Both Java and Python implementations updated (if applicable)
- [ ] Tests added/updated for changes
- [ ] **New code has ≥80% test coverage** (Java: JaCoCo, Python: pytest-cov)
- [ ] Documentation updated (README, JavaDoc, docstrings)
- [ ] Service registration files updated (Java: `META-INF/services/`, Python: loaders)
- [ ] No secrets or sensitive data committed
- [ ] CI/CD pipelines updated if necessary (GitHub Actions workflows, build configurations)
- [ ] All CI checks passing

### Commit Message Format

```
<type>: <short summary>

<detailed description if needed>

- Specific change 1
- Specific change 2
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

### Draft Pull Requests (Mandatory)

All new pull requests MUST be created in **draft** mode. The agent should never open a non-draft ("ready for review") PR initially. C

Agent Rules:

- Always set `draft: true` when invoking pull request creation tools.
- If a PR was accidentally opened as ready, immediately update it to draft and leave a comment noting the correction.
- Do not convert out of draft automatically; wait for explicit user request or all readiness conditions met.

## Debugging & Troubleshooting

### Common Build Issues

**Java Checkstyle failures:**

```bash
cd lib/java/opentoken && mvn checkstyle:check
```

Fix style issues before running full build.

**Python import errors:**

```bash
cd lib/python/opentoken && source .venv/bin/activate
pip install -e .
```

Ensure editable install for local development.

**Token mismatch between Java/Python:**

- Verify normalization logic matches exactly
- Check attribute order in token signatures
- Use `tools/interoperability/` tests to compare outputs

### Testing Strategies

**Unit tests**: Test individual attributes/validators in isolation
**Integration tests**: `PersonAttributesProcessorIntegrationTest.java` tests full pipeline
**Interoperability tests**: Verify Java/Python produce identical tokens
**Sanity checks**: Maven runs end-to-end CSV/Parquet tests post-build

### Code Coverage Requirements

**⚠️ MANDATORY: All new code must have at least 80% code coverage by unit tests.**

This requirement applies to all supported languages:

- **Java**: JaCoCo is used for coverage analysis. Run `mvn verify` to generate coverage reports in `target/site/jacoco/`
- **Python**: pytest-cov is used for coverage analysis. Run `pytest --cov=opentoken --cov-report=html` to generate coverage reports

**Coverage expectations:**

- New classes/modules: ≥80% line coverage
- New methods/functions: ≥80% branch coverage
- Bug fixes: Add tests that reproduce the bug before fixing
- Critical paths (token generation, validation, normalization): Target 90%+ coverage

**How to verify coverage:**

```bash
# Java: Generate and view coverage report
cd lib/java/opentoken && mvn verify
# Open target/site/jacoco/index.html in browser

# Python: Generate and view coverage report
cd lib/python/opentoken && source .venv/bin/activate
pytest --cov=opentoken --cov-report=html --cov-report=term
# Open htmlcov/index.html in browser
```

### Performance Considerations

- **Thread-safety**: All validators must be thread-safe (pre-compile regex patterns)
- **Streaming**: I/O readers use iterators, not loading entire files into memory
- **Batch processing**: Process large datasets in chunks for memory efficiency

## Code Review Standards

### What to Look For

1. **Correctness**: Logic matches requirements, edge cases handled
2. **Parity**: Java and Python implementations produce identical results
3. **Security**: No secrets committed, validation prevents injection
4. **Performance**: No unnecessary allocations, thread-safe patterns
5. **Documentation**: Public APIs documented, complex logic explained
6. **Tests**: New code has corresponding tests, tests are meaningful

### Red Flags

- Missing service registration (Java won't discover new attributes)
- Python loader not updated (hardcoded set won't include new classes)
- Validation after normalization (must validate normalized values)
- Mutable shared state in validators (causes race conditions)
- Breaking changes without major version bump
