---
layout: default
---

# Sharing Tokenized Data Between Organizations

How to securely exchange Open Link Token outputs for cross-organization record linkage.

---

## Overview

Organizations often need to identify overlapping individuals across datasets without exposing raw person data. Open Link Token enables this by generating deterministic, cryptographically secure tokens that can be shared and matched externally.

**Typical scenario:**

1. Organization A and Organization B each hold patient records
2. Both organizations run Open Link Token on their data using **the same secrets**
3. They exchange only the token output (no raw PII)
4. Matching tokens indicate the same person exists in both datasets

```text
┌─────────────────┐                    ┌─────────────────┐
│  Organization A │                    │  Organization B │
│  (Patient Data) │                    │  (Patient Data) │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         ▼                                      ▼
┌─────────────────┐                    ┌─────────────────┐
│ Open Link Token │                    │ Open Link Token │
│ (same secrets)  │                    │ (same secrets)  │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         ▼                                      ▼
┌─────────────────┐     Exchange       ┌─────────────────┐
│  Tokens + Meta  │ ←───────────────→  │  Tokens + Meta  │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         └───────────────┬──────────────────────┘
                         ▼
               ┌─────────────────┐
               │  Token Matching │
               │  (find overlap) │
               └─────────────────┘
```

---

## ECDH Bootstrap Workflow (Recommended)

The two-command ECDH bootstrap workflow lets partners establish a shared hashing secret without transmitting it in plaintext. Only the JSON exchange config — containing the **encrypted** secret — needs to leave the sender's environment.

For this workflow:

- `sender` means the party that runs `olt initiate-exchange` and creates the exchange artifact
- `recipient` means the counterparty whose public key is supplied to `initiate-exchange` and who later decrypts with the matching private key

### Overview

```text
Recipient                                   Sender
─────────────────────────────────────────────────────
generate-key-pair                                │
  → recipient.public.pem ──────────────────────► │
                                                 │
                                         initiate-exchange
                                           --public-key recipient.public.pem
                                           → sender.exchange.json
                                           → sender.private.pem (local only)
                                                 │
                        ◄────────────────────────┤ sender.exchange.json
                                                 │ (contains encrypted secret)
Recover hashing secret
from sender's local public key
+ own private key (ECDH)
```

### Step 1 — Recipient generates a key pair

```bash
olt generate-key-pair --name recipient-org
```

This writes:

- `~/.openlinktoken/recipient-org.private.pem` — keep this secret, never share it
- `~/.openlinktoken/recipient-org.public.pem` — share this with the sender

### Step 2 — Sender initiates the exchange

```bash
olt initiate-exchange \
  --name sender-q2 \
  --public-key ./recipient-org.public.pem \
  --output ./sender-q2.exchange.json
```

To provide the same partner public key via stdin instead of `--public-key`:

```bash
cat ./recipient-org.public.pem | \
  olt initiate-exchange \
    --name sender-q2 \
    --public-key-stdin \
    --output ./sender-q2.exchange.json
```

To provide both the recipient public key and the sender private key by
reference in one command, use environment variables:

```bash
OLT_RECIPIENT_PUBLIC_KEY="$(az keyvault secret show --vault-name my-vault --name recipient-public-key --query value -o tsv)" \
OLT_SENDER_PRIVATE_KEY="$(az keyvault secret show --vault-name my-vault --name sender-private-key --query value -o tsv)" \
olt initiate-exchange \
  --name sender-q2 \
  --public-key-env OLT_RECIPIENT_PUBLIC_KEY \
  --sender-private-key-env OLT_SENDER_PRIVATE_KEY \
  --output ./sender-q2.exchange.json
```

This:

1. Generates a local ECDH key pair for the sender under `~/.openlinktoken/`, reuses one supplied with `--sender-private-key`, or derives one from `--sender-private-key-env`.
2. Generates a secure random hashing secret by default, or accepts an existing one via `--hashingsecret-env`, `--hashingsecret-stdin`, or `--hashingsecret`.
3. Encrypts the hashing secret into a multi-recipient JWE JSON envelope.
4. Adds one JWE recipient entry for the sender's public key and one for the recipient's public key.
5. Writes `sender-q2.exchange.json` without embedding any private key material.

