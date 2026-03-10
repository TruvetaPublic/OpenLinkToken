---
layout: default
---

# Sharing Tokenized Data Between Organizations

How to securely exchange OpenToken outputs for cross-organization record linkage.

---

## Overview

Organizations often need to identify overlapping individuals across datasets without exposing raw person data. OpenToken enables this by generating deterministic, cryptographically secure tokens that can be shared and matched externally.

**Typical scenario:**

1. Organization A and Organization B each hold patient records
2. Both organizations run OpenToken on their data using **the same secrets**
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
│   OpenToken     │                    │   OpenToken     │
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

### Overview

```text
Recipient                                   Sender
─────────────────────────────────────────────────────
generate-key-pair                                │
  → recipient.public.pem ──────────────────────►│
                                                 │
                                         initiate-exchange
                                           --public-key recipient.public.pem
                                           → sender.exchange.json
                                           → sender.private.pem (local only)
                                                 │
                              ◄──────────────────┤ sender.exchange.json
                                                 │ (contains encrypted secret)
Recover hashing secret
from sender's local public key
+ own private key (ECDH)
```

### Step 1 — Recipient generates a key pair

```bash
opentoken generate-key-pair --name recipient-org
```

This writes:

- `~/.opentoken/recipient-org.private.pem` — keep this secret, never share it
- `~/.opentoken/recipient-org.public.pem` — share this with the sender

### Step 2 — Sender initiates the exchange

```bash
opentoken initiate-exchange \
  --name sender-q2 \
  --public-key ./recipient-org.public.pem \
  --output ./sender-q2.exchange.json
```

This:

1. Generates a local ECDH key pair for the sender under `~/.opentoken/`.
2. Generates a secure random hashing secret (or accepts one via `--hashingsecret`).
3. Derives a shared secret via ECDH from the sender's private key and the recipient's public key.
4. Expands the shared secret into an AES-256 key via HKDF.
5. Encrypts the hashing secret with AES-256-GCM and writes `sender-q2.exchange.json`.

The exchange config **never** contains the sender's private key or the plaintext hashing secret.

### Step 3 — Sender transfers the exchange config

Transfer `sender-q2.exchange.json` to the recipient over any channel. The hashing secret inside is encrypted; only a holder of the matching private key can recover it.

### Step 4 — Recipient recovers the hashing secret

The recipient uses the sender's local public key (embedded in the exchange config) together with their own private key to derive the same shared secret and decrypt the hashing secret:

```python
import base64, json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ec import ECDH
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from pathlib import Path

config = json.loads(Path("sender-q2.exchange.json").read_text())
recipient_private = load_pem_private_key(
    Path("~/.opentoken/recipient-org.private.pem").expanduser().read_bytes(), password=None
)
sender_public = load_pem_public_key(config["local_public_key"].encode())

shared_secret = recipient_private.exchange(ECDH(), sender_public)
hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"opentoken-exchange-v1")
aes_key = hkdf.derive(shared_secret)

nonce = base64.b64decode(config["encryption"]["nonce"])
ciphertext = base64.b64decode(config["encrypted_hashing_secret"])
hashing_secret = AESGCM(aes_key).decrypt(nonce, ciphertext, None)
print("Recovered hashing secret:", hashing_secret.decode())
```

### Step 5 — Both parties tokenize using the recovered secret

Once both parties have the hashing secret they run `opentoken package` as normal:

```bash
opentoken package \
  -i patient_data.csv -t csv \
  -o tokens_for_partner.csv \
  -h "$HASHING_SECRET" \
  -e "$ENCRYPTION_KEY"
```

---

## Sender Workflow (manual secret agreement)

The sending organization prepares tokenized data for sharing.

### Step 1: Agree on Shared Secrets

Before tokenization, both parties must agree on:

- **Hashing secret** (required): Used for HMAC-SHA256
- **Encryption key** (recommended for external sharing): Used for AES-256-GCM

**Best practice:** Use a secure channel (encrypted email, secure file transfer, or direct key exchange in person) to share secrets. Never send secrets alongside token files.

### Step 2: Run OpenToken

Generate tokens using the agreed-upon secrets.

**Encrypted mode (recommended for external sharing):**

```bash
opentoken package \
  -i patient_data.csv \
  -t csv \
  -o tokens_for_partner.csv \
  -h "$SHARED_HASHING_SECRET" \
  -e "$SHARED_ENCRYPTION_KEY"
```

**Tokenize (overlap analysis helper, internal artifact):**

Tokenized (unencrypted) output is primarily used **inside your environment** to support overlap analysis against encrypted tokens received from a partner:

```bash
opentoken tokenize \
  -i local_patient_data.csv \
  -t csv \
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

Run OpenToken on your local data using the **same secrets**:

```bash
opentoken package \
  -i local_patient_data.csv \
  -t csv \
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
opentoken decrypt \
  -i partner_tokens.csv \
  -t csv \
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

- **Log token generation events**: Who ran OpenToken, when, with which input file
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

| Issue                         | Cause                     | Solution                                                |
| ----------------------------- | ------------------------- | ------------------------------------------------------- |
| Zero matches between datasets | Different secrets used    | Verify secret hashes match in metadata files            |
| Partial matches only          | Normalization differences | Ensure both parties use the same OpenToken version      |
| High invalid record counts    | Data quality issues       | Clean data before tokenization; review validation rules |
| Secrets exposed in logs       | Logging misconfiguration  | Configure logging to exclude sensitive parameters       |
| Token file intercepted        | Insecure transfer         | Use encrypted file transfer; prefer encrypted tokens    |

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
