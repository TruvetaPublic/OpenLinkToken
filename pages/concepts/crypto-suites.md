---
layout: default
title: Cryptographic Suites
---

# Cryptographic Suites

Open Link Token uses a **cryptographic suite** to select the algorithms used
for both deterministic token generation and exchange key establishment. A suite
is a complete algorithm contract: every organization participating in an
exchange must use the same suite.

The suite is selected when key material and the exchange config are created.
Commands that consume an exchange config (`package`, default `tokenize`,
`encrypt`, and `decrypt`) read the suite from that config. They do not silently
fall back to another suite when the suite, exchange version, or key material
does not match.

> **Important:** Changing suites changes the generated token values. A dataset
> generated with one suite cannot be matched with tokens generated using
> another suite, even when the input attributes are identical.

## What a suite controls

Each suite fixes all of the following:

- **Token digest**: the unkeyed digest applied to each token signature.
- **Token MAC**: the keyed operation that makes deterministic tokens resistant
  to guessing without the hashing secret.
- **Token content encryption**: AES-256-GCM for all currently supported suites.
- **Exchange key agreement**: the mechanism used to protect the exchange
  payload's transport key.
- **Exchange config version**: the envelope and key-material format used by the
  exchange workflow.

Post-quantum suites use **ML-KEM-768** for exchange key establishment. This is
separate from the token digest and MAC: a suite can use a post-quantum exchange
while still using SHA-3 and HMAC for its deterministic token primitives.
Version 2 exchanges use the RFC 7516 general JWE JSON Serialization with
the custom key-management algorithm identifier `ML-KEM-768` for both
`mlkem768-sha3-256` and `mlkem768-shake256`.

The JWE content-encryption key is used only for the exchange payload. The
exchange implementation derives a separate token transport key from that CEK
and the authenticated exchange ID, so token consumers never use the CEK
directly.

## Supported suites

| Suite ID            | Token digest | Token MAC                 | Exchange format version and key agreement | Key material     | Choose it when                                                                                                    |
| ------------------- | ------------ | ------------------------- | ----------------------------------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------- |
| `ecdh-sha256`       | SHA-256      | HMAC-SHA256 (`HS256`)     | Version 1, ECDH/JWE                       | PEM              | You need the backward-compatible default or must interoperate with an existing version-1 exchange.                |
| `ecdh-sha3-256`     | SHA3-256     | HMAC-SHA3-256 (`HS3-256`) | Version 1, ECDH/JWE                       | PEM              | All participants support version 1 and you want SHA-3 token primitives without changing the ECDH exchange format. |
| `mlkem768-sha3-256` | SHA3-256     | HMAC-SHA3-256 (`HS3-256`) | Version 2, ML-KEM-768                     | JSON key bundles | You want a post-quantum-only exchange and SHA-3/HMAC token primitives.                                            |
| `mlkem768-shake256` | SHAKE256-256 | KMAC256-256               | Version 2, ML-KEM-768                     | JSON key bundles | You want a post-quantum-only exchange and the SHAKE/KMAC family for token primitives.                             |

All suites use AES-256-GCM for token content encryption. Suite IDs have no
version suffix. Exchange format versions remain separate protocol metadata:
the ECDH suites use version 1 and the ML-KEM suites use version 2.
Exchanges use either ECDH or ML-KEM, never a combination of both.

### Reading a suite name

Names follow `<key-agreement>-<digest>`. `ecdh` selects classical ECDH;
`mlkem768` selects ML-KEM-768. ECDH curves remain selectable independently.
`sha256` means SHA-256, `sha3-256` means SHA3-256, and `shake256` means
SHAKE256 with a fixed 256-bit output.

The MAC is implicit in the registered profile: SHA-256 uses HMAC-SHA256,
SHA3-256 uses HMAC-SHA3-256, and SHAKE256 uses KMAC256 with a 256-bit output.
All four profiles use AES-256-GCM. These names identify fixed registered
profiles; they are not expressions for composing arbitrary algorithms.

Former `suite-` IDs, with or without version suffixes, are not accepted.
Regenerate exchange configs and JSON key bundles that explicitly name them;
editing an existing artifact's suite field is not a valid migration because
the ID is bound into authenticated metadata and key derivation.

