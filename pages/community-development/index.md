---
layout: default
---

# Community & Development

Guidance for contributors, branching workflow, and local setup.

## Contribution Guidelines

- **Target branch:** All feature and bugfix PRs go to `develop` (not `main`).
- **Branch naming:** `dev/<github-username>/<feature-name>` (kebab-case). Example: `dev/alex-smith/add-zip-validation`.
- **Draft PRs:** Open pull requests in **draft** mode first.
- **Code standards:**
  - Java: Follow Checkstyle; add Javadoc for public APIs; never use fully qualified class names—add imports instead.
  - Python: PEP 8; Google-style docstrings.
- **Tests:** Add/extend tests for new logic; keep coverage ≥80% for new code.
- **Security:** Never commit secrets. Use placeholder keys only in examples.

## Development Setup

### Java

```bash
cd lib/java
mvn clean install
```

### Python

```bash
# From repo root
python -m venv .venv
source .venv/bin/activate

# Core library
cd lib/python/opentoken
pip install -r requirements.txt -e .

# CLI
cd ../opentoken-cli
pip install -r requirements.txt -e .
```

### PySpark Bridge

```bash
source /workspaces/OpenToken/.venv/bin/activate
cd lib/python/opentoken-pyspark
pip install -r requirements.txt -e .
```

## Branch Workflow (Gitflow)

```
dev/* (feature work) → develop → release/x.y.z → main → develop (auto-sync)
```

- Feature branches start from `develop`.
- Release branches (`release/x.y.z`) open PRs to `main`.
- After release, an automated PR syncs `main` back into `develop`.

## Versioning

- Semantic versioning: `MAJOR.MINOR.PATCH`.
- Use `bump2version` for version increments during releases.

## Tests & Quality Gates

- Java: `mvn clean install` (includes unit tests, integration tests, Checkstyle, JaCoCo).
- Python: `pytest` (run from `lib/python/opentoken` and `lib/python/opentoken-cli`).
- Interoperability: `python tools/interoperability/java_python_interoperability_test.py`.
- Sync check: [tools/sync-check.sh](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/tools/sync-check.sh) to ensure Java/Python parity.

## Dev Container

A VS Code dev container is provided with Java, Maven, Python, and Docker CLI pre-installed. See [Developer Guide](../dev-guide-development.md) for details.

## Issues & Discussions

- File issues and feature requests on GitHub.
- Include repro steps, expected behavior, and environment details.

## License

OpenToken is released under the MIT License. See the [LICENSE file on GitHub](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/LICENSE) for details.
