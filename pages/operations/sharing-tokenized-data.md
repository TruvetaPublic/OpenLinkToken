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
2. Both organizations run Open Link Token on their data using **the same exchange config**
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
│ (same exchange) │                    │ (same exchange) │
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

## Choose an exchange profile

Partners must agree on a crypto suite before generating keys. Use the
[Cryptographic Suites](../concepts/crypto-suites.md) guide to choose between
the version-1 ECDH profiles and the version-2 ML-KEM profiles.

- Use `suite-sha256` when an existing exchange or token namespace requires
  the default version-1 behavior.
- Use `suite-pq` or `suite-pq-shake` for a new ML-KEM-only exchange.

The sender and recipient must use the same suite ID. Do not mix PEM keys with
version-2 JSON bundles.

## End-to-end examples

The two examples below use the same sample input to show the current default
workflow and the post-quantum workflow. Run them from the repository root.
The recipient sends their public key or bundle to the sender; the sender
returns the exchange config and encrypted tokens. Never transfer either
party's private key or bundle.

### Current default: `suite-sha256`

The recipient creates an ECDH key pair and securely sends the public PEM file
to the sender as `./recipient-sha256.public.pem`:

```bash
olt generate-key-pair \
  --crypto-suite suite-sha256 \
  --name recipient-sha256
```

The sender uses that public key to create the exchange config and package the
sample data:

```bash
olt initiate-exchange \
  --crypto-suite suite-sha256 \
  --public-key ./recipient-sha256.public.pem \
  --name sender-sha256 \
  --output ./sender-sha256.exchange.json

olt package \
  -i ./resources/sample.csv \
  -o ./sample-sha256-encrypted.csv \
  --exchange-config ./sender-sha256.exchange.json
```

The sender shares `sender-sha256.exchange.json` and
`sample-sha256-encrypted.csv` with the recipient. The recipient decrypts with
their local private PEM file:

```bash
olt decrypt \
  -i ./sample-sha256-encrypted.csv \
  -o ./sample-sha256-decrypted.csv \
  --exchange-config ./sender-sha256.exchange.json \
  --private-key ~/.openlinktoken/recipient-sha256.private.pem
```

### Post-quantum: `suite-pq`

The recipient creates an ML-KEM key bundle and securely sends the public
bundle to the sender as `./recipient-pq.public.bundle.json`:

```bash
olt generate-key-pair \
  --crypto-suite suite-pq \
  --name recipient-pq
```

The sender uses that public bundle to create the exchange config and package
the same sample data:

```bash
olt initiate-exchange \
  --crypto-suite suite-pq \
  --public-key ./recipient-pq.public.bundle.json \
  --name sender-pq \
  --output ./sender-pq.exchange.json

olt package \
  -i ./resources/sample.csv \
  -o ./sample-pq-encrypted.csv \
  --exchange-config ./sender-pq.exchange.json
```

The sender shares `sender-pq.exchange.json` and `sample-pq-encrypted.csv`
with the recipient. The recipient decrypts with their local private bundle:

```bash
olt decrypt \
  -i ./sample-pq-encrypted.csv \
  -o ./sample-pq-decrypted.csv \
  --exchange-config ./sender-pq.exchange.json \
  --private-key ~/.openlinktoken/recipient-pq.private.bundle.json
```

### Differences

- `suite-sha256` uses the version-1 ECDH exchange and PEM keys; `suite-pq`
  uses the version-2 ML-KEM-768 exchange and JSON key bundles.
- `suite-pq` also changes the token primitives from SHA-256/HMAC-SHA-256 to
  SHA3-256/HMAC-SHA3-256. The command flow is otherwise the same.
- Tokens produced with different suites are not interchangeable for matching.
- In both workflows, share the recipient's public key and then the exchange
  config and encrypted token output. Keep the private key or bundle local.

## Version 1 ECDH Bootstrap Workflow

The version-1 ECDH bootstrap workflow lets partners establish a shared hashing
secret without transmitting it in plaintext. Only the JSON exchange config —
containing the **encrypted** secret — needs to leave the sender's environment.

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

