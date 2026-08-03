---
layout: default
---

# Match Token Format

Open Link Token supports a self-contained match token format that embeds versioning and cryptographic metadata directly in each token. This enables continuous data exchange across systems with varying Open Link Token versions and algorithms.

---

## Why Self-Contained Tokens?

Traditional token formats store metadata externally (in file headers or separate configuration). The match token format bundles everything together:

| Benefit                   | Description                                                      |
| ------------------------- | ---------------------------------------------------------------- |
| **Version tracking**      | Each token identifies which Open Link Token version generated it |
| **Cryptographic agility** | Algorithm changes are self-documented per token                  |
| **Ring identification**   | Key management metadata travels with the token                   |
| **Scanner safety**        | Distinct prefix prevents confusion with access tokens            |
| **Batch processing**      | Metadata queryable without decryption                            |

---

## Format Overview

### Serialization

```
olt.V1.<JWE-compact-serialization>
```

**Components:**

| Part    | Description                                          |
| ------- | ---------------------------------------------------- |
| `olt`   | Open Link Token prefix (scanner-safe)                |
| `V1`    | Envelope format version                              |
| `<JWE>` | Standard JWE (RFC 7516) containing encrypted payload |

### Example Token

```
olt.V1.eyJhbGciOiJBMjU2R0NNS1ciLCJlbmMiOiJBMjU2R0NNIiwidHlwIjoibWF0Y2gtdG9rZW4iLCJraWQiOiJyaW5nLTIwMjYtcTEifQ.K7q3nT8Xh2Yk5L9m.Gw5hT2Qk9Lm3Np7R.dGhlIHF1aWNrIGJyb3duIGZveA.4vT8kL2mNpQ9rStYz
```

### Token Structure

The JWE portion has 5 dot-separated components:

```
olt.V1.<header>.<encrypted-key>.<iv>.<ciphertext>.<auth-tag>
      │        │              │    │            │
      │        │              │    │            └─ Integrity proof (GCM tag)
      │        │              │    │
      │        │              │    └─ Encrypted payload lives HERE
      │        │              │
      │        │              └─ Random IV (unique per token)
      │        │
      │        └─ CEK wrapped with KEK (empty for "dir" mode)
      │
      └─ Metadata (alg, enc, kid) - readable WITHOUT decryption
```

**Encryption:** `AES-GCM(CEK, IV, payload) → (ciphertext, auth_tag)`

**Decryption:** `AES-GCM-Decrypt(CEK, IV, ciphertext, auth_tag) → payload`

The authentication tag ensures integrity—any modification to the ciphertext causes decryption to fail.

---

## JWE Header

The protected header (visible without decryption) contains:

```json
{
  "alg": "A256GCMKW",
  "enc": "A256GCM",
  "typ": "match-token",
  "kid": "ring-2026-q1"
}
```

| Field | Purpose                           | Example        |
| ----- | --------------------------------- | -------------- |
| `alg` | Key wrapping algorithm            | `A256GCMKW`    |
| `enc` | Content encryption algorithm      | `A256GCM`      |
| `typ` | Token type (always `match-token`) | `match-token`  |
| `kid` | Ring/key identifier               | `ring-2026-q1` |

### Supported Key Wrapping Algorithms

| Algorithm            | `alg` Value      | Use Case                               |
| -------------------- | ---------------- | -------------------------------------- |
| AES-256-GCM Key Wrap | `A256GCMKW`      | Symmetric (recommended default)        |
| Direct               | `dir`            | Pre-shared symmetric keys              |
| RSA-OAEP-256         | `RSA-OAEP-256`   | Asymmetric (RSA)                       |
| ECDH-ES              | `ECDH-ES`        | Asymmetric (elliptic curve, direct)    |
| ECDH-ES + Key Wrap   | `ECDH-ES+A256KW` | Asymmetric (elliptic curve + AES wrap) |

### ECDH Key Exchange

For ECDH algorithms, the header includes an ephemeral public key:

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

- `epk`: Sender's ephemeral public key
- Receiver derives shared secret using `epk` + their private key
- IV is randomly generated; authentication tag is computed by AES-GCM

---

