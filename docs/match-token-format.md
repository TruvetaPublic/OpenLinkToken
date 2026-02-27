# Match Token Format Specification

This document describes the self-contained match token format for OpenToken, designed for continuous data exchange with versioning support and cryptographic agility.

## Overview

Match tokens are privacy-protected identifiers generated from normalized person attributes. Each token is self-contained, embedding all metadata required for proper versioning and processing without external context.

### Design Goals

| Goal                | Description                                                      |
| ------------------- | ---------------------------------------------------------------- |
| **Self-contained**  | All cryptographic and versioning metadata embedded in each token |
| **Standards-based** | Built on JOSE/JWE (RFC 7516) for cryptographic agility           |
| **Scanner-safe**    | Distinct prefix prevents confusion with access tokens            |
| **Batch-friendly**  | Metadata extractable without decryption for efficient querying   |
| **Extensible**      | Supports traditional hash tokens and vector embeddings           |

## Token Structure

### Serialization Format

```
ot.V1.<base64url(JWE)>
```

| Component | Description                                                        |
| --------- | ------------------------------------------------------------------ |
| `ot`      | OpenToken prefix (scanner-safe, clearly not an access token)       |
| `V1`      | Format version (allows future evolution of the envelope structure) |
| `<JWE>`   | Standard JWE Compact Serialization (RFC 7516)                      |

### JWE Structure

The JWE portion follows standard JOSE compact serialization:

```
<protected-header>.<encrypted-key>.<iv>.<ciphertext>.<auth-tag>
```

All components are base64url-encoded.

**Component breakdown:**

```
ot.V1.<header>.<encrypted-key>.<iv>.<ciphertext>.<auth-tag>
      │        │              │    │            │
      │        │              │    │            └─ Integrity proof (GCM tag)
      │        │              │    │
      │        │              │    └─ Encrypted payload lives HERE
      │        │              │
      │        │              └─ Random initialization vector (unique per token)
      │        │
      │        └─ CEK wrapped with KEK (empty for "dir" mode)
      │
      └─ Metadata (alg, enc, kid) - readable WITHOUT decryption
```

**Encryption process:**

```
AES-GCM-Encrypt(CEK, IV, plaintext_payload) → (ciphertext, auth_tag)
                         │
                         └─ {"rlid":"T1","hash_alg":"SHA-256","ppid":[...],...}
```

**Decryption process:**

```
AES-GCM-Decrypt(CEK, IV, ciphertext, auth_tag) → plaintext_payload
```

The authentication tag verifies integrity—if anyone modifies the ciphertext, decryption fails.

## Protected Header

The JWE protected header contains cryptographic parameters and token type identification:

```json
{
  "alg": "A256GCMKW",
  "enc": "A256GCM",
  "typ": "match-token",
  "kid": "ring-2026-q1"
}
```

| Field | Description                                  | Required |
| ----- | -------------------------------------------- | -------- |
| `alg` | Key wrapping algorithm (JOSE registry)       | Yes      |
| `enc` | Content encryption algorithm (JOSE registry) | Yes      |
| `typ` | Token type identifier (always `match-token`) | Yes      |
| `kid` | Key identifier / ring ID for key management  | Yes      |

### Supported Algorithms

#### Symmetric Key Wrapping

| Algorithm            | `alg` Value | `enc` Value | Notes               |
| -------------------- | ----------- | ----------- | ------------------- |
| AES-256-GCM Key Wrap | `A256GCMKW` | `A256GCM`   | Recommended default |
| Direct AES-256-GCM   | `dir`       | `A256GCM`   | For pre-shared keys |

#### Asymmetric Key Wrapping

| Algorithm          | `alg` Value      | `enc` Value | Notes                          |
| ------------------ | ---------------- | ----------- | ------------------------------ |
| RSA-OAEP-256       | `RSA-OAEP-256`   | `A256GCM`   | RSA public key encryption      |
| ECDH-ES (direct)   | `ECDH-ES`        | `A256GCM`   | Ephemeral-static key agreement |
| ECDH-ES + Key Wrap | `ECDH-ES+A256KW` | `A256GCM`   | ECDH with AES key wrapping     |

#### ECDH Key Agreement

When using ECDH algorithms, the header includes an ephemeral public key (`epk`):

```json
{
  "alg": "ECDH-ES+A256KW",
  "enc": "A256GCM",
  "typ": "match-token",
  "kid": "ring-2026-q1",
  "epk": {
    "kty": "EC",
    "crv": "P-256",
    "x": "WKn-ZIGevcwGFOM...",
    "y": "y77t-RvAHRKTsSG..."
  }
}
```

| Field | Description                                |
| ----- | ------------------------------------------ |
| `epk` | Sender's ephemeral public key (EC point)   |
| `crv` | Elliptic curve (`P-256`, `P-384`, `P-521`) |

The receiver combines `epk` with their private key to derive the shared secret. The IV is randomly generated per token, and the authentication tag is computed by AES-GCM.

