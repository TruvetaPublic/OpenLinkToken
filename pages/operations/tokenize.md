---
layout: default
---

# Tokenize

How to generate tokens without AES encryption, including default `tokenize`, `tokenize --mode hash-only`, and `tokenize --mode demo`.

---

## Overview

The `tokenize` subcommand supports three modes:

**Normal mode** (default) — applies SHA-256 and HMAC-SHA256 to produce opaque, secret-keyed tokens:

```text
Token Signature → SHA-256 Hash → HMAC-SHA256(hash, secret) → Base64 Encode
```

**Hash-only mode** (`--mode hash-only`) — applies SHA-256 only and emits deterministic 64-character lowercase hex strings:

```text
Token Signature → SHA-256 Hash → Lowercase Hex Encode
```

**Demo mode** (`--mode demo`) — skips all hashing and outputs the raw pipe-separated attribute signature string:

```text
Token Signature → (passthrough) → Raw attribute signature string
```

For reference, the full encryption pipeline used by `package` is:

```text
Token Signature → SHA-256 Hash → HMAC-SHA256(hash, secret) → AES-256-GCM Encrypt → Base64 Encode
```

---

## When to Use `tokenize`

The `tokenize` subcommand is primarily used to support **overlap analysis workflows** where you receive **encrypted tokens from an external partner** and want to build an internal dataset that can be joined against those tokens.

**Use `tokenize` (normal mode) when:**

- You are creating an internal tokenized dataset that will be matched against **encrypted tokens received from an external partner** (after decrypting their tokens to their unencrypted equivalent)
- You need faster processing or smaller token size for **internal analytics and overlap reporting**
- Raw data and tokens are already protected at rest within your environment

**Use `tokenize --mode demo` when:**

- Exploring which attributes contribute to each token rule without managing secrets
- Writing documentation or conducting interactive demonstrations
- Debugging attribute normalisation or token rule logic