## How to choose a suite

Use this decision guide before creating keys or an exchange config:

1. **Are you joining an existing exchange?**
   Use the suite recorded by that exchange. For an existing default exchange,
   this is usually `ecdh-sha256`. Do not create a new suite just because it
   is newer; all participants must use the same suite and hashing secret.
2. **Do you need to keep the version-1 ECDH/JWE format?**
   Choose `ecdh-sha256` for existing behavior or `ecdh-sha3-256` when the
   participants have agreed to SHA-3 token primitives.
3. **Is post-quantum key establishment required for a new exchange?**
   Choose a version-2 suite. Use `mlkem768-sha3-256` for ML-KEM-only exchange with
   SHA-3/HMAC token primitives, or `mlkem768-shake256` for ML-KEM-only exchange
   with SHAKE/KMAC token primitives.
4. **Are you unsure which post-quantum token primitives to use?**
   Choose `mlkem768-sha3-256` unless a policy or interoperability requirement
   specifically calls for SHAKE/KMAC. It provides the simpler post-quantum
   profile while retaining SHA-3/HMAC token behavior.

### Quick recommendations

| Requirement                                    | Recommended suite   |
| ---------------------------------------------- | ------------------- |
| Preserve existing token compatibility          | `ecdh-sha256`       |
| Version-1 exchange with SHA-3 token primitives | `ecdh-sha3-256`     |
| New post-quantum-only deployment               | `mlkem768-sha3-256` |
| Post-quantum-only deployment with SHAKE/KMAC   | `mlkem768-shake256` |

## Key generation and exchange setup

Pass the same suite ID to both `generate-key-pair` and
`initiate-exchange`. The key file format depends on the exchange version:

### Version 1: ECDH/JWE and PEM keys

Version-1 suites use PEM key pairs. The curve can be selected for the ECDH
key pair; P-256 is the default.

```bash
olt generate-key-pair \
  --crypto-suite ecdh-sha256 \
  --name partner

olt initiate-exchange \
  --crypto-suite ecdh-sha256 \
  --public-key ~/.openlinktoken/partner.public.pem \
  --output ./partner.exchange.json
```

The private key remains local. Share only the public key and the exchange
config.

### Version 2: ML-KEM exchange and JSON bundles

Version-2 suites use JSON key bundles instead of PEM files:

```bash
olt generate-key-pair \
  --crypto-suite mlkem768-sha3-256 \
  --name partner

olt initiate-exchange \
  --crypto-suite mlkem768-sha3-256 \
  --public-key ~/.openlinktoken/partner.public.bundle.json \
  --output ./partner.exchange.json
```

This creates:

- `<name>.public.bundle.json` containing public ML-KEM material. This file may
  be shared.
- `<name>.private.bundle.json` containing the private material. Keep it local
  and protect it as a secret.

The `--curve` option applies only to version-1 ECDH PEM generation. Version-2
key bundles use only ML-KEM-768.

For a field-by-field description of both exchange versions, see the
`docs/exchange-config-format.md` reference in the repository.

## Operational rules

- Select the suite before generating keys. Existing keys and exchange configs
  cannot be safely converted to another suite.
- Both sides must use the same suite ID, exchange config, and resolved hashing
  secret.
- Keep private PEM keys and private JSON bundles out of transfer packages,
  source control, logs, and tickets.
- Treat a new suite as a new token namespace. During migration, run both
  profiles deliberately and label the outputs rather than mixing them.
- `mlkem768-shake256` requires a hashing secret of at least 32 bytes because
  KMAC256 uses the secret directly as a KMAC key. Use a high-entropy secret
  from a secret manager or secure environment input.
- Version-2 key bundles are larger and have more exchange processing overhead
  than version-1 PEM/ECDH keys. Account for that when selecting a suite for
  high-volume key provisioning or constrained environments.

## Related documentation

- [Configuration guide](../config/configuration.md) - CLI setup and secret requirements
- [CLI reference](../reference/cli.md) - Complete suite and exchange flags
- [Sharing tokenized data](../operations/sharing-tokenized-data.md) - Partner exchange workflow
- [Security](../security.md) - Key management and cryptographic safeguards
- `docs/exchange-config-format.md` - Repository reference for envelope details
