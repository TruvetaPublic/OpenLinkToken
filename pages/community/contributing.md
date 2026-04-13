---
layout: default
---

# Contributing

This guide outlines how to contribute code, documentation, and bug reports to OpenLinkToken.

---

## Getting Started

### Prerequisites

- **Git**: Version control
- **Java 21+**: For Java development
- **Python 3.10+**: For Python development
- **Maven**: For Java builds
- **Docker** (optional): For containerized testing

### Setting Up Your Environment

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR-USERNAME/OpenLinkToken.git
   cd OpenLinkToken
   ```
3. **Set up the Python environment** (at repo root):
   ```bash
   uv venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or .venv\Scripts\activate on Windows
   uv pip install -r lib/python/openlinktoken/requirements.txt
   uv pip install -r lib/python/openlinktoken/dev-requirements.txt
   ```
4. **Build Java components**:
   ```bash
   cd lib/java && mvn clean install
   ```

---

## Branching Strategy

OpenLinkToken uses a Gitflow-based branching strategy:

### Branch Types

| Branch                     | Purpose                   | Merges To   |
| -------------------------- | ------------------------- | ----------- |
| `main`                     | Production-ready releases | —           |
| `develop`                  | Integration branch        | `release/*` |
| `dev/<username>/<feature>` | Feature development       | `develop`   |
| `release/x.y.z`            | Release preparation       | `main`      |

### Creating a Feature Branch

```bash
# Start from develop
git checkout develop
git pull origin develop

# Create your feature branch
git checkout -b dev/your-username/feature-name
```

### Branch Naming Convention

- Format: `dev/<github-username>/<feature-description>`
- Use kebab-case for feature descriptions
- Examples:
  - `dev/jsmith/add-middle-name-attribute`
  - `dev/jsmith/fix-ssn-validation`

---

## Pull Request Process

### Before Submitting

1. **Run all tests**:

   ```bash
   # Java
   cd lib/java && mvn clean test

   # Python
   cd lib/python/openlinktoken && pytest
   cd ../openlinktoken-cli && pytest
   ```

2. **Check code style**:

   ```bash
   # Java (Checkstyle)
   cd lib/java && mvn checkstyle:check
   ```

3. **Verify cross-language parity** (if applicable):

   ```bash
   python3 tools/multi_language_syncer.py
   ```

4. **Update documentation** if your changes affect user-facing behavior

### PR Requirements

- [ ] Clear, descriptive title
- [ ] Reference any related issues (`Fixes #123`)
- [ ] Both Java and Python implementations updated (if applicable)
- [ ] Tests added or updated
- [ ] Documentation updated
- [ ] All CI checks passing

### Review Process

1. Submit PR to `develop` (not `main`)
2. Wait for CI checks to pass
3. Address reviewer feedback
4. Once approved, a maintainer will merge

---

## Coding Standards

### Java

- **Style**: Follow Checkstyle configuration in `lib/java/openlinktoken/checkstyle.xml`
- **JavaDoc**: Required for all public classes and methods
- **Testing**: JUnit 5, aim for ≥80% code coverage
- **Imports**: Use short class names with imports (never fully qualified names in code)

```java
// ✓ Correct
import org.openlinktoken.tokens.tokenizer.SHA256Tokenizer;
SHA256Tokenizer tokenizer = new SHA256Tokenizer(transformers);

// ✗ Wrong - never use fully qualified names
org.openlinktoken.tokens.tokenizer.SHA256Tokenizer tokenizer = ...
```

### Python

- **Style**: Follow PEP 8
- **Docstrings**: Google style (Args, Returns, Raises)
- **Testing**: pytest, aim for ≥80% code coverage
- **Type hints**: Use type annotations for function signatures

---

## Testing Requirements

### Test Coverage

- **New code**: Must have ≥80% test coverage
- **Bug fixes**: Add a test that reproduces the bug before fixing
- **Critical paths**: Token generation, validation, normalization should target 90%+

### Running Tests

```bash
# Java with coverage report
cd lib/java && mvn verify
# Report: target/site/jacoco/index.html

# Python with coverage report
cd lib/python/openlinktoken
pytest --cov=openlinktoken --cov-report=html
# Report: htmlcov/index.html
```

---

## Adding New Attributes

When adding a new attribute (e.g., `MiddleNameAttribute`):

### Java

1. Create class extending `BaseAttribute` in `lib/java/openlinktoken/src/main/java/org/openlinktoken/attributes/`
2. Add to `META-INF/services/org.openlinktoken.attributes.Attribute` (alphabetical order)
3. Add tests in `src/test/java/`

### Python

1. Create class in `lib/python/openlinktoken/src/main/openlinktoken/attributes/`
2. Add to `AttributeLoader.load()` set in `attribute_loader.py`
3. Add tests in `src/test/`

### Cross-Language Sync

After adding to both languages:

```bash
python3 tools/multi_language_syncer.py
```

---

## Filing Issues

### Bug Reports

Include:

- **Title**: Clear, concise description
- **Environment**: OS, Java/Python version, OpenLinkToken version
- **Steps to reproduce**: Minimal example
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Error messages**: Full stack traces if applicable

### Feature Requests

Include:

- **Problem statement**: What problem does this solve?
- **Proposed solution**: How should it work?
- **Alternatives considered**: Other approaches you have thought about
- **Use cases**: Who would benefit and how?

---

## Commit Messages

### Format

```
<type>: <short summary>

<optional body>
```

### Types

| Type       | Description                                             |
| ---------- | ------------------------------------------------------- |
| `feat`     | New feature                                             |
| `fix`      | Bug fix                                                 |
| `docs`     | Documentation only                                      |
| `test`     | Adding or updating tests                                |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `chore`    | Build process, dependencies, tooling                    |

---

## Questions?

- Open a GitHub Discussion
- Check existing issues for similar questions
- Review the [Code of Conduct](code-of-conduct.md)

Thank you for contributing to OpenLinkToken!
