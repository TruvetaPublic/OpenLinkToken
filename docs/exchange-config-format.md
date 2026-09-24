# Open Link Token Exchange Config Format

## Overview

`olt initiate-exchange` writes one JSON exchange configuration containing an
encrypted hashing secret and the key material needed by both participants.
The matching private key remains local; the JSON file contains public
recipient information only.

The selected crypto suite determines the exchange version:

| Suite                | Token primitives             | Exchange version | Key agreement             | Key material |
| -------------------- | ---------------------------- | ---------------: | ------------------------- | ------------ |
| `suite-sha256-v1`    | SHA-256 and HMAC-SHA256      |                1 | ECDH/JWE                  | PEM          |
| `suite-sha3-v1`      | SHA3-256 and HMAC-SHA3-256   |                1 | ECDH/JWE                  | PEM          |
| `suite-pq-shake-v1`  | SHAKE256-256 and KMAC256-256 |                2 | ML-KEM-768                | JSON bundles |
| `suite-pq-v1`        | SHA3-256 and HMAC-SHA3-256   |                2 | ML-KEM-768                | JSON bundles |
| `suite-pq-hybrid-v1` | SHA3-256 and HMAC-SHA3-256   |                2 | ECDH-P256 plus ML-KEM-768 | JSON bundles |

Both participants can decrypt the same configuration because the sender and
partner public keys are added as JWE recipients. Consumers reject a suite or
version mismatch instead of silently selecting another algorithm.

## Java library boundary

The Java core library provides the same exchange operations without adopting
the Python CLI's filesystem policy:

- `ExchangeJwe` builds and decrypts version-1 ECDH/JWE envelopes.
- `ExchangeKem` builds and decrypts version-2 ML-KEM and hybrid envelopes.
- `ExchangeKeyBundle` generates, parses, and serializes version-2 key bundles.
- `ExchangeConfig` loads caller-supplied JSON or paths and resolves it with
  caller-supplied private PEM or bundle material.

Java callers must provide the input path or JSON and matching private material
explicitly. The library does not read `~/.openlinktoken`, inspect environment
variables, parse CLI arguments, or choose file overwrite/permission policies.

Java exchange and crypto-suite objects support native Java serialization,
preserving private keys and other secret fields. Object streams are not
encrypted and are Java-specific: protect serialized bytes as secrets and never
deserialize streams from untrusted sources. Use the JSON formats below for
cross-language exchange.

## Version 2: standard JWE JSON serialization

Version 2 uses the RFC 7516 general JWE JSON Serialization. The outer object
contains only standard JWE members:

| Member       | Type   | Description                                               |
| ------------ | ------ | --------------------------------------------------------- |
| `protected`  | string | Base64url-encoded authenticated JOSE protected header.    |
| `recipients` | array  | One JWE recipient for each participant.                   |
| `iv`         | string | Base64url-encoded 96-bit `A256GCM` initialization vector. |
| `ciphertext` | string | Base64url-encoded encrypted exchange payload.             |
| `tag`        | string | Base64url-encoded `A256GCM` authentication tag.           |

There is no top-level `version`, `type`, `cryptoSuite`, or custom key-management
member in a version 2 JWE. The version and exchange metadata are authenticated
inside the protected header.

The required protected header is:

```json
{
  "typ": "openlinktoken-exchange+jwe",
  "cty": "application/openlinktoken-exchange+json",
  "enc": "A256GCM",
  "version": 2,
  "cryptoSuite": "suite-pq-hybrid-v1",
  "exchangeId": "0f3d5f8a-3f2a-4c2f-b69d-cb1f9d08d4ab"
}
```

The `exchangeId` is a UUID generated for the exchange. It authenticates the
configuration metadata and is also the HKDF salt for the token transport-key
derivation.

### Recipients

Each object in `recipients` contains the standard JWE `encrypted_key` and an
optional `header` object:

```json
{
  "encrypted_key": "Base64UrlEncoded1128ByteValue",
  "header": {
    "alg": "ECDH-ES+ML-KEM-768",
    "kid": "sha256:11-22-33-44-55-66-77-88",
    "epk": {
      "kty": "EC",
      "crv": "P-256",
      "x": "...",
      "y": "..."
    }
  }
}
```

The recipient `alg` and headers are suite-specific:

| Suite                | `alg`                | Required recipient headers |
| -------------------- | -------------------- | -------------------------- |
| `suite-pq-v1`        | `ML-KEM-768`         | `kid`                      |
| `suite-pq-shake-v1`  | `ML-KEM-768`         | `kid`                      |
| `suite-pq-hybrid-v1` | `ECDH-ES+ML-KEM-768` | `kid`, P-256 `epk`         |

`kid` is a stable identifier derived from the recipient public bundle. It is
not the friendly local name used for files under `~/.openlinktoken/`.

For every version 2 recipient, `encrypted_key` contains:

1. A 1088-byte ML-KEM-768 ciphertext.
2. A 40-byte AES-KW result wrapping the 32-byte JWE content-encryption key
   (CEK).

