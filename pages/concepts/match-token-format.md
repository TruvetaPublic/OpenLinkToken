---
layout: default
---

# Match Token Format

`olt.V1.<compact-JWE>` is the encrypted match-token envelope emitted by the
`package` and `encrypt` CLI commands and by the Java and Python
`JweMatchTokenFormatter` implementations. It wraps a generated token with the
rule and key-ring identifiers needed by the recipient.

## Wire format

The token has the following prefix and JWE compact serialization:

```text
olt.V1.<protected>.<encrypted-key>.<iv>.<ciphertext>.<auth-tag>
```

The five segments after `olt.V1.` are the standard JWE compact serialization:

| Segment         | Current value or meaning           |
| --------------- | ---------------------------------- |
| `protected`     | Base64url-encoded protected header |
| `encrypted-key` | Empty, because `alg` is `dir`      |
| `iv`            | Per-token initialization vector    |
| `ciphertext`    | Encrypted JSON payload             |
| `auth-tag`      | AES-GCM authentication tag         |

Only the protected header is readable without the encryption key. The payload,
including the rule ID and issued-at time, is encrypted.

## Protected header

The current formatter emits this fixed header shape:

```json
{
  "alg": "dir",
  "enc": "A256GCM",
  "typ": "match-token",
  "kid": "ring-2026-q1"
}
```

| Field | Meaning                                       |
| ----- | --------------------------------------------- |
| `alg` | Direct use of the content-encryption key      |
| `enc` | AES-256-GCM content encryption                |
| `typ` | Always `match-token`                          |
| `kid` | Key-ring identifier supplied to the formatter |

The encryption key must be exactly 32 bytes. The formatter does not currently
support RSA, ECDH, `A256GCMKW`, or other alternative JWE key-management
algorithms. ECDH used by exchange-configuration bootstrap is a separate
workflow and does not change this match-token envelope.

## Encrypted payload

The formatter emits the following fields:

```json
{
  "rlid": "T1",
  "hash_alg": "SHA-256",
  "mac_alg": "HS256",
  "ppid": ["<base64-HMAC-output>"],
  "rid": "ring-2026-q1",
  "iss": "org.openlinktoken",
  "iat": 1738339200
}
```

| Field      | Meaning                                                                                                                     |
| ---------- | --------------------------------------------------------------------------------------------------------------------------- |
| `rlid`     | Rule identifier, such as `T1`–`T5`, `ML1`, or a configured custom rule                                                      |
| `hash_alg` | Fixed payload label: `SHA-256`                                                                                              |
| `mac_alg`  | Fixed payload label: `HS256` (HMAC-SHA256)                                                                                  |
| `ppid`     | Single-element array containing the opaque token value passed to the formatter; the formatter does not interpret this value |
| `rid`      | Key-ring identifier, also exposed as `kid` in the protected header                                                          |
| `iss`      | Issuer; defaults to `org.openlinktoken`                                                                                     |
| `iat`      | Issued-at time as Unix seconds                                                                                              |

`exp`, `nbf`, vector-specific fields, and alternative hash or MAC algorithms
are not emitted by the current formatter.

## Token generation

For the standard `package` path, the relevant stages are:

```text
rule signature → SHA-256 → HMAC-SHA256 → AES-256-GCM transform
              → JWE (AES-256-GCM) → olt.V1. prefix
```

The CLI's `package` and `encrypt` paths pass the Base64-encoded result of the
inner encryption transform as `ppid`; library callers can pass another token
value. Normal `tokenize` output is a Base64 HMAC value rather than a JWE. Its
`--mode hash-only` output is lowercase SHA-256 hexadecimal, and demo mode
outputs raw signatures.

## Security properties

- AES-256-GCM provides payload confidentiality and authenticated integrity.
- The `kid` value remains visible so a recipient can select a key ring.
- A token is still sensitive data; the envelope does not remove the need to
  protect token files and encryption keys.

Use a JWE implementation to decrypt and validate the payload. See the
[CLI reference](../reference/cli.md), [Decrypting Tokens](../operations/decrypting-tokens.md),
and [Token Rules](token-rules.md) for command and rule details.

## Standards

The envelope uses [RFC 7516](https://datatracker.ietf.org/doc/html/rfc7516)
JWE compact serialization and the registered algorithm names from
[RFC 7518](https://datatracker.ietf.org/doc/html/rfc7518).

## Further reading

- [Security](../security.md) — Key handling and cryptographic guidance
- [Configuration](../config/configuration.md) — Input, output, and runtime options
- [Full Specification](../specification.md) — Broader processing and interoperability details
