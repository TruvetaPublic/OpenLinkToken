---
description: "OpenLinkToken architecture, parity, and registration guidance"
applyTo: "**"
---

# OpenLinkToken Architecture and Parity Guidance

## Core Model

OpenLinkToken is a dual-implementation library. Java and Python should produce equivalent behavior and byte-identical token outputs for the same normalized input unless a change is explicitly designed otherwise.

Core component areas:

- **Attributes** define normalized person fields
- **Validators** enforce constraints after normalization
- **Tokens** combine attributes into T1-T5 token rules
- **Token transformers** handle hashing and encryption stages
- **CLI I/O** handles CSV/Parquet processing and metadata output

## Registration Rules

When adding new discoverable attributes or tokens, update both language implementations:

- **Java:** add the implementation to the appropriate `META-INF/services/com.truveta.openlinktoken...` ServiceLoader file
- **Python:** update the explicit loader/registry modules such as `attribute_loader.py` and `token_registry.py`

If registration is updated in only one language, treat it as a likely parity or runtime-discovery bug.

## Change-Risk Heuristics

Treat these as parity-sensitive changes that deserve extra scrutiny:

- normalization or validation changes
- token composition/rule changes
- hashing/encryption pipeline changes
- metadata schema or CLI behavior changes

## Verification Guidance

When parity-sensitive code changes land, verify the relevant language tests and use the sync/interoperability tooling when appropriate:

- `tools/multi_language_syncer.py`
- `tools/sync-check.sh`
- interoperability tests under `tools/interoperability/`

For broader developer workflow details, see `docs/dev-guide-development.md`.
