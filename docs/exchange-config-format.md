# OpenToken Exchange Config Format

## Overview

The exchange config is a JSON bundle produced by `opentoken initiate-exchange`.

Its purpose is to carry the encrypted hashing secret plus the key material needed
to recover that secret on another system. In the current format, the bundle is
self-contained by default and is therefore a **secret-bearing artifact**.

## Top-Level Structure

The file is JSON with these top-level fields:

| Field                    | Type    | Description                                                                               |
| ------------------------ | ------- | ----------------------------------------------------------------------------------------- |
| `version`                | integer | Format version for the exchange bundle.                                                   |
| `exchangeName`           | string  | Logical name of the exchange, usually matching the local key basename.                    |
| `keyAgreement`           | string  | Key agreement mechanism used to derive the wrapping key. Currently `ECDH`.                |
| `curve`                  | string  | Elliptic curve used by the local key pair. Currently one of `P-256`, `P-384`, or `P-521`. |
| `localKey`               | object  | Nested local key material for the bundle. See below.                                      |
| `partnerKey`             | object  | Nested partner key material for the bundle. See below.                                    |
| `kdf`                    | object  | Parameters used to derive the AES key from the ECDH shared secret.                        |
| `encryption`             | object  | Parameters used to encrypt the hashing secret.                                            |
| `encryptedHashingSecret` | string  | Base64-encoded AES-GCM ciphertext for the hashing secret.                                 |

## `localKey`

The `localKey` object keeps the local public and private key material together.

| Field                   | Type   | Description                                                                             |
| ----------------------- | ------ | --------------------------------------------------------------------------------------- |
| `basename`              | string | Base name used for the local key files under `~/.opentoken/`.                           |
| `publicKey`             | string | PEM-encoded public key corresponding to `privateKey`.                                   |
| `publicKeyFingerprint`  | string | SHA-256 fingerprint of `publicKey` in colon-separated uppercase hex.                    |
| `privateKey`            | string | PEM-encoded local private key used for ECDH and embedded for self-contained bundle use. |
| `privateKeyFingerprint` | string | SHA-256 fingerprint of the embedded private key's corresponding public key.             |

## `partnerKey`

The `partnerKey` object keeps the partner public key together with its fingerprint.

| Field                  | Type   | Description                                                          |
| ---------------------- | ------ | -------------------------------------------------------------------- |
| `publicKey`            | string | PEM-encoded public key supplied for the exchange partner.            |
| `publicKeyFingerprint` | string | SHA-256 fingerprint of `publicKey` in colon-separated uppercase hex. |

## `kdf`

| Field       | Type   | Description                                           |
| ----------- | ------ | ----------------------------------------------------- |
| `algorithm` | string | Key derivation function. Currently `HKDF`.            |
| `hash`      | string | Digest used by HKDF. Currently `SHA-256`.             |
| `info`      | string | HKDF `info` value. Currently `opentoken-exchange-v1`. |

## `encryption`

| Field           | Type    | Description                                          |
| --------------- | ------- | ---------------------------------------------------- |
| `algorithm`     | string  | Symmetric encryption algorithm. Currently `AES-GCM`. |
| `keyLength`     | integer | AES key length in bits. Currently `256`.             |
| `nonceEncoding` | string  | Encoding used for the nonce. Currently `base64`.     |
| `nonce`         | string  | Base64-encoded AES-GCM nonce.                        |

## Example

```json
{
  "version": 1,
  "exchangeName": "sender-q2",
  "keyAgreement": "ECDH",
  "curve": "P-256",
  "localKey": {
    "basename": "sender-q2",
    "publicKey": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n",
    "publicKeyFingerprint": "AA:BB:CC:DD:EE:FF",
    "privateKey": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
    "privateKeyFingerprint": "AA:BB:CC:DD:EE:FF"
  },
  "partnerKey": {
    "publicKey": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n",
    "publicKeyFingerprint": "11:22:33:44:55:66"
  },
  "kdf": {
    "algorithm": "HKDF",
    "hash": "SHA-256",
    "info": "opentoken-exchange-v1"
  },
  "encryption": {
    "algorithm": "AES-GCM",
    "keyLength": 256,
    "nonceEncoding": "base64",
    "nonce": "Base64NonceHere"
  },
  "encryptedHashingSecret": "Base64CiphertextHere"
}
```

## Security Notes

- This file now contains `localKey.privateKey`, so possession of the file is
  sufficient to recover the hashing secret.
- Treat the exchange config like any other secret-bearing credential bundle.
- If you need to control which private key is embedded, use
  `opentoken initiate-exchange --local-private-key <path>`.

## Compatibility Notes

- Older exchange bundles may store legacy snake_case field names and older
  top-level local key fields instead of the current camelCase names.
- `tools/validate_exchange_secret.py` remains backward-compatible with those
  earlier bundles.