> ⚠️ Demo mode output is **not** suitable for production or cross-organisation exchange. See [Demo Mode](#demo-mode---mode-demo) below.

**Use `tokenize --mode hash-only` when:**

- You need deterministic SHA-256 output for local experiments, tests, or demonstrations
- You want to inspect or compare token generation behavior without creating an exchange config first
- You explicitly do **not** want keyed HMAC output

> ⚠️ Hash-only output is deterministic SHA-256 without HMAC. It is **not** suitable for production or cross-organisation exchange.

**Use `package` when:**

- Sharing tokens with external parties (encrypted tokens are the artifact that should be exchanged)
- Defense in depth is required for tokens stored outside your boundary
- Regulatory or contractual requirements mandate encryption of shared artifacts
- Tokens may be stored in less-secure systems or shared across multiple organizations

---

## CLI Usage

### Normal Mode

Use the `tokenize` subcommand with an exchange config. The CLI resolves the hashing secret from the exchange config and auto-discovers the matching private key by default.

```bash
olt tokenize \
  -i resources/sample.csv \
  -o resources/hashed-output.csv \
  --exchange-config ./tokenize.exchange.json
```

#### Normal Mode — Docker Override Example

If the container cannot auto-discover the matching key under `~/.openlinktoken/`, pass it explicitly:

```bash
docker run --rm \
  -e OLT_PRIVATE_KEY_PEM="$(cat ~/.openlinktoken/tokenize.private.pem)" \
  -v $(pwd)/resources:/app/resources \
  openlinktoken:latest tokenize \
  -i /app/resources/sample.csv \
  -o /app/resources/hashed-output.csv \
  --exchange-config /app/resources/tokenize.exchange.json \
  --private-key-env OLT_PRIVATE_KEY_PEM
```

### Hash-only Mode (`--mode hash-only`)

In hash-only mode the CLI skips exchange-config resolution and applies SHA-256 only. `--exchange-config`, `--private-key`, and `--private-key-env` are not allowed in this mode.

```bash
olt tokenize \
  -i resources/sample.csv \
  -o resources/hash-only-output.csv \
  --mode hash-only
```

#### Hash-only Mode — Docker

```bash
docker run --rm -v $(pwd)/resources:/app/resources \
  openlinktoken:latest tokenize \
  -i /app/resources/sample.csv \
  -o /app/resources/hash-only-output.csv \
  --mode hash-only
```

Hash-only tokens are deterministic 64-character lowercase hex digests. Because no secret is used, the output is easier to reproduce locally but provides less protection than normal `tokenize` mode.

### Hashing Record IDs (`--hash-record-ids`)

Add `--hash-record-ids` to replace each input `RecordId` with its SHA-256 hex digest in the output. This is a **one-way, irreversible operation** — the original `RecordId` is not stored or recoverable from the output. Use this when the input dataset contains raw identifiers that should not appear in any output file.

The `--hash-record-ids` flag is also supported by the `package` subcommand.

```bash
olt tokenize \
  -i resources/sample.csv \
  -o resources/hashed-output.csv \
  --exchange-config ./tokenize.exchange.json \
  --hash-record-ids
```

**Output (`hashed-output.csv`) with `--hash-record-ids`:**

```csv
RecordId,RuleId,Token
390671c4d060d84284c167d382e5b7f5f61b424ae833ae11f9d6d5667b2fe223,T1,abc123def456...
390671c4d060d84284c167d382e5b7f5f61b424ae833ae11f9d6d5667b2fe223,T2,def456ghi789...
```

Each `RecordId` is replaced with a 64-character lowercase SHA-256 hex digest. The original `RecordId` does not appear anywhere in the output.

### Demo Mode (`--mode demo`)

In demo mode the full hashing pipeline is skipped. No exchange config or private key is required.

```bash
olt tokenize \
  -i resources/sample.csv \
  -o resources/demo-output.csv \
  --mode demo
```

#### Demo Mode — Docker

```bash
docker run --rm -v $(pwd)/resources:/app/resources \
  openlinktoken:latest tokenize \
  -i /app/resources/sample.csv \
  -o /app/resources/demo-output.csv \
  --mode demo
```

#### Demo Output Example

For a record with first name `John`, last name `Doe`, and birth date `1980-01-15`:

```csv
RecordId,RuleId,Token
ID001,T1,JOHN|DOE|19800115
ID001,T2,JOHN|DOE|19800115|M
ID001,T5,123456789
```

Each token is the raw pipe-separated list of normalised attribute values that compose that token rule — making it easy to see exactly which attributes contributed to each rule.

---

## Output Comparison

### Encrypted Tokens (~80-100 characters)

```csv
RecordId,RuleId,Token
ID001,T1,Gn7t1Zj16E5Qy+z9iINtczP6fRDYta6C0XFrQtpjnVQSEZ5pQXAzo02Aa9LS9oNMOog6Ssw9GZE6fvJrX2sQ/cThSkB6m91L
```

### Tokenized (Unencrypted) Tokens (~44 characters)

```csv
RecordId,RuleId,Token
ID001,T1,abc123def456ghi789jkl012mno345pqr678stu901vwx234
```

Normal `tokenize` output is a base64-encoded HMAC value, typically about 44 characters because it omits the AES initialization vector (IV) and authentication tag.

### Hash-only Tokens (64 hexadecimal characters)

```csv
RecordId,RuleId,Token
ID001,T1,8d0f7f0d30f4b9e2e31e9d7fdc7f1c7f0d0fb6b246bd27d4f91f4fbad0b8e2c4
```

`tokenize --mode hash-only` output is always a 64-character lowercase SHA-256 hex digest.

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

### `tokenize --mode hash-only` Metadata

```json
{
  "TotalRows": 10
}
```

Neither `HashingSecretHash` nor `EncryptionSecretHash` appears in hash-only metadata because no secret is used.

### `tokenize --mode demo` Metadata

```json
{
  "TotalRows": 10
}
```

Neither `HashingSecretHash` nor `EncryptionSecretHash` appears in demo-mode metadata — no secret is used.

---

## Security Trade-offs

| Aspect                  | `package`                     | `tokenize`                    | `tokenize --mode hash-only`        | `tokenize --mode demo`         |
| ----------------------- | ----------------------------- | ----------------------------- | ---------------------------------- | ------------------------------ |
| **Token length**        | ~80-100 chars                 | ~44 chars (base64)            | 64 chars (lowercase hex)           | Varies (plain text)            |
| **Processing speed**    | Slower                        | Faster                        | Fastest keyed-free hashed mode     | Fastest overall                |
| **CLI inputs required** | Exchange config + private key | Exchange config + private key | None                               | None                           |
| **Reversibility**       | Decryptable (to HMAC hash)    | Not decryptable               | Not decryptable                    | Directly readable (plain text) |
| **External sharing**    | Recommended                   | Not recommended               | Never recommended                  | Never — contains raw PII       |
| **Defense in depth**    | Yes                           | No                            | No                                 | No                             |
| **Use case**            | Production / sharing          | Internal analysis             | Local deterministic SHA-256 output | Exploration / debugging only   |

### Security Notes

- **All hashed modes are one-way**: Original attributes cannot be recovered from normal `tokenize`, `tokenize --mode hash-only`, or encrypted token output
- **Same hashing secret = same tokens**: Normal `tokenize` output from different runs with the same secret will match
- **Hash-only is keyless**: `tokenize --mode hash-only` always produces the same SHA-256 hex output for the same normalized signature, but lacks the protection of keyed HMAC

---

## Matching Tokenized Output

Tokenized (unencrypted) tokens can be matched directly without decryption when **both sides are in tokenized form**. In an external-partner workflow, this typically means:

1. Partner generates and shares **encrypted tokens**.
2. You run [Decrypting Tokens](decrypting-tokens.md) to convert the partner's encrypted tokens to their unencrypted equivalent.
3. You generate **tokenized output** for your own dataset using the same exchange config.
4. You join the two tokenized datasets to measure overlap.

```sql
-- Match records between datasets
SELECT a.RecordId AS RecordA, b.RecordId AS RecordB
FROM tokens_a a
JOIN tokens_b b ON a.Token = b.Token AND a.RuleId = b.RuleId
WHERE a.RuleId = 'T1';
```

For encrypted tokens, decrypt them to their hashed form first and then match on `RuleId` plus `Token`.

---

## Troubleshooting

### Tokens Don't Match Between Runs

**Cause:** Different exchange configs resolved different hashing secrets.

**Solution:** Verify both runs produced the same secret hashes in metadata:

```bash
# Check metadata for secret hash
cat output.metadata.json | jq '.HashingSecretHash'
```

### "No private key matching this exchange config was found" Error

**Cause:** The CLI found the exchange config but could not auto-discover a matching private key.

**Solution:** Provide the correct key explicitly:

```bash
olt tokenize \
  -i data.csv \
  -o out.csv \
  --exchange-config ./tokenize.exchange.json
```

---

## Next Steps

- **`package` (encrypt) mode**: [Decrypting Tokens](decrypting-tokens.md)
- **Batch processing**: [Running Batch Jobs](running-batch-jobs.md)
- **Security guidance**: [Security](../security.md)
- **Full flag reference**: [CLI Reference — tokenize](../reference/cli.md#tokenize)
