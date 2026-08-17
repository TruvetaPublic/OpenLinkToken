# Exchange configuration format

`olt initiate-exchange` writes a version `1` JSON artifact. The Python CLI
currently creates and consumes this format. It contains one encrypted payload
and one JWE recipient entry for each party:

- the sender's key
- the partner's public key

The artifact contains no private key material.

## Envelope

| Field        | Type    | Description                             |
| ------------ | ------- | --------------------------------------- |
| `version`    | integer | Current format version: `1`             |
| `protected`  | string  | Base64url-encoded shared JOSE header    |
| `iv`         | string  | Base64url AES-GCM initialization vector |
| `ciphertext` | string  | Base64url encrypted payload             |
| `tag`        | string  | Base64url AES-GCM authentication tag    |
| `recipients` | array   | Per-party wrapped-key entries           |

The decoded protected header is:

```json
{
  "typ": "openlinktoken-exchange+jwe",
  "cty": "application/openlinktoken-exchange+json",
  "enc": "A256GCM"
}
```

Each recipient has an `encrypted_key` and a `header`:

```json
{
  "encrypted_key": "Base64UrlWrappedKey",
  "header": {
    "alg": "ECDH-ES+A256KW",
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

`kid` is derived from the public-key SHA-256 fingerprint in
`sha256:<lowercase-hyphenated-hex>` form. A local friendly key name such as
`sender-q2` is not stored in the artifact.

## Decrypted payload

| Field                     | Type    | Description                                   |
| ------------------------- | ------- | --------------------------------------------- |
| `exchangeName`            | string  | Logical exchange name                         |
| `hashingSecret`           | string  | Unpadded base64url-encoded hashing secret     |
| `hashingSecretEncoding`   | string  | `base64url`                                   |
| `senderKeyFingerprint`    | string  | SHA-256 fingerprint of the sender public key  |
| `recipientKeyFingerprint` | string  | SHA-256 fingerprint of the partner public key |
| `senderPublicKey`         | string  | Sender public key PEM                         |
| `recipientPublicKey`      | string  | Partner public key PEM                        |
| `curve`                   | string  | Exchange key curve, such as `P-256`           |
| `createdAt`               | string  | UTC timestamp in ISO 8601 `Z` form            |
| `exchangeId`              | string  | Random UUID for the exchange                  |
| `rotationIv`              | string  | Unpadded base64url rotation IV                |
| `rotationIvEncoding`      | string  | `base64url`                                   |
| `rotationCount`           | integer | Rotation count; CLI default is `50`           |
| `binWidth`                | number  | Quantization bin width; CLI default is `0.05` |
| `dimensionBias`           | array   | Bias vector; CLI default is 1,024 zero values |

The hashing secret and rotation IV are generated randomly when the caller does
not provide them. Use the CLI's stdin or environment-variable options to avoid
putting secret values in shell history.

Example:

```json
{
  "exchangeName": "sender-q2",
  "hashingSecret": "R2VuZXJhdGVkU2VjcmV0",
  "hashingSecretEncoding": "base64url",
  "senderKeyFingerprint": "AA:BB:CC:DD",
  "recipientKeyFingerprint": "11:22:33:44",
  "senderPublicKey": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n",
  "recipientPublicKey": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n",
  "curve": "P-256",
  "createdAt": "2026-03-11T21:00:00Z",
  "exchangeId": "0f3d5f8a-3f2a-4c2f-b69d-cb1f9d08d4ab",
  "rotationIv": "Um90YXRpb25JVg",
  "rotationIvEncoding": "base64url",
  "rotationCount": 50,
  "binWidth": 0.05,
  "dimensionBias": [0.0, 0.0]
}
```

The example bias is shortened. A real default payload contains 1,024 entries,
or the length of the supplied `--rotation-embedding-bias` array.

## Key resolution and inspection

Both parties can decrypt the artifact with the matching private key. The CLI
can receive that key through `--private-key`, `--private-key-env`, or the local
`~/.openlinktoken/` key directory, where it resolves `kid` from the public-key
fingerprint.

Useful inspection tools:

- `tools/exchange/print_exchange_envelope.py` prints the envelope, decoded
  protected header, and decrypted payload when a matching key is available.
- `tools/exchange/validate_exchange_secret.py` validates the recipient key and
  reads the decrypted hashing secret.