After base64url decoding, the member is therefore 1128 bytes. For the hybrid
algorithm, the recipient shared secret is the concatenation of the P-256 ECDH
shared secret and the ML-KEM shared secret. Both algorithms derive a
recipient-specific 32-byte AES-KW key with HKDF-SHA256 using the exchange ID
as salt and this domain-separated info:

```text
openlinktoken:jwe:v2:<cryptoSuite>:<alg>:<kid>
```

The CEK is used only by the standard JWE content-encryption layer. After the
payload is authenticated and decrypted, the exchange code derives a separate
32-byte token transport key with HKDF-SHA256:

```text
salt = UTF-8(exchangeId)
info = openlinktoken:token-encryption:v2
```

The transport key, not the CEK, is exposed to token encryption and decryption
consumers.

### Decrypted payload

The JWE plaintext is a JSON object containing the exchange configuration:

| Field                   | Type    | Description                                              |
| ----------------------- | ------- | -------------------------------------------------------- |
| `exchangeName`          | string  | Local logical name recorded by the sender.               |
| `hashingSecret`         | string  | Base64url-encoded hashing secret.                        |
| `hashingSecretEncoding` | string  | Always `base64url`.                                      |
| `senderKeyId`           | string  | Stable sender public-bundle identifier.                  |
| `recipientKeyId`        | string  | Stable partner public-bundle identifier.                 |
| `createdAt`             | string  | UTC creation timestamp in ISO 8601 `Z` form.             |
| `exchangeId`            | string  | Must match the protected header.                         |
| `rotationIv`            | string  | Base64url-encoded rotation-matrix initialization vector. |
| `rotationIvEncoding`    | string  | Always `base64url`.                                      |
| `rotationCount`         | integer | Number of rotation matrices to generate.                 |
| `binWidth`              | number  | Quantization bin width.                                  |
| `dimensionBias`         | array   | Per-dimension rotation bias vector.                      |

The payload may include suite-specific metadata, but consumers must validate
the protected `cryptoSuite`, `version`, and `exchangeId` before accepting it.

## Version 1

Version 1 uses ECDH/JWE and PEM key pairs for `suite-sha256-v1` and
`suite-sha3-v1`. When `cryptoSuite` is absent from the protected header, readers
resolve the legacy default `suite-sha256-v1`, so existing default-suite
envelopes retain their original wire format. For `suite-sha3-v1`, the
authenticated protected header contains `cryptoSuite: "suite-sha3-v1"` and
`crit: ["cryptoSuite"]`. Suite identity is not added to the v1 payload or the
top-level envelope. Readers reject unknown, incompatible, unprotected, or
non-critical suite markers; older readers that do not recognize the critical
parameter will reject these non-default v1 envelopes.

The exchange config uses the standard JWE JSON members `protected`,
`recipients`, `iv`, `ciphertext`, and `tag`. Its recipient algorithm remains
`ECDH-ES+A256KW`. The post-quantum suites continue to use the version 2 format
above, which authenticates `version`, `cryptoSuite`, and `exchangeId` in the
protected header.

Version 1 derives the token transport key with its existing
`openlinktoken:token-encryption:v1` contract. Version 1 behavior is preserved
for existing exchanges and is independent of the version 2 algorithms above.

## Key generation

Version 2 uses JSON key bundles instead of PEM files:

```bash
olt generate-key-pair --crypto-suite suite-pq-v1 --name partner --force
olt initiate-exchange \
  --crypto-suite suite-pq-v1 \
  --public-key ~/.openlinktoken/partner.public.bundle.json \
  --output ./partner.exchange.json
```

The public bundle may be shared. The private bundle contains ML-KEM private
material and must remain local with restrictive permissions. The hybrid
profile also stores the P-256 private key in the private bundle.

Version 1 continues to use PEM key pairs:

```bash
olt generate-key-pair --crypto-suite suite-sha256-v1 --name partner
olt initiate-exchange \
  --crypto-suite suite-sha256-v1 \
  --public-key ~/.openlinktoken/partner.public.pem \
  --output ./partner.exchange.json
```

## Roles

- `sender` runs `olt initiate-exchange`, creates the configuration, and
  contributes the local sender recipient.
- `recipient` supplies a public key bundle or PEM key and decrypts with the
  corresponding local private key.

## Decryption and validation

- The sender and recipient can both decrypt the file because both public keys
  are represented as JWE recipients.
- The exchange config alone cannot recover the hashing secret; a matching
  private key is required.
- `tools/exchange/validate_exchange_secret.py` verifies that a matching key
  decrypts the configuration and that an optional expected secret matches.
- `tools/exchange/inspect_exchange_config.py` resolves and prints the
  authenticated metadata and decrypted payload without exposing private key
  material.
- `tools/exchange/print_exchange_envelope.py` prints the raw standard JWE JSON
  members and, when a private key is supplied, the decoded protected header
  and decrypted payload.

Version 2 key-bundle processing is implemented by both the Python library/CLI
and the Java core library. The Java APIs intentionally do not provide CLI
defaults, environment-variable lookup, or filesystem key discovery; callers
must supply exchange JSON and the matching private key material explicitly.
Both implementations validate the same authenticated headers, payload identity,
key-bundle identifiers, and transport-key derivation contracts. The Java core
library does not add a production exchange CLI.
