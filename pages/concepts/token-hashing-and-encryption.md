---
layout: default
title: Token Hashing and Encryption
---

# Token Hashing and Encryption

Open Link Token uses two different protections for tokens:

- **Hashing** creates deterministic values that can be compared for matching.
- **Encryption** protects those hashed values when tokens are stored or shared
  outside the producing system.

Decryption removes the encryption layer. It does **not** recover the original
person attributes because hashing is intentionally one-way.

## The three token transformations

### Hashing for deterministic matching

The normal `tokenize` flow converts each normalized token signature into a
secret-keyed value:

```text
Normalized attributes
  ↓
Token rule signature
  ↓
Suite-selected digest
  ↓
Suite-selected keyed MAC using the hashing secret
  ↓
Base64-encoded hashed token
```

The digest and MAC are selected by the crypto suite:

| Suite family                                         | Digest       | Keyed MAC     |
| ---------------------------------------------------- | ------------ | ------------- |
| `suite-sha256-v1`                                    | SHA-256      | HMAC-SHA256   |
| `suite-sha3-v1`, `suite-pq-v1`, `suite-pq-hybrid-v1` | SHA3-256     | HMAC-SHA3-256 |
| `suite-pq-shake-v1`                                  | SHAKE256-256 | KMAC256-256   |

The same normalized attributes, suite, and hashing secret produce the same
hashed token. Changing any of those inputs produces a different token
namespace, so participants must agree on the suite before exchanging data.

### Hash-only and demo modes

`tokenize` also supports modes for local experiments:

```bash
# Deterministic SHA-256 without a hashing secret
olt tokenize \
  -i input.csv \
  -o hash-only.csv \
  --mode hash-only

# Raw token-rule signatures for demonstrations and debugging
olt tokenize \
  -i input.csv \
  -o demo.csv \
  --mode demo
```

Hash-only mode skips the keyed MAC. Demo mode skips cryptographic
transformation entirely. Neither mode is suitable for sharing production
tokens across organizations.

### Encryption for transport and storage

The `package` and `encrypt` flows add authenticated encryption around the
hashed token:

```text
Normalized attributes
  ↓
Token rule signature
  ↓
Suite-selected digest and keyed MAC
  ↓
Hashed token payload
  ↓
AES-256-GCM with a fresh IV
  ↓
JWE compact token with the `olt.V1.` prefix
```

The encrypted payload includes the hashed identifier and the metadata needed
to interpret it, such as the rule ID, digest algorithm, MAC algorithm, and key
ring identifier. The JWE header and token prefix identify the envelope format,
but the protected payload cannot be read without the matching encryption key.

All currently supported suites use AES-256-GCM for token content encryption.
Post-quantum suites change the token digest/MAC and exchange key agreement;
they do not replace AES-256-GCM with a post-quantum symmetric cipher.

For the serialized JWE structure, see [Match Token Format](match-token-format.md).

### Decryption

The `decrypt` flow verifies and removes the JWE/AES-256-GCM layer:

```text
`olt.V1.<JWE>` token
  ↓
Authenticated AES-256-GCM decryption
  ↓
Hashed token payload
```

The result is equivalent to the normal `tokenize` output for the same input,
suite, and hashing secret. Decryption does not reveal names, dates, addresses,
or other original attributes:

```text
Original attributes
  ↓
Normalized token signature
  ↓
Digest + keyed MAC
  ↓
Encrypted token
  ↓
Decryption reveals the digest/MAC result, not the original attributes
```

Use the same exchange config and a matching private key:

```bash
olt decrypt \
  -i encrypted.csv \
  -o hashed.csv \
  --exchange-config ./exchange.json
```

Only a holder of a matching private key should be able to resolve the
transport encryption key from the exchange config. The decrypted output
remains sensitive because keyed hashes can still be compared and linked.

## Secrets and key roles

The workflows use separate cryptographic materials for separate purposes:

| Material              | Protects                                   | Used by                                                     |
| --------------------- | ------------------------------------------ | ----------------------------------------------------------- |
| Hashing secret        | Deterministic token generation             | `tokenize`, `package`, `encrypt`, and decryption validation |
| Exchange private key  | Access to protected exchange-config values | `package`, `encrypt`, and `decrypt`                         |
| Derived transport key | Encrypted token content                    | `package`, `encrypt`, and `decrypt`                         |

The exchange config carries the hashing secret and transport-key material in a
protected, versioned envelope. Keep private keys and exchange configs out of
source control, logs, and unencrypted transfer packages. Prefer environment
variables or a managed secret store for explicit secret overrides.

## How crypto suites affect the pipeline

Crypto suites are complete, versioned contracts. They select:

- the digest and keyed MAC used for deterministic token values;
- the key agreement used to protect the exchange config;
- the exchange-config version and key-material format; and
- the token content-encryption algorithm.

The current post-quantum suites use ML-KEM-768 for exchange key agreement.
`suite-pq-hybrid-v1` combines ML-KEM-768 with ECDH-P256. The token payload
still uses AES-256-GCM, and decryption still returns hashed values rather than
original attributes.

See [Cryptographic Suites](crypto-suites.md) for suite selection and
key-generation guidance.

## Choosing a flow

| Goal                                                | Flow                        |
| --------------------------------------------------- | --------------------------- |
| Create deterministic tokens for internal matching   | `tokenize`                  |
| Experiment without a secret                         | `tokenize --mode hash-only` |
| Inspect rule signatures during development          | `tokenize --mode demo`      |
| Share protected tokens with another organization    | `package` or `encrypt`      |
| Remove encryption from received tokens for matching | `decrypt`                   |

For operational decryption guidance, see [Decrypting Tokens](../operations/decrypting-tokens.md).