## Payload Structure

The encrypted payload contains the actual token data:

```json
{
  "rlid": "T1",
  "hash_alg": "SHA-256",
  "mac_alg": "HS256",
  "ppid": ["7Kx9mL2pNqRsTuVw8yZaB3cD4eF5gH6iJ7kL8mN9oP0q"],
  "rid": "ring-2026-q1",
  "iss": "org.openlinktoken",
  "iat": 1738339200
}
```

### Required Fields

| Field      | Type   | Description                                                       |
| ---------- | ------ | ----------------------------------------------------------------- |
| `rlid`     | string | Token rule (T1–T8)                                                |
| `hash_alg` | string | Hash algorithm identifier; current implementations emit `SHA-256` |
| `mac_alg`  | string | MAC algorithm identifier; current implementations emit `HS256`    |
| `ppid`     | array  | Privacy-protected identifier(s)                                   |
| `rid`      | string | Ring identifier                                                   |

### Optional Fields

| Field | Type   | Description                        |
| ----- | ------ | ---------------------------------- |
| `iss` | string | Issuer (who generated the token)   |
| `iat` | number | Issued-at timestamp (Unix seconds) |
| `exp` | number | Expiration timestamp               |
| `nbf` | number | Not-before timestamp               |

---

## Token Rules (`rlid`)

The `rlid` field identifies which token signature rule was used:

### Standard Rules

| ID   | Signature                         | Use Case                |
| ---- | --------------------------------- | ----------------------- |
| `T1` | Last + First[0] + Sex + BirthDate | High recall matching    |
| `T2` | Last + First + BirthDate + ZIP3   | Geographic matching     |
| `T3` | Last + First + Sex + BirthDate    | High precision matching |
| `T4` | SSN + Sex + BirthDate             | SSN-based matching      |
| `T5` | Last + First[0:3] + Sex           | Candidate generation    |

---

## Cryptographic Algorithms

### Hash Algorithms (`hash_alg`)

The Java and Python implementations currently emit `SHA-256` and do not
expose a hash-algorithm selection option. The other identifiers are reserved
for future extensions.

| Identifier                                               | Output Size | Status                                      |
| -------------------------------------------------------- | ----------- | ------------------------------------------- |
| `SHA-256`                                                | 32 bytes    | Implemented and emitted                     |
| `SHA-384`, `SHA-512`, `SHA3-256`, `SHA3-384`, `SHA3-512` | Varies      | Future extension; not currently implemented |

### MAC Algorithms (`mac_alg`)

The Java and Python implementations currently emit `HS256` (HMAC-SHA256)
after SHA-256 hashing. Other MAC identifiers are reserved for future
extensions.

| Identifier                                        | Algorithm   | Output Size | Status                                      |
| ------------------------------------------------- | ----------- | ----------- | ------------------------------------------- |
| `HS256`                                           | HMAC-SHA256 | 32 bytes    | Implemented and emitted                     |
| `HS384`, `HS512`, `HS3-256`, `HS3-384`, `HS3-512` | Varies      | Varies      | Future extension; not currently implemented |

---

## Examples

### Example 1: Standard Configuration (SHA-256 + HMAC-SHA256 + AES-256-GCM)

**Protected Header:**

```json
{
  "alg": "A256GCMKW",
  "enc": "A256GCM",
  "typ": "match-token",
  "kid": "ring-2026-q1"
}
```

**Payload:**

```json
{
  "rlid": "T1",
  "hash_alg": "SHA-256",
  "mac_alg": "HS256",
  "ppid": ["7Kx9mL2pNqRsTuVw8yZaB3cD4eF5gH6iJ7kL8mN9oP0q"],
  "rid": "ring-2026-q1",
  "iss": "org.openlinktoken",
  "iat": 1738339200
}
```

### Example 2: Vector Embedding (ML1)

For ML-based matching with vector embeddings, the `ppid` contains base64-encoded binary:

**Payload:**

