# Open Link Token Exchange Config Format

## Overview

`olt initiate-exchange` writes a single JSON exchange artifact that contains:

- a top-level `version` field with value `1`
- a JSON JWE envelope with shared ciphertext fields
- two JWE recipients: one for the sender's local key and one for the partner's key

Both sides can decrypt the same file because both public keys are included as JWE
recipients when the artifact is created. The file does **not** embed any private
key material.

## Roles

- `sender`: the party that runs `olt initiate-exchange`, creates the
  exchange artifact, and contributes the local sender key entry written into
  `recipients`
- `recipient`: the counterparty whose public key is supplied to
  `olt initiate-exchange` and whose matching private key can decrypt the
  recipient entry in `recipients`

## Top-Level Structure

The exchange config is a JSON object with these fields:

| Field        | Type    | Description                                                                               |
| ------------ | ------- | ----------------------------------------------------------------------------------------- |
| `version`    | integer | Artifact format marker. Current value: `1`.                                               |
| `protected`  | string  | Base64url-encoded protected JOSE header shared by all recipients.                         |
| `iv`         | string  | Base64url AES-GCM initialization vector for the ciphertext.                               |
| `ciphertext` | string  | Base64url ciphertext for the encrypted payload.                                           |
| `tag`        | string  | Base64url AES-GCM authentication tag.                                                     |
| `recipients` | array   | Per-recipient JWE entries. Open Link Token writes one sender entry and one partner entry. |

This is a JWE JSON serialization with shared ciphertext fields and per-recipient
key-wrapping metadata.

## Protected Header

The `protected` value decodes to a JSON object shared by all recipients:

| Field | Type   | Description                                                                     |
| ----- | ------ | ------------------------------------------------------------------------------- |
| `typ` | string | JWE type marker. Current value: `openlinktoken-exchange+jwe`.                   |
| `cty` | string | Payload content type. Current value: `application/openlinktoken-exchange+json`. |
| `enc` | string | Content-encryption algorithm. Current value: `A256GCM`.                         |

Example decoded protected header:

```json
{
  "typ": "openlinktoken-exchange+jwe",
  "cty": "application/openlinktoken-exchange+json",
  "enc": "A256GCM"
}
```

## Recipient Entries

Each item in `recipients` contains the wrapped key for one decrypting party.

| Field           | Type   | Description                                                  |
| --------------- | ------ | ------------------------------------------------------------ |
| `encrypted_key` | string | Base64url wrapped content-encryption key for this recipient. |
| `header`        | object | Recipient-specific JOSE header.                              |

### Recipient Header

| Field | Type   | Description                                                                      |
| ----- | ------ | -------------------------------------------------------------------------------- |
| `alg` | string | Key management algorithm. Current value: `ECDH-ES+A256KW`.                       |
| `kid` | string | Portable recipient identifier derived from the recipient public-key fingerprint. |
| `epk` | object | Ephemeral EC public key used for this recipient's JWE key agreement.             |

`kid` is not a friendly key name. Open Link Token derives it from the public-key
fingerprint and writes it in `sha256:<lowercase-hyphenated-hex>` form.
Friendly names such as `sender-q2` remain local operator-facing names for files in
`~/.openlinktoken/`; they are not the portable identifiers embedded in the artifact.

Example recipient entry:

```json
{
  "encrypted_key": "Base64UrlWrappedKeyHere",
  "header": {
    "alg": "ECDH-ES+A256KW",
    "kid": "sha256:11-22-33-44-55-66-77-88-99-aa-bb-cc-dd-ee-ff-00",
    "epk": {
      "kty": "EC",
      "crv": "P-256",
      "x": "...",
      "y": "..."
    }
  }
}
```

## Encrypted Payload

After decryption, the payload is JSON with these fields:

| Field                     | Type   | Description                                                        |
| ------------------------- | ------ | ------------------------------------------------------------------ |
| `exchangeName`            | string | Logical exchange name recorded in the payload.                     |
| `hashingSecret`           | string | Hashing secret encoded as unpadded base64url text.                 |
| `hashingSecretEncoding`   | string | Encoding marker. Current value: `base64url`.                       |
| `senderKeyFingerprint`    | string | SHA-256 fingerprint of the sender public key.                      |
| `recipientKeyFingerprint` | string | SHA-256 fingerprint of the partner public key.                     |
| `curve`                   | string | Open Link Token curve name for the exchange keys, such as `P-256`. |
| `createdAt`               | string | UTC creation timestamp in ISO 8601 `Z` form.                       |
| `exchangeId`              | string | Random UUID used to identify the exchange artifact.                |

Example decrypted payload:

```json
{
  "exchangeName": "sender-q2",
  "hashingSecret": "R2VuZXJhdGVkU2VjcmV0Qnl0ZXMwMTIzNDU2Nzg5MDE",
  "hashingSecretEncoding": "base64url",
  "senderKeyFingerprint": "AA:BB:CC:DD:EE:FF",
  "recipientKeyFingerprint": "11:22:33:44:55:66",
  "curve": "P-256",
  "createdAt": "2026-03-11T21:00:00Z",
  "exchangeId": "0f3d5f8a-3f2a-4c2f-b69d-cb1f9d08d4ab"
}
```

## Example Serialized Artifact

```json
{
  "version": 1,
  "protected": "eyJ0eXAiOiJvcGVudG9rZW4tZXhjaGFuZ2UrandlIiwiY3R5IjoiYXBwbGljYXRpb24vb3BlbnRva2VuLWV4Y2hhbmdlK2pzb24iLCJlbmMiOiJBMjU2R0NNIn0",
  "iv": "Base64UrlIvHere",
  "ciphertext": "Base64UrlCiphertextHere",
  "tag": "Base64UrlTagHere",
  "recipients": [
    {
      "encrypted_key": "Base64UrlWrappedKeyForSenderHere",
      "header": {
        "alg": "ECDH-ES+A256KW",
        "kid": "sha256:aa-bb-cc-dd-ee-ff",
        "epk": {
          "kty": "EC",
          "crv": "P-256",
          "x": "...",
          "y": "..."
        }
      }
    },
    {
      "encrypted_key": "Base64UrlWrappedKeyForRecipientHere",
      "header": {
        "alg": "ECDH-ES+A256KW",
        "kid": "sha256:11-22-33-44-55-66",
        "epk": {
          "kty": "EC",
          "crv": "P-256",
          "x": "...",
          "y": "..."
        }
      }
    }
  ]
}
```

## Decryption and Validation Notes

- The sender and recipient can both decrypt the artifact because each side appears in
  `recipients`.
- The artifact alone is not enough to recover the hashing secret; the matching private
  key must be available locally.
- A validator or other tool can resolve a private key by the fingerprint-derived
  `kid`, even when operators primarily know the key by a friendly local filename.
- `tools/exchange/print_exchange_envelope.py` prints the raw serialized envelope,
  adds a `protectedDecoded` object for the shared JOSE header, and decrypts the inner
  payload into `decryptedPayload` when a matching private key is available.
- `tools/exchange/validate_exchange_secret.py` decrypts the payload, checks that a
  supplied private key matches one of the recipient `kid` values, or otherwise tries to
  resolve a matching private key from `~/.openlinktoken/`.
