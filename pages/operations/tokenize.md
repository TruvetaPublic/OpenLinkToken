---
layout: default
---

# Tokenize

How to generate tokens using HMAC-SHA256 without AES encryption.

---

## Overview

The `tokenize` subcommand generates deterministic tokens without AES encryption:

```
Token Signature → SHA-256 Hash → HMAC-SHA256(hash, secret) → Base64 Encode
```

Compared to encryption mode:

```
Token Signature → SHA-256 Hash → HMAC-SHA256(hash, secret) → AES-256-GCM Encrypt → Base64 Encode
```

---

## When to Use `tokenize`

The `tokenize` subcommand is primarily used to support **overlap analysis workflows** where you receive **encrypted tokens from an external partner** and want to build an internal dataset that can be joined against those tokens.

**Use `tokenize` when:**

- You are creating an internal tokenized dataset that will be matched against **encrypted tokens received from an external partner** (after decrypting their tokens to their unencrypted equivalent)
- You need faster processing or smaller token size for **internal analytics and overlap reporting**
- Raw data and tokens are already protected at rest within your environment

**Use `package` when:**

- Sharing tokens with external parties (encrypted tokens are the artifact that should be exchanged)
- Defense in depth is required for tokens stored outside your boundary
- Regulatory or contractual requirements mandate encryption of shared artifacts
- Tokens may be stored in less-secure systems or shared across multiple organizations

---

## CLI Usage

Use the `tokenize` subcommand. Only the hashing secret is required (no encryption key).

### Java

```bash
java -jar opentoken-cli/target/opentoken-cli-*.jar tokenize \
  -i ../../resources/sample.csv \
  -t csv \
  -o ../../resources/hashed-output.csv \
  -h "HashingKey"
```

### Python

```bash
python -m opentoken_cli.main tokenize \
  -i ../../../resources/sample.csv \
  -t csv \
  -o ../../../resources/hashed-output.csv \
  -h "HashingKey"
```

### Docker

```bash
docker run --rm -v $(pwd)/resources:/app/resources \
  opentoken:latest tokenize \
  -i /app/resources/sample.csv \
  -t csv \
  -o /app/resources/hashed-output.csv \
  -h "HashingKey"
```

---

## Output Comparison

### Encrypted Tokens (~80-100 characters)

```csv
RecordId,RuleId,Token
ID001,T1,Gn7t1Zj16E5Qy+z9iINtczP6fRDYta6C0XFrQtpjnVQSEZ5pQXAzo02Aa9LS9oNMOog6Ssw9GZE6fvJrX2sQ/cThSkB6m91L
```

### Tokenized (Unencrypted) Tokens (~44-64 characters)

```csv
RecordId,RuleId,Token
ID001,T1,abc123def456ghi789jkl012mno345pqr678stu901vwx234
```

Tokenized (unencrypted) tokens are shorter because they don't include the AES initialization vector (IV) and authentication tag.

---

## Metadata Differences

### Encryption Mode Metadata

```json
{
  "HashingSecretHash": "abc123...",
  "EncryptionSecretHash": "def456..."
}
```

### `tokenize` Metadata

```json
{
  "HashingSecretHash": "abc123..."
}
```

No `EncryptionSecretHash` field is present when using `tokenize`.

---

## Security Trade-offs

| Aspect               | `package`                       | `tokenize`          |
| -------------------- | ------------------------------- | ------------------- |
| **Token length**     | ~80-100 chars                   | ~44-64 chars        |
| **Processing speed** | Slower                          | Faster              |
| **Secret required**  | Hashing secret + encryption key | Hashing secret only |
| **Reversibility**    | Decryptable (to HMAC hash)      | Not decryptable     |
| **External sharing** | Recommended                     | Not recommended     |
| **Defense in depth** | Yes                             | No                  |

### Security Notes

- **Both modes are one-way**: Original attributes cannot be recovered from either token type
- **Same hashing secret = same tokens**: Tokenized output from different runs with the same secret will match
- **Cross-language parity**: Java and Python produce identical tokenized output for the same input

---

## Matching Tokenized Output

Tokenized (unencrypted) tokens can be matched directly without decryption when **both sides are in tokenized form**. In an external-partner workflow, this typically means:

1. Partner generates and shares **encrypted tokens**.
2. You run [Decrypting Tokens](decrypting-tokens.md) to convert the partner's encrypted tokens to their unencrypted equivalent.
3. You generate **tokenized output** for your own dataset using the same hashing secret.
4. You join the two tokenized datasets to measure overlap.

```sql
-- Match records between datasets
SELECT a.RecordId AS RecordA, b.RecordId AS RecordB
FROM tokens_a a
JOIN tokens_b b ON a.Token = b.Token AND a.RuleId = b.RuleId
WHERE a.RuleId = 'T1';
```

For encrypted tokens, either:
1. Decrypt both datasets first, then match
2. Use the same encryption key for both datasets and match encrypted tokens directly

---

## Troubleshooting

### Tokens Don't Match Between Runs

**Cause:** Different hashing secrets.

**Solution:** Verify the same hashing secret is used for both runs:
```bash
# Check metadata for secret hash
cat output.metadata.json | jq '.HashingSecretHash'
```

### Tokens Don't Match Between Java and Python

**Cause:** Attribute normalization differences or encoding issues.

**Solution:**
1. Verify secrets match exactly (including whitespace)
2. Run the interoperability test:
   ```bash
   cd tools/interoperability
   python java_python_interoperability_test.py
   ```
3. Compare normalized attributes (not raw input)

### "Encryption key not provided" Error

**Cause:** Using package mode without an encryption key.

**Solution:** Use the `tokenize` subcommand to skip encryption:
```bash
java -jar opentoken-cli-*.jar tokenize -i data.csv -t csv -o out.csv -h "Key"
```

---

## Next Steps

- **`package` (encrypt) mode**: [Decrypting Tokens](decrypting-tokens.md)
- **Batch processing**: [Running Batch Jobs](running-batch-jobs.md)
- **Security guidance**: [Security](../security.md)