1. Generates a local ECDH key pair for the sender under `~/.openlinktoken/`, reuses a valid existing pair for the selected name or one supplied with `--sender-private-key`, or derives one from `--sender-private-key-env`.
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
  --exchange-config sender-q2.exchange.json
```

## Version 2 ML-KEM Workflow

Version 2 suites use JSON key bundles and the RFC 7516 general JWE JSON
Serialization. The recipient shares a public bundle with the sender, who
creates the exchange config and generates or reuses a local sender bundle.
Each party keeps its own private bundle local.

### Overview

```text
Recipient                                                   Sender
-----------------------------------------------------------|--------------------
generate-key-pair --crypto-suite suite-pq                  |
  private bundle: keep local                               |
  public bundle ------------------------------------------>|
                                                           |
                                                           | initiate-exchange
                                                           |   use recipient public bundle
                                                           |   create exchange config
                                                           |   private bundle: keep local
                                                           |
exchange config <------------------------------------------|
  (encrypted secret and ML-KEM ciphertexts)               |
                                                           |
                                                           | package sample.csv
encrypted tokens <-----------------------------------------|
decrypt with recipient private bundle                      |
  → decrypted tokens (local only)                          |
```

Unlike ECDH, ML-KEM uses encapsulation and decapsulation rather than deriving
a shared secret from a peer public key and a local private key. Each JWE
recipient entry carries an ML-KEM ciphertext that the matching private
bundle can decapsulate. Both parties can open the same exchange config
using their own private bundle; neither needs the other's private bundle.
Token decryption reveals suite-specific hashed tokens, not the original
person data.

### Key generation and exchange creation

```bash
# Recipient: generate a bundle and share only the public bundle
olt generate-key-pair \
  --crypto-suite suite-pq \
  --name recipient-org

# Sender: use the same suite and the recipient's public bundle
olt initiate-exchange \
  --crypto-suite suite-pq \
  --public-key ~/.openlinktoken/recipient-org.public.bundle.json \
  --output ./sender-q2.exchange.json
```

The private bundle remains under `~/.openlinktoken/` on the machine that
generated it. Consumer commands still use only `--exchange-config` plus the
matching private bundle; the suite is read from the exchange artifact.
JWE recipients use `alg=ML-KEM-768` without an ECDH ephemeral key.
The protected JWE header authenticates the exchange
version, suite, and exchange ID.

---

## Sender Workflow (shared exchange config)

The sending organization prepares tokenized data for sharing.

### Step 1: Confirm the Shared Exchange Config

Before tokenization, both parties must use the same exchange config:

- **Exchange config** (required): Carries the encrypted hashing secret and the public-key metadata for transport encryption
- **Private key** (required per party): Each side keeps its own matching private key locally and never shares it

**Best practice:** Share the exchange config over your normal transfer channel, but distribute private keys through your standard secret-management process only.

### Step 2: Run Open Link Token

Generate tokens using the shared exchange config.

**Encrypted mode (recommended for external sharing):**

```bash
olt package \
  -i patient_data.csv \
  -o tokens_for_partner.csv \
  --exchange-config sender-q2.exchange.json