## Payload Structure

The encrypted payload contains the privacy-protected identifiers and metadata:

```json
{
  "rlid": "T1",
  "hash_alg": "SHA-256",
  "mac_alg": "HS256",
  "ppid": ["base64url-encoded-identifier"],
  "rid": "ring-2026-q1",
  "iss": "org.example",
  "iat": 1738339200,
  "exp": 1769875200,
  "nbf": 1738339200
}
```

### Required Fields

| Field      | Type   | Description                                                   |
| ---------- | ------ | ------------------------------------------------------------- |
| `rlid`     | string | Token rule identifier (e.g., `T1`–`T5`)                       |
| `hash_alg` | string | Hash algorithm used before HMAC (e.g., `SHA-256`, `SHA3-512`) |
| `mac_alg`  | string | HMAC algorithm identifier (e.g., `HS256`, `HS384`, `HS512`)   |
| `ppid`     | array  | Array of base64url-encoded privacy-protected identifiers      |
| `rid`      | string | Ring identifier for key selection                             |

### Optional Fields

| Field | Type   | Description                               |
| ----- | ------ | ----------------------------------------- |
| `iss` | string | Issuer - entity that generated the token  |
| `iat` | number | Issued-at timestamp (Unix epoch seconds)  |
| `exp` | number | Expiration timestamp (Unix epoch seconds) |
| `nbf` | number | Not-before timestamp (Unix epoch seconds) |

### Token Rule Identifiers (`rlid`)

| Identifier | Description                       | PPID Format |
| ---------- | --------------------------------- | ----------- |
| `T1`       | Last + First[0] + Sex + BirthDate | Single hash |
| `T2`       | Last + First + BirthDate + ZIP3   | Single hash |
| `T3`       | Last + First + Sex + BirthDate    | Single hash |
| `T4`       | SSN + Sex + BirthDate             | Single hash |
| `T5`       | Last + First[0:3] + Sex           | Single hash |

### Hash Algorithm Identifiers (`hash_alg`)

| Identifier | Output Size | Notes                  |
| ---------- | ----------- | ---------------------- |
| `SHA-256`  | 32 bytes    | Default, FIPS approved |
| `SHA-384`  | 48 bytes    | FIPS approved          |
| `SHA-512`  | 64 bytes    | FIPS approved          |
| `SHA3-256` | 32 bytes    | NIST standard          |
| `SHA3-384` | 48 bytes    | NIST standard          |
| `SHA3-512` | 64 bytes    | NIST standard          |

### MAC Algorithm Identifiers (`mac_alg`)

| Identifier | Algorithm     | Output Size | Notes                    |
| ---------- | ------------- | ----------- | ------------------------ |
| `HS256`    | HMAC-SHA256   | 32 bytes    | Default, JOSE registered |
| `HS384`    | HMAC-SHA384   | 48 bytes    | JOSE registered          |
| `HS512`    | HMAC-SHA512   | 64 bytes    | JOSE registered          |
| `HS3-256`  | HMAC-SHA3-256 | 32 bytes    | Custom                   |
| `HS3-384`  | HMAC-SHA3-384 | 48 bytes    | Custom                   |
| `HS3-512`  | HMAC-SHA3-512 | 64 bytes    | Custom                   |

## Examples

### Example 1: Standard Configuration (SHA-256 + HMAC-SHA256 + AES-256-GCM)

**Input Record:**

```json
{
  "FirstName": "Thomas",
  "LastName": "O'Reilly",
  "BirthDate": "11/03/1995",
  "Sex": "Male"
}
```

**Normalized Signature:**

```
OREILLY|T|M|1995-11-03
```

**Match Token:**

```
ot.V1.eyJhbGciOiJBMjU2R0NNS1ciLCJlbmMiOiJBMjU2R0NNIiwidHlwIjoibWF0Y2gtdG9rZW4iLCJraWQiOiJyaW5nLTIwMjYtcTEifQ.K7q3nT8Xh2Yk5L9mNpQ4rS.Gw5hT2Qk9Lm3Np7R.dGhlIHF1aWNrIGJyb3duIGZveA.4vT8kL2mNpQ9rStYz
```

**Protected Header (decoded):**

```json
{
  "alg": "A256GCMKW",
  "enc": "A256GCM",
  "typ": "match-token",
  "kid": "ring-2026-q1"
}
```

**Payload (decrypted):**

```json
{
  "rlid": "T1",
  "hash_alg": "SHA-256",
  "mac_alg": "HS256",
  "ppid": ["7Kx9mL2pNqRsTuVw8yZaB3cD4eF5gH6iJ7kL8mN9oP0qRs"],
  "rid": "ring-2026-q1",
  "iss": "truveta.opentoken",
  "iat": 1738339200
}
```

### Example 2: High-Security Configuration (SHA3-512 + HMAC-SHA512 + RSA-OAEP-256)

