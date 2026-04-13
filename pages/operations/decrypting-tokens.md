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

Use the `decrypt` subcommand with the same encryption key used for token generation.

### OpenLinkToken CLI (Python)

```bash
olt decrypt \
  -i ../../resources/output.csv \
  -t csv \
  -o ../../resources/decrypted.csv \
  -e "Secret-Encryption-Key-Goes-Here."
```

### Docker

```bash
docker run --rm -v $(pwd)/resources:/app/resources \
  openlinktoken:latest decrypt \
  -i /app/resources/output.csv \
  -t csv \
  -o /app/resources/decrypted.csv \
  -e "Secret-Encryption-Key-Goes-Here."
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
  -i ../../resources/output.csv \
  -o ../../resources/decrypted.csv
```

### Requirements

- Python 3.10+
- `pycryptodome` library
- CSV with `RuleId`, `Token`, `RecordId` columns

---

## Cross-Language Decryption

Tokens can be encrypted by one OpenLinkToken implementation and decrypted by another—all implementations use AES-256-GCM with identical parameters:

```bash
# Encrypt with OpenLinkToken CLI
olt package \
  -i data.csv -t csv -o tokens.csv \
  -h "HashingKey" -e "EncryptionKey32Characters!!!!!"

# Decrypt with OpenLinkToken CLI
olt decrypt \
  -i tokens.csv -t csv -o decrypted.csv \
  -e "EncryptionKey32Characters!!!!!"
```

**Requirements for cross-language compatibility:**

- Same encryption key (exactly 32 characters/bytes)
- Same token file format
- Both implementations use AES-256-GCM with identical parameters

---

## Security Considerations

### Key Handling

- **Never commit encryption keys** to version control
- **Use environment variables** or secret stores:
  ```bash
  export OPENTOKEN_ENCRYPTION_KEY="YourKey32Characters!!!!!!!!!!!!"
  olt decrypt -e "$OPENTOKEN_ENCRYPTION_KEY" ...
  ```
- **Rotate keys periodically** and re-encrypt tokens as needed

### Access Control

- **Limit decryption access**: Only authorized personnel should have encryption keys
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