```

**Tokenize (overlap analysis helper, internal artifact):**

Tokenized (unencrypted) output is primarily used **inside your environment** to support overlap analysis against encrypted tokens received from a partner:

```bash
olt tokenize \
  -i local_patient_data.csv \
  -o local_hash_only_tokens.csv \
  --exchange-config sender-q2.exchange.json
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
  }
}
```

**Key checks:**

- `TotalRowsWithInvalidAttributes`: High counts may indicate data quality issues
- `BlankTokensByRule`: T1 and T3 require SSN; blanks are expected if SSN is often missing
- Confirm both sides are using the same exchange config and hashing secret through your secure operational process

### Step 4: Prepare Transfer Package

Use `olt package -o output.zip` to automatically bundle the tokens, metadata, and exchange config into a single archive. Alternatively, include the files separately:

| File                       | Purpose                                                          | Contains Secrets?       |
| -------------------------- | ---------------------------------------------------------------- | ----------------------- |
| `sender-q2.exchange.json`  | Shared exchange config if the recipient does not already have it | No private key material |
| `tokens.parquet`           | Token output (package defaults to Parquet)                       | No                      |
| `tokens.metadata.json`     | Processing and data-quality statistics                           | No secret material      |
| Data dictionary (optional) | Column definitions, RecordId mapping                             | No                      |

Current CLI metadata contains processing and data-quality statistics only; it
does not emit secret hashes.

**Do NOT include:**

- Raw input data (PII)
- Any private key
- Decrypted tokens

### Step 5: Transfer Securely

Use encrypted file transfer:

- SFTP with encryption
- Cloud storage with encryption at rest (S3, Azure Blob, GCS)
- Secure email with encrypted attachment

---

## Recipient Workflow

The receiving organization ingests shared tokens and matches against their own data.

### Step 1: Obtain the Exchange Config and Your Private Key

Receive the shared exchange config and make sure your organization has the matching private key available locally or in a secret store.

### Step 2: Verify You Can Open the Exchange Config

Before processing, verify that your private key matches the shared exchange config:

```bash
python tools/exchange/validate_exchange_secret.py \
  --exchange-config sender-q2.exchange.json \
  --private-key ~/.openlinktoken/recipient-org.private.pem
```

If decryption succeeds, your private key matches one of the exchange recipients and the CLI will be able to resolve the same hashing secret and transport key as the sender.

### Step 3: Generate Your Own Tokens

Run Open Link Token on your local data using the **same exchange config**:

```bash
olt package \
  -i local_patient_data.csv \
  -o local_tokens.csv \
  --exchange-config sender-q2.exchange.json
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
  --exchange-config sender-q2.exchange.json
```

See [Decrypting Tokens](decrypting-tokens.md) for details.

---

## Security Considerations

### Use Encrypted Tokens for External Sharing

Encrypted mode (`package` with an exchange config) adds AES-256-GCM encryption
on top of the suite-selected keyed MAC. For the default
`suite-sha256`, that MAC is HMAC-SHA256:

| Mode      | External Sharing    | Defense in Depth | Reversible                               |
| --------- | ------------------- | ---------------- | ---------------------------------------- |
| Encrypted | ✓ Recommended       | Yes              | To HMAC hash (with matching private key) |
| Tokenize  | ⚠ Use with caution | No               | Not reversible                           |

Encrypted tokens provide an additional security layer if token files are intercepted.

### Protect Exchange Configs and Private Keys

- **Never send private keys with token files.** Each organization keeps its own key material.
- **Store private keys in a vault** (AWS Secrets Manager, HashiCorp Vault, Azure Key Vault)
- **Limit access** to private keys to authorized personnel only
- **Rotate private keys periodically** and reissue exchange configs as needed

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
| Zero matches between datasets | Different secrets used    | Verify both parties used the same exchange config inputs |
| Partial matches only          | Normalization differences | Ensure both parties use the same Open Link Token version |
| High invalid record counts    | Data quality issues       | Clean data before tokenization; review validation rules  |
| Secrets exposed in logs       | Logging misconfiguration  | Configure logging to exclude sensitive parameters        |
| Token file intercepted        | Insecure transfer         | Use encrypted file transfer; prefer encrypted tokens     |

---

## Checklist: Before Sharing

**Sender:**

- [ ] Confirmed the shared exchange config and local private key
- [ ] Generated tokens with the correct exchange config
- [ ] Verified metadata shows expected row counts
- [ ] Prepared transfer package (tokens + metadata only)
- [ ] Using encrypted file transfer

**Recipient:**

- [ ] Received the exchange config and confirmed local private-key access
- [ ] Verified the exchange config can be decrypted locally
- [ ] Generated own tokens with the same exchange config
- [ ] Matching logic uses correct RuleId and Token columns

---

## Related Documentation

- [Tokenize](tokenize.md) — When to skip encryption
- [Decrypting Tokens](decrypting-tokens.md) — Reversing encrypted tokens for verification
- [Security](../security.md) — Cryptographic details and key management
- [Key Management & Secrets](../security.md#key-management--secrets) — Secret handling best practices
- [Configuration](../config/configuration.md) — CLI arguments and environment variables
- [Matching Model](../concepts/matching-model.md) — How token matching works
