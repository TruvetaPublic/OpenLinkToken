# Match token format

Java and Python use the same version 1 match-token envelope. The formatter wraps
the tokenized value in a compact JWE:

```text
olt.V1.<JWE compact serialization>
```

The `olt.V1.` prefix identifies the envelope version. The JWE body has the
standard five parts:

```text
<protected-header>.<encrypted-key>.<iv>.<ciphertext>.<auth-tag>
```

With direct encryption, the encrypted-key part is empty. The protected header
is readable without the encryption key; the payload is not.

## Current protected header

```json
{
  "alg": "dir",
  "enc": "A256GCM",
  "typ": "match-token",
  "kid": "ring-2026-q1"
}
```

| Field | Description                                       |
| ----- | ------------------------------------------------- |
| `alg` | `dir`: the 256-bit content key is used directly   |
| `enc` | `A256GCM` authenticated encryption                |
| `typ` | `match-token`                                     |
| `kid` | Ring identifier used to select the encryption key |

The current formatter accepts exactly a 32-byte encryption key and emits
`dir` with `A256GCM`. It does not select RSA, ECDH, key-wrapping, or alternate
hash/MAC algorithms.

## Current payload

```json
{
  "rlid": "T1",
  "hash_alg": "SHA-256",
  "mac_alg": "HS256",
  "ppid": ["base64-encoded-HMAC-value"],
  "rid": "ring-2026-q1",
  "iss": "org.openlinktoken",
  "iat": 1738339200
}
```

| Field      | Description                                                            |
| ---------- | ---------------------------------------------------------------------- |
| `rlid`     | Token rule identifier, such as `T1` or `ML1`                           |
| `hash_alg` | `SHA-256`                                                              |
| `mac_alg`  | `HS256` (HMAC-SHA256)                                                  |
| `ppid`     | Array containing the tokenized value; current hash rules use one value |
| `rid`      | Ring identifier                                                        |
| `iss`      | Issuer; defaults to `org.openlinktoken`                                |
| `iat`      | Issued-at time in Unix seconds                                         |

The current formatter emits the fields above. It does not emit expiration or
not-before claims.

## Generation pipeline

For the normal encrypted flow:

```text
normalized signature
  -> SHA-256 hex digest
  -> HMAC-SHA256 with the exchange hashing secret
  -> standard Base64 PPID
  -> JWE AES-256-GCM with the transport key
  -> olt.V1. prefix
```

The JWE IV is random, so two encryptions of the same PPID produce different
`olt.V1` strings. Decrypt tokens before comparing them.

Blank tokens are returned without a JWE wrapper. The `rlid` value comes from
the token rule definition; see [Token rules](../pages/concepts/token-rules.md).

## Key and compatibility notes

- The `olt.V1.` prefix is a deliberate scanner-safe marker: it does not match
  the shape of a JWT access token (`eyJ...`), a provider API key, or an AWS
  credential (`AKIA...`), reducing accidental flags in automated secret
  scanners.
- The encryption key is not stored in the token.
- The protected header can be inspected without decryption, but the PPID and
  rule metadata require the encryption key.
- The Java and Python formatters use the same prefix, header fields, payload
  fields, and algorithms.
- `olt.V1` tokens are distinct from legacy non-JWE token values. Consumers that
  support both formats should detect the prefix before choosing a parser.

This envelope uses [RFC 7516](https://datatracker.ietf.org/doc/html/rfc7516)
JWE compact serialization.

For exchange-key derivation and key-file handling, see
[Exchange configuration format](exchange-config-format.md).