**Protected Header (decoded):**

```json
{
  "alg": "RSA-OAEP-256",
  "enc": "A256GCM",
  "typ": "match-token",
  "kid": "ring-2026-q1-highsec"
}
```

**Payload (decrypted):**

```json
{
  "rlid": "T1",
  "hash_alg": "SHA3-512",
  "mac_alg": "HS512",
  "ppid": [
    "dGhpcyBpcyBhIFNIQTMtNTEyIHRoZW4gSE1BQy1TSEE1MTIgaGFzaCB3aGljaCBpcyA2NCBieXRlcw"
  ],
  "rid": "ring-2026-q1-highsec",
  "iss": "truveta.opentoken",
  "iat": 1738339200
}
```

**Differences from Standard:**

- `hash_alg`: SHA3-512 (64-byte output) vs SHA-256 (32-byte output)
- `mac_alg`: HS512 (HMAC-SHA512) vs HS256 (HMAC-SHA256)
- `alg`: RSA-OAEP-256 (asymmetric key wrapping) vs A256GCMKW (symmetric)

### Example 3: Vector Embedding (T8)

For ML-based matching with vector embeddings, the `ppid` contains base64-encoded binary:

**Payload (decrypted):**

```json
{
  "rlid": "T8",
  "hash_alg": "SHA-256",
  "mac_alg": "HS256",
  "ppid": ["SGVsbG8gV29ybGQhIFRoaXMgaXMgYSBiYXNlNjQgZW5jb2RlZCBmbG9hdDMyIGFycmF5..."],
  "ppid_dtype": "float32",
  "ppid_dims": 768,
  "rid": "ring-2026-q1",
  "iss": "truveta.opentoken",
  "iat": 1738339200
}
```

## Token Processing Pipeline

### Generation

```
1. Normalize attributes → Token Signature
2. Hash(signature, hash_alg) → Hash digest
3. HMAC(hash, ring_key, mac_alg) → PPID
4. Build payload JSON with metadata (rlid, hash_alg, mac_alg, ppid, rid, ...)
5. Encrypt payload with JWE (alg, enc from header)
6. Prepend "ot.V1." prefix
```

### Parsing (Without Decryption)

The following metadata is extractable from the JWE header without decryption:

```python
def parse_ot_token(token: str) -> dict:
    """Extract metadata without decryption."""
    if not token.startswith("ot."):
        raise ValueError("Invalid ot token format")

    parts = token.split(".")
    format_version = parts[1]  # "V1"

    # JWE header is the third part (index 2), base64url-encoded
    header_b64 = parts[2]
    header = json.loads(base64url_decode(header_b64))

    return {
        "format_version": format_version,
        "algorithm": header.get("alg"),
        "encryption": header.get("enc"),
        "token_type": header.get("typ"),
        "ring_id": header.get("kid")
    }
```

### Decryption

Full decryption requires the ring-specific encryption key:

```python
def decrypt_ot_token(token: str, key: bytes) -> dict:
    """Decrypt and return full payload."""
    if not token.startswith("ot.V1."):
        raise ValueError("Invalid ot token format")

    jwe_token = token[len("ot.V1."):]
    payload_bytes = jwe.decrypt(jwe_token, key)
    return json.loads(payload_bytes)
```

## Security Considerations

### Scanner Safety

The `ot.V1.` prefix clearly distinguishes these tokens from:

- JWT access tokens (which start with `eyJ`)
- API keys (which have provider-specific prefixes)
- AWS credentials (which start with `AKIA`)

### Key Management

- Ring IDs (`rid`, `kid`) identify which key set to use
- Keys are never embedded in tokens—only fingerprints/identifiers
- Ring rotation: new `kid` values for key rotation without breaking old tokens

### Encryption Properties

- AES-256-GCM provides authenticated encryption
- Random IV per token prevents pattern analysis
- GCM tag ensures integrity (tampering detection)

## Compatibility

### JOSE Library Support

This format is compatible with standard JOSE/JWE libraries:

| Language   | Library                         |
| ---------- | ------------------------------- |
| Java       | jose4j, Nimbus JOSE+JWT         |
| Python     | python-jose, jwcrypto           |
| JavaScript | jose, node-jose                 |
| Go         | go-jose                         |
| .NET       | System.IdentityModel.Tokens.Jwt |

## Version History

| Version | Date    | Changes               |
| ------- | ------- | --------------------- |
| V1      | 2026-01 | Initial specification |

## References

- [RFC 7516 - JSON Web Encryption (JWE)](https://datatracker.ietf.org/doc/html/rfc7516)
- [RFC 7517 - JSON Web Key (JWK)](https://datatracker.ietf.org/doc/html/rfc7517)
- [RFC 7518 - JSON Web Algorithms (JWA)](https://datatracker.ietf.org/doc/html/rfc7518)
- [OpenToken Token Rules](../pages/concepts/token-rules.md)
- [OpenToken Security](../pages/security.md)
