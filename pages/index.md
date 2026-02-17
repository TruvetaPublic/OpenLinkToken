---
layout: default
---

# OpenToken Documentation

OpenToken is a privacy-preserving tokenization and matching library for secure person linkage using PII-derived attributes. It provides deterministic, cryptographically secure tokens across Java and Python implementations.

## What is OpenToken?

OpenToken is a library and CLI tool for generating cryptographically secure matching tokens from person attributes. It enables privacy-preserving person matching by comparing tokens across datasets instead of directly comparing names, birthdates, SSNs, and other sensitive identifiers. It’s designed for any domain that needs deterministic, auditable linkage while minimizing exposure of raw PII.

Matching is foundational for analytics, operations, and research, but traditional record linkage relies on handling raw identifiers that are both highly sensitive and frequently messy (typos, nicknames, missing values, inconsistent formats). OpenToken provides a deterministic, standards-driven tokenization pipeline (normalize → validate → generate T1–T5 signatures → hash/encrypt) so matching can be performed with minimized identifier exposure and with predictable behavior across environments.

Why it matters:

- Reduces the surface area of sensitive data in downstream systems by shifting matching to tokens.
- Improves match quality by applying consistent normalization/validation before token generation.
- Supports reproducibility and auditability via metadata and deterministic hash/decrypted outputs.
- Enables interoperability: Java and Python produce byte-identical deterministic values (hash-only/decrypted) for the same inputs and secrets.

## Start Here

**→ [Quickstarts](quickstarts/index.md)** – The fastest path to generating tokens. Choose CLI (Docker), Python, or Java.

For background on how OpenToken works before diving in, see [Overview](overview/index.md).

## Documentation Structure

This site organizes quickstarts, concepts, operations guidance, configuration, references, security notes, the formal specification, and community resources for OpenToken.

## Table of Contents

- [Overview](overview/index.md)
- [Quickstarts](quickstarts/index.md)
  - [Quickstarts Hub](quickstarts/index.md) — Start here
  - [CLI Quickstart](quickstarts/cli-quickstart.md)
  - [Java Quickstart](quickstarts/java-quickstart.md)
  - [Python Quickstart](quickstarts/python-quickstart.md)
- [Concepts](concepts/index.md)
  - [Matching Model](concepts/matching-model.md)
  - [Token Rules](concepts/token-rules.md)
  - [Normalization and Validation](concepts/normalization-and-validation.md)
  - [Metadata and Audit](concepts/metadata-and-audit.md)
- [Operations](operations/index.md)
  - [Running Batch Jobs](operations/running-batch-jobs.md)
  - [Spark or Databricks](operations/spark-or-databricks.md)
  - [Sharing Tokenized Data](operations/sharing-tokenized-data.md)
  - [PPRL Demo Walkthrough](operations/pprl-demo-walkthrough.md)
  - [Decrypting Tokens](operations/decrypting-tokens.md)
  - [Hash-Only Mode](operations/hash-only-mode.md)
  - [Mock Data Workflows](operations/mock-data-workflows.md)
- [Configuration](config/configuration.md)
  - [Configuration](config/configuration.md)
- [Security](security.md)
- [Specification](specification.md)
- [Community](community/index.md)
  - [Contributing](community/contributing.md)
  - [Code of Conduct](community/code-of-conduct.md)
- [Reference](reference/index.md)
  - [CLI Reference](reference/cli.md)
  - [Java API Reference](reference/java-api.md)
  - [Python API Reference](reference/python-api.md)
  - [Metadata Format](reference/metadata-format.md)
  - [Token Registration](reference/token-registration.md)
