---
layout: default
---

# Decrypting Tokens

How to decrypt previously encrypted tokens for debugging, verification, or re-encryption.

---

## When to Decrypt

Decryption is useful for:

- **Debugging**: Verifying attribute normalization produced expected token signatures
- **Verification**: Confirming tokens match between datasets
- **Re-encryption**: Decrypting tokens to re-encrypt with a different key
- **Cross-language validation**: Ensuring consistent tokens across implementations

**Note:** Decryption produces HMAC-SHA256 hashed tokens (base64 encoded), **not** the original attribute values. Token generation is one-way.

---

## CLI Decrypt Mode

Use the `decrypt` subcommand with the same exchange config used for token generation. The CLI auto-discovers both the exchange config (from the current directory) and the matching private key (from `~/.openlinktoken/`).

### Open Link Token CLI (Python)

```bash
olt decrypt -i ./resources/output.csv -o ./resources/decrypted.csv
```

If the exchange config or private key cannot be auto-discovered, pass them explicitly with `--exchange-config` and `--private-key`.

### Docker

If the container cannot auto-discover the matching key under `~/.openlinktoken/`, pass it explicitly:

```bash
docker run --rm \
  -e OLT_PRIVATE_KEY_PEM="$(cat ~/.openlinktoken/decrypt.private.pem)" \
  -v $(pwd)/resources:/app/resources \
  openlinktoken:latest decrypt \
  -i /app/resources/output.csv \
  -o /app/resources/decrypted.csv \
  --exchange-config /app/resources/decrypt.exchange.json \
  --private-key-env OLT_PRIVATE_KEY_PEM
```

---

## Decrypted Output Format

Decrypted tokens are HMAC-SHA256 hashes (base64 encoded)—equivalent to `tokenize` output:

```csv
RecordId,RuleId,Token
ID001,T1,abc123def456...  # Base64-encoded HMAC hash
ID001,T2,fed456abc123...  # Same format as tokenize output
...
```

This output can be used to:

- Compare with tokenized output from another run
- Verify token consistency across datasets
- Debug normalization issues

---

## Standalone Decryptor Tool

A Python decryptor tool is available in `tools/decryptor/`:

```bash
cd tools/decryptor
uv pip install pycryptodome

python decryptor.py \
  -e "Secret-Encryption-Key-Goes-Here." \
  -i ./resources/output.csv \
  -o ./resources/decrypted.csv
```

### Requirements

- Python 3.10+
- `pycryptodome` library
- CSV with `RuleId`, `Token`, `RecordId` columns

---

## Cross-Language Decryption

Tokens encrypted by one Open Link Token implementation can be decrypted by another — all implementations use AES-256-GCM with identical parameters. A round trip with the same exchange config:

```bash
# Encrypt with one implementation (CLI shown; the Java or Python API would behave identically)
olt package -i data.csv -o tokens.csv

# Decrypt anywhere that holds the matching private key
olt decrypt -i tokens.csv -o decrypted.csv
```

For an end-to-end Java↔Python verification, run `tools/interoperability/multi_language_interoperability_test.py`.

**Requirements for cross-language compatibility:**

- Same exchange config (or one that resolves to the same hashing secret and transport key)
- A private key matching one of the exchange recipients
- Same token file format on both sides
- Both implementations use the same JWE/AES-256-GCM token format

---

## Security Considerations

### Key Handling

- **Never commit private keys** to version control
- **Use environment variables** or secret stores when you need to override local key auto-discovery:
  ```bash
  export OLT_PRIVATE_KEY_PEM="$(cat ~/.openlinktoken/interop.private.pem)"
  olt decrypt --exchange-config ./interop.exchange.json --private-key-env OLT_PRIVATE_KEY_PEM ...
  ```
- **Rotate keys periodically** and issue a fresh exchange config as needed

### Access Control

- **Limit decryption access**: Only authorized personnel should have the matching private key
- **Audit decryption events**: Log when and why tokens are decrypted
- **Secure decrypted output**: Decrypted tokens are still sensitive (HMAC hashes)

### What Decryption Does NOT Reveal

Decryption produces HMAC hashes, **not** original data:

```
Original: John Doe, 1980-01-15, Male
    ↓
Token Signature: DOE|JOHN|MALE|1980-01-15
    ↓
SHA-256 Hash: abc123...
    ↓
HMAC-SHA256: def456...  ← Decryption reveals this
    ↓
AES-256-GCM: xyz789...  ← Encrypted token
```

You **cannot** reverse the original attribute values from decrypted tokens.

---

## Troubleshooting

| Problem                             | Solution                                                                                    |
| ----------------------------------- | ------------------------------------------------------------------------------------------- |
| "Decryption error"                  | Verify encryption key matches the key used for encryption                                   |
| Key length error                    | Encryption key must be exactly 32 characters                                                |
| Blank tokens in output              | Blank tokens in input (from invalid records) remain blank                                   |
| Tokens don't match across languages | Run interoperability test: `tools/interoperability/multi_language_interoperability_test.py` |

---

## Next Steps

- **Tokenize**: [Tokenize](tokenize.md) (no encryption needed)
- **Batch processing**: [Running Batch Jobs](running-batch-jobs.md)
- **Security guidance**: [Security](../security.md)