This means the same exchange artifact can be decrypted by either side with its own private key, but the JSON alone is not enough to recover the hashing secret.

When `--sender-private-key-env` is used, Open Link Token derives the sender public key
from the referenced private key in memory and skips writing sender key files to
`~/.openlinktoken/`.

If you want to keep using an existing sender private key instead of generating a new one, use `--sender-private-key`:

```bash
olt initiate-exchange \
  --name sender-q2 \
  --public-key ./recipient-org.public.pem \
  --sender-private-key ~/.openlinktoken/sender-q2.private.pem \
  --output ./sender-q2.exchange.json
```

If you need to supply a pre-existing hashing secret, prefer an environment-variable or stdin-based input so the secret does not appear in shell history or process listings:

```bash
export OLT_HASHING_SECRET="$(az keyvault secret show --vault-name my-vault --name hashing-secret --query value -o tsv)"

olt initiate-exchange \
  --name sender-q2 \
  --public-key ./recipient-org.public.pem \
  --hashingsecret-env OLT_HASHING_SECRET \
  --output ./sender-q2.exchange.json
```

### Step 3 — Sender transfers the exchange config

Transfer `sender-q2.exchange.json` to the recipient over any channel. The hashing secret inside is encrypted, and the file can be decrypted by the sender or recipient only if the matching private key is available locally. For a field-by-field format reference, see `docs/exchange-config-format.md`.

### Step 4 — Sender or recipient recovers the hashing secret

Either side can decrypt the same exchange artifact with its own private key. If a matching key already exists under `~/.openlinktoken/`, the validator can resolve it automatically:

```bash
python tools/exchange/validate_exchange_secret.py \
  --exchange-config sender-q2.exchange.json
```

You can also point at a specific private key file with `--private-key`. For example, the recipient can validate with its private key:

```bash
python tools/exchange/validate_exchange_secret.py \
  --exchange-config sender-q2.exchange.json \
  --private-key ~/.openlinktoken/recipient-org.private.pem
```

The sender can do the same with the sender private key:

```bash
python tools/exchange/validate_exchange_secret.py \
  --exchange-config sender-q2.exchange.json \
  --private-key ~/.openlinktoken/sender-q2.private.pem
```

To provide the same private key via stdin instead of `--private-key`, pipe the PEM into `--private-key-stdin`:

```bash
cat ~/.openlinktoken/recipient-org.private.pem | \
  python tools/exchange/validate_exchange_secret.py \
    --exchange-config sender-q2.exchange.json \
    --private-key-stdin
```

If the sender provided a known plaintext via `olt initiate-exchange --hashingsecret-env ...`, `--hashingsecret-stdin`, or `--hashingsecret ...`, the recipient can also perform an explicit pass/fail check:

```bash
python tools/exchange/validate_exchange_secret.py \
  --exchange-config sender-q2.exchange.json \
  --private-key ~/.openlinktoken/recipient-org.private.pem \
  --expected-secret "$HASHING_SECRET"
```

Successful AES-GCM decryption proves the available key material matches one of the JWE recipient entries in the exchange config. If decryption fails, the key material does not correspond to that exchange.

### Step 5 — Both parties tokenize using the exchange config

Once both parties have the exchange artifact and the matching private key, they run the consumer commands directly against the exchange config:

```bash
olt package \
  -i patient_data.csv \
  -o tokens_for_partner.csv \
  --exchange-config sender-q2.exchange.json \
  --private-key ~/.openlinktoken/sender-q2.private.pem
```

---

## Sender Workflow (manual secret agreement)

The sending organization prepares tokenized data for sharing.

### Step 1: Agree on Shared Secrets

Before tokenization, both parties must agree on:

- **Hashing secret** (required): Used for HMAC-SHA256
- **Encryption key** (recommended for external sharing): Used for AES-256-GCM

**Best practice:** Use a secure channel (encrypted email, secure file transfer, or direct key exchange in person) to share secrets. Never send secrets alongside token files.

### Step 2: Run Open Link Token