```json
{
  "rlid": "ML1",
  "hash_alg": "SHA-256",
  "mac_alg": "HS256",
  "ppid": [
    "SGVsbG8gV29ybGQhIFRoaXMgaXMgYSBiYXNlNjQgZW5jb2RlZCBmbG9hdDMyIGFycmF5..."
  ],
  "ppid_dtype": "float32",
  "ppid_dims": 1024,
  "rid": "ring-2026-q1",
  "iss": "org.openlinktoken",
  "iat": 1738339200
}
```

---

## Processing Examples

### Generating a Match Token

```python
from jose import jwe
import json
from datetime import datetime

def create_olt_token(
    ppid: list,
    rlid: str,
    ring_id: str,
    encryption_key: bytes,
    hash_alg: str = "SHA-256",
    mac_alg: str = "HS256",
    issuer: str = None
) -> str:
    """Create a self-contained Open Link Token."""

    # Build payload
    payload = {
        "rlid": rlid,
        "hash_alg": hash_alg,
        "mac_alg": mac_alg,
        "ppid": ppid,
        "rid": ring_id,
        "iat": int(datetime.utcnow().timestamp())
    }
    if issuer:
        payload["iss"] = issuer

    # Create JWE with custom headers
    protected = {
        "alg": "A256GCMKW",
        "enc": "A256GCM",
        "typ": "match-token",
        "kid": ring_id
    }

    jwe_token = jwe.encrypt(
        json.dumps(payload).encode(),
        encryption_key,
        algorithm="A256GCMKW",
        encryption="A256GCM",
        headers=protected
    )

    return f"olt.V1.{jwe_token.decode()}"
```

### Parsing Without Decryption

Extract metadata from the header without needing the decryption key:

```python
import json
import base64

def parse_olt_token_header(token: str) -> dict:
    """Extract header metadata without decryption."""

    if not token.startswith("olt."):
        raise ValueError("Not an Open Link Token")

    parts = token.split(".")
    format_version = parts[1]  # "V1"

    # Decode JWE protected header (third part)
    header_b64 = parts[2]
    # Add padding if needed
    padding = 4 - len(header_b64) % 4
    if padding != 4:
        header_b64 += "=" * padding

    header = json.loads(base64.urlsafe_b64decode(header_b64))

    return {
        "format_version": format_version,
        "ring_id": header.get("kid"),
        "algorithm": header.get("alg"),
        "encryption": header.get("enc")
    }
```

### Full Decryption

```python
def decrypt_olt_token(token: str, encryption_key: bytes) -> dict:
    """Decrypt and return full payload."""

    if not token.startswith("olt.V1."):
        raise ValueError("Unsupported format version")

    jwe_token = token[len("olt.V1."):]
    payload_bytes = jwe.decrypt(jwe_token, encryption_key)

    return json.loads(payload_bytes)
```

---

## Security Benefits

### Scanner Safety

The `olt.V1.` prefix clearly identifies these tokens:

```
olt.V1.eyJhbGci... ← Open Link Token (clearly labeled)
eyJhbGciOiJIUzI1NiIs...     ← JWT (could trigger scanners)
AKIA1234567890ABCDEF...     ← AWS key (definitely triggers scanners)
```

### Cryptographic Properties

| Property           | Mechanism                 |
| ------------------ | ------------------------- |
| Confidentiality    | AES-256-GCM encryption    |
| Integrity          | GCM authentication tag    |
| Key identification | `kid` header field        |
| Algorithm agility  | `alg`/`enc` header fields |

---

## Standards Compliance

This format builds on established IETF standards:

| Standard                                                  | Usage                           |
| --------------------------------------------------------- | ------------------------------- |
| [RFC 7516](https://datatracker.ietf.org/doc/html/rfc7516) | JWE structure and serialization |
| [RFC 7517](https://datatracker.ietf.org/doc/html/rfc7517) | Key identification (`kid`)      |
| [RFC 7518](https://datatracker.ietf.org/doc/html/rfc7518) | Algorithm identifiers           |

---

## Further Reading

- [Token Rules](token-rules.md) — Standard token generation rules (T1–T5)
- [Security](../security.md) — Cryptographic building blocks
- [Configuration](../config/configuration.md) — Configuration options for inputs, outputs, secrets, and runtime behavior
- [Full Specification](../specification.md) — Detailed technical specification
