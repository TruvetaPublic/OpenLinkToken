---
layout: default
title: Community
---

# Community

Join the Open Link Token community.

- [Contributing](contributing.md) — How to contribute code and documentation
- [Code of Conduct](code-of-conduct.md) — Community standards
- [Branch Workflow and Release Process](../branch-workflow-and-release-process.md) — Branching, pull-request routing, and release automation

## Contribution and Development

### Contribution Guidelines

- **Target branch:** All feature and bugfix PRs go to `develop` (not `main`).
- **Branch naming:** `dev/<github-username>/<feature-name>` (kebab-case). Example: `dev/alex-smith/add-zip-validation`.
- **Draft PRs:** Open pull requests in **draft** mode first.
- **Code standards:**
  - Java: Follow Checkstyle; add Javadoc for public APIs; never use fully qualified class names—add imports instead.
  - Python: PEP 8; Google-style docstrings.
- **Tests:** Add/extend tests for new logic; keep coverage ≥80% for new code.
- **Security:** Never commit secrets. Use placeholder keys only in examples.

### Development Setup

#### Java

```bash
cd lib/java
mvn clean install
```

#### Python

```bash
# From repo root
uv venv .venv
source .venv/bin/activate

# Core library
cd lib/python/openlinktoken
uv pip install -r requirements.txt -e .

# CLI
cd ../openlinktoken-cli
uv pip install -r requirements.txt -e .
```

#### PySpark Bridge

```bash
# From repo root
source .venv/bin/activate
cd lib/python/openlinktoken-pyspark
uv pip install -r requirements.txt -e .
```

### Branch Workflow (Gitflow)

```text
dev/* (feature work) → develop → release/x.y.z → main
```

- Feature branches start from `develop`.
- Release branches (`release/x.y.z`) open PRs to `main`.
- Merged release PRs create the version tag and GitHub release automatically.
- Keep `develop` current through the normal pull-request process; the release
  workflow does not create an automatic back-sync PR.

### Versioning

- Semantic versioning: `MAJOR.MINOR.PATCH`.
- Use `bump2version` for version increments during releases.

### Tests and Quality Gates

- Java: `mvn clean install` (includes unit tests, integration tests, Checkstyle, JaCoCo).
- Python: `pytest` (run from `lib/python/openlinktoken` and `lib/python/openlinktoken-cli`).
- Interoperability: `python tools/interoperability/multi_language_interoperability_test.py`.
- Sync check: [tools/sync-check.sh](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/tools/sync-check.sh) to ensure Java/Python parity.

### Dev Container

A VS Code dev container is provided with Java, Maven, Python, and Docker CLI
pre-installed. See the [canonical Developer Guide on GitHub](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/docs/dev-guide-development.md)
for full setup and build details.

### Issues and Discussions

- File issues and feature requests on GitHub.
- Include repro steps, expected behavior, and environment details.

### License

Open Link Token is released under the MIT License. See the [LICENSE file on GitHub](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/LICENSE) for details.

## Next Steps

- **Get started**: [Quickstarts](../quickstarts/index.md)
- **Report issues**: [GitHub Issues](https://github.com/TruvetaPublic/OpenLinkToken/issues)