Generate tokens using the agreed-upon secrets.

**Encrypted mode (recommended for external sharing):**

```bash
olt package \
  -i patient_data.csv \
  -o tokens_for_partner.csv \
  -h "$SHARED_HASHING_SECRET" \
  -e "$SHARED_ENCRYPTION_KEY"
```

**Tokenize (overlap analysis helper, internal artifact):**

Tokenized (unencrypted) output is primarily used **inside your environment** to support overlap analysis against encrypted tokens received from a partner:

```bash
olt tokenize \
  -i local_patient_data.csv \
  -o local_hash_only_tokens.csv \
  -h "$SHARED_HASHING_SECRET"
```

Typical pattern:

1. Both parties exchange **encrypted tokens** only.
2. You decrypt the partner's encrypted tokens (see [Decrypting Tokens](decrypting-tokens.md)).
3. You run `tokenize` for your own dataset to produce unencrypted tokens.
4. You perform overlap analysis by joining the two tokenized datasets.

See [Tokenize](tokenize.md) for trade-offs between encrypted and tokenized output.

### Step 3: Review Metadata

Check the generated `.metadata.json` for processing statistics:

```json
{
  "TotalRows": 50000,
  "TotalRowsWithInvalidAttributes": 120,
  "InvalidAttributesByType": {
    "SocialSecurityNumber": 80,
    "BirthDate": 40
  },
  "BlankTokensByRule": {
    "T1": 80,
    "T3": 80
  },
  "HashingSecretHash": "e0b4e60b...",
  "EncryptionSecretHash": "a1b2c3d4..."
}
```

**Key checks:**

- `TotalRowsWithInvalidAttributes`: High counts may indicate data quality issues
- `BlankTokensByRule`: T1 and T3 require SSN; blanks are expected if SSN is often missing
- `HashingSecretHash` / `EncryptionSecretHash`: Share these hashes (not the secrets) so the recipient can verify they used the correct keys

### Step 4: Prepare Transfer Package

Include in the transfer:

| File                         | Purpose                              | Contains Secrets?         |
| ---------------------------- | ------------------------------------ | ------------------------- |
| `tokens.csv` (or `.parquet`) | Token output                         | No                        |
| `tokens.metadata.json`       | Processing stats, secret hashes      | Hashes only (not secrets) |
| Data dictionary (optional)   | Column definitions, RecordId mapping | No                        |

**Do NOT include:**

- Raw input data (PII)
- Hashing secret or encryption key (share separately via secure channel)
- Decrypted tokens

### Step 5: Transfer Securely

Use encrypted file transfer:

- SFTP with encryption
- Cloud storage with encryption at rest (S3, Azure Blob, GCS)
- Secure email with encrypted attachment

---

## Recipient Workflow

The receiving organization ingests shared tokens and matches against their own data.

### Step 1: Obtain Shared Secrets

Receive the hashing secret (and encryption key, if applicable) through a secure channel separate from the token files.

### Step 2: Verify Secret Hashes

Before processing, verify that your secrets match the sender's:

```bash
python tools/hash_calculator.py \
  --hashing-secret "$SHARED_HASHING_SECRET" \
  --encryption-key "$SHARED_ENCRYPTION_KEY"
```

Compare the output hashes with `HashingSecretHash` and `EncryptionSecretHash` in the received metadata file. If they don't match, tokens will not match correctly.

### Step 3: Generate Your Own Tokens

Run Open Link Token on your local data using the **same secrets**:

```bash
olt package \
  -i local_patient_data.csv \
  -o local_tokens.csv \
  -h "$SHARED_HASHING_SECRET" \
  -e "$SHARED_ENCRYPTION_KEY"
```

### Step 4: Match Tokens

Join token files to find matching records:

```sql
-- Find overlapping patients
SELECT
    partner.RecordId AS PartnerRecordId,
    local.RecordId AS LocalRecordId,
    partner.RuleId
FROM partner_tokens partner
JOIN local_tokens local
    ON partner.Token = local.Token
    AND partner.RuleId = local.RuleId;
```

**Interpretation:**

- **T4 match**: Very high confidence (SSN + Sex + BirthDate)
- **T3 match**: High confidence (Last name + full first name + Sex + BirthDate)
- **Multiple rule matches**: Stronger confidence (more agreement across attributes)

See [Matching Model](../concepts/matching-model.md) for matching strategies.

### Step 5: Handle Encrypted Tokens (If Applicable)

If tokens are encrypted and you need to debug or verify:

```bash
olt decrypt \
  -i partner_tokens.csv \
  -o partner_decrypted.csv \
  -e "$SHARED_ENCRYPTION_KEY"
```

See [Decrypting Tokens](decrypting-tokens.md) for details.

---

## Security Considerations

### Use Encrypted Tokens for External Sharing

Encrypted mode (`-e` flag) adds AES-256-GCM encryption on top of HMAC-SHA256:

| Mode      | External Sharing    | Defense in Depth | Reversible              |
| --------- | ------------------- | ---------------- | ----------------------- |
| Encrypted | ✓ Recommended       | Yes              | To HMAC hash (with key) |
| Tokenize  | ⚠ Use with caution | No               | Not reversible          |

Encrypted tokens provide an additional security layer if token files are intercepted.

### Protect Shared Secrets

- **Never send secrets with token files.** Use a separate secure channel.
- **Store secrets in a vault** (AWS Secrets Manager, HashiCorp Vault, Azure Key Vault)
- **Limit access** to secrets to authorized personnel only
- **Rotate secrets periodically** and re-tokenize as needed

### Verify Partner Identity

Before sharing:

- Confirm the partner organization's identity through established business relationships
- Use signed data-sharing agreements
- Verify contact information through independent channels

### Audit and Logging

- **Log token generation events**: Who ran Open Link Token, when, with which input file
- **Log token transfers**: When tokens were sent/received, to/from whom
- **Log matching events**: Who performed matching, what results were produced

### Minimize Data Exposure

- **Share only tokens**: Never share raw input data alongside tokens
- **Limit token rules if appropriate**: If only T2 matching is needed, consider generating only T2 tokens
- **Use RecordId mappings**: Map internal IDs to opaque identifiers before sharing

### What Tokens Do NOT Reveal

Tokens are one-way transformations. Without the hashing secret:

- Attackers cannot reverse tokens to original attributes
- Attackers cannot generate new tokens for known individuals
- Attackers cannot determine which attributes produced a token

With only the token file, an attacker cannot identify individuals.

---

## Common Pitfalls

| Issue                         | Cause                     | Solution                                                 |
| ----------------------------- | ------------------------- | -------------------------------------------------------- |
| Zero matches between datasets | Different secrets used    | Verify secret hashes match in metadata files             |
| Partial matches only          | Normalization differences | Ensure both parties use the same Open Link Token version |
| High invalid record counts    | Data quality issues       | Clean data before tokenization; review validation rules  |
| Secrets exposed in logs       | Logging misconfiguration  | Configure logging to exclude sensitive parameters        |
| Token file intercepted        | Insecure transfer         | Use encrypted file transfer; prefer encrypted tokens     |

---

## Checklist: Before Sharing

**Sender:**

- [ ] Agreed on secrets with recipient (via secure channel)
- [ ] Generated tokens with correct secrets
- [ ] Verified metadata shows expected row counts
- [ ] Prepared transfer package (tokens + metadata only)
- [ ] Using encrypted file transfer

**Recipient:**

- [ ] Received secrets via secure channel (separate from token files)
- [ ] Verified secret hashes match sender's metadata
- [ ] Generated own tokens with same secrets
- [ ] Matching logic uses correct RuleId and Token columns

---

## Related Documentation

- [Tokenize](tokenize.md) — When to skip encryption
- [Decrypting Tokens](decrypting-tokens.md) — Reversing encrypted tokens for verification
- [Security](../security.md) — Cryptographic details and key management
- [Key Management & Secrets](../security.md#key-management--secrets) — Secret handling best practices
- [Configuration](../config/configuration.md) — CLI arguments and environment variables
- [Matching Model](../concepts/matching-model.md) — How token matching works
