---
layout: default
---

# Security

Cryptographic building blocks, key management expectations, and security considerations for privacy-preserving record linkage.

## Overview

Open Link Token generates cryptographically secure tokens for privacy-preserving record linkage across datasets. The system uses deterministic hashing and optional encryption to prevent re-identification while enabling matching on identical person attributes.

**Key security properties:**

- Tokens are one-way (cannot reverse to original data without secrets)
- Same input produces same token (deterministic matching)
- Metadata tracks processing statistics without exposing person data

---

## Cryptographic Building Blocks

### Token Transformation Pipeline

Open Link Token transforms person attributes through multiple layers:

**Encryption mode (default):**

```
Token Signature (normalized attributes)
  ↓
SHA-256 Hash (one-way digest, 256-bit)
  ↓
HMAC-SHA256 (authenticated hash with hashing secret)
  ↓
AES-256-GCM Encrypt (symmetric encryption with encryption key)
  ↓
Base64 Encode (storable format)
```

**`tokenize` subcommand (alternative):**

```
Token Signature
  ↓
SHA-256 Hash
  ↓
HMAC-SHA256 (with hashing secret)
  ↓
Base64 Encode
```

### SHA-256 (Secure Hash Algorithm)

- **Standard**: FIPS 180-4
- **Output**: 256-bit (32-byte) fixed-size digest
- **Collision resistance**: ~2^128 computational effort
- **Purpose**: Convert variable-length token signatures to fixed-size digests

**Properties:**

- One-way function (cannot reverse hash to input)
- Avalanche effect (small input change produces completely different hash)
- Deterministic (same input always produces same hash)

### HMAC-SHA256 (Hash-based Message Authentication Code)

- **Standard**: FIPS 198-1
- **Input**: SHA-256 hash + hashing secret
- **Output**: 256-bit authenticated hash
- **Purpose**: Prevent rainbow table attacks and verify secret usage

**Security benefits:**

- Requires secret key to generate matching hashes
- Prevents pre-computation of token values
- Different secret produces completely different output for same input

**Formula:**

```
HMAC-SHA256(message, key) = SHA256((key ⊕ opad) || SHA256((key ⊕ ipad) || message))
```

### AES-256-GCM (Advanced Encryption Standard with Galois/Counter Mode)

- **Standard**: FIPS 197
- **Key size**: 256-bit (32-byte)
- **Mode**: GCM (Galois/Counter Mode) with authentication
- **Purpose**: Encrypt tokens to prevent re-identification

**Technical details:**

- **Initialization Vector (IV)**: 12 bytes, randomly generated per token
- **Authentication tag**: 128-bit (16-byte) GCM tag for integrity
- **Padding**: NoPadding (GCM mode handles message length)
- **Algorithm**: `AES/GCM/NoPadding`

**Security properties:**

- Authenticated encryption (detects tampering)
- Unique IV per token prevents pattern analysis
- Computationally infeasible to brute-force (2^256 possible keys)
- Reversible only with correct encryption key

---

## Key Management & Secrets

This section consolidates practical guidance for managing the cryptographic secrets Open Link Token requires.

### Types of Secrets

Open Link Token uses two secrets. Which secrets are required depends on the subcommand:

| Secret             | CLI Flag                 | Purpose                                   | Required for subcommands        | Requirements                         |
| ------------------ | ------------------------ | ----------------------------------------- | ------------------------------- | ------------------------------------ |
| **Hashing Secret** | `-h` / `--hashingsecret` | HMAC-SHA256 key for deterministic hashing | `package`, `tokenize`           | 8+ characters recommended, 16+ ideal |
| **Encryption Key** | `-e` / `--encryptionkey` | AES-256-GCM symmetric key                 | `package`, `encrypt`, `decrypt` | **Exactly 32 characters**            |

### Handling Secrets in Practice

#### Development / Local Testing

Use clearly marked placeholder values:

```bash
# Placeholder secrets for local testing only
olt package \
  -i sample.csv -o output.csv \
  -h "HashingKey" \
  -e "Secret-Encryption-Key-Goes-Here."
```

Store these in a local `.env` file (not committed):

```bash
# .env (add to .gitignore)
OLT_HASHING_SECRET=HashingKey
OLT_ENCRYPTION_KEY=Secret-Encryption-Key-Goes-Here.
```

Load and use:

```bash
source .env
olt package \
  -i sample.csv -o output.csv \
  -h "$OLT_HASHING_SECRET" \
  -e "$OLT_ENCRYPTION_KEY"
```

#### Production

Store secrets in a managed secret store and inject via environment variables at runtime:

| Platform   | Secret Store       | Injection Method                                            |
| ---------- | ------------------ | ----------------------------------------------------------- |
| AWS        | Secrets Manager    | `aws secretsmanager get-secret-value` or ECS/Lambda secrets |
| Azure      | Key Vault          | `az keyvault secret show` or App Service key references     |
| GCP        | Secret Manager     | `gcloud secrets versions access` or workload identity       |
| On-prem    | HashiCorp Vault    | `vault kv get` or agent auto-auth                           |
| Databricks | Databricks Secrets | `dbutils.secrets.get("scope", "key")`                       |

**Example (AWS Secrets Manager):**

```bash
export OLT_HASHING_SECRET=$(aws secretsmanager get-secret-value \
  --secret-id openlinktoken-hash-key --query SecretString --output text)
export OLT_ENCRYPTION_KEY=$(aws secretsmanager get-secret-value \
  --secret-id openlinktoken-enc-key --query SecretString --output text)

olt package \
  -i data.csv -o tokens.csv \
  -h "$OLT_HASHING_SECRET" \
  -e "$OLT_ENCRYPTION_KEY"
```

**Example (Databricks):**

```python
from openlinktoken_pyspark import SparkPersonTokenProcessor

processor = SparkPersonTokenProcessor(
    spark=spark,
    hashing_secret=dbutils.secrets.get("openlinktoken", "hashing_secret"),
    encryption_key=dbutils.secrets.get("openlinktoken", "encryption_key")
)
```

### Secret Rotation

1. **Generate new secrets** – use a cryptographically secure generator.
2. **Re-run token generation** – tokens are deterministic; same input + same secrets = same tokens. New secrets = new tokens.
3. **Version secrets in your store** – keep old versions for auditability.
4. **Coordinate downstream** – any system that decrypts tokens needs the matching encryption key.

### What NOT to Do

- **Never commit secrets to source control.** Add `.env` and similar files to `.gitignore`.
- **Never log secrets.** CLI output and metadata files contain hashes of secrets, not the secrets themselves.
- **Never hard-code secrets in scripts checked into git.** Use environment variables or secret-store references.

### Secret Verification via Metadata

Each run produces a `.metadata.json` with SHA-256 hashes of secrets:

```json
{
  "HashingSecretHash": "e0b4e60b...",
  "EncryptionSecretHash": "a1b2c3d4..."
}
```

Use [tools/hash_calculator.py](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/tools/hash_calculator.py) to verify:

```bash
python tools/hash_calculator.py \
  --hashing-secret "YourSecret" \
  --encryption-key "YourEncryptionKey"
# Compare output hashes to metadata file
```

### Cross-References

- **CLI flags for secrets**: [CLI Reference](reference/cli.md)
- **Environment variable usage**: [Configuration](config/configuration.md#environment-variables)
- **Databricks / Spark secrets**: [Spark or Databricks](operations/spark-or-databricks.md)
- **Running the CLI**: [Running Open Link Token](running-openlinktoken/index.md)
- **Metadata format (hash fields)**: [Reference: Metadata Format](reference/metadata-format.md)

---

## Security Considerations and Limitations

### What Open Link Token Protects Against

**✓ Re-identification without secrets:**

- Encrypted tokens cannot be reversed without encryption key
- Hashed tokens cannot be reversed (one-way HMAC-SHA256)
- Attacker with tokens alone cannot recover person data

**✓ Rainbow table attacks:**

- HMAC-SHA256 with secret prevents pre-computed lookup tables
- Different secret produces different tokens for same input

**✓ Data quality issues:**
Metadata captures processing statistics; data quality guidance lives in the concepts documentation.

### What Open Link Token Does NOT Protect Against

**✗ Compromise of secrets:**

- If attacker obtains hashing secret + encryption key, they can regenerate tokens from known person data
- Token security depends entirely on secret protection

**✗ Side-channel attacks:**

- Timing attacks, memory access patterns not specifically mitigated
- Use secure execution environments for sensitive workloads

**✗ Statistical analysis with auxiliary data:**

- If attacker has auxiliary demographic data and token frequency distributions, statistical attacks may be possible
- Consider differential privacy techniques for high-risk scenarios

**✗ Token distribution analysis:**

- Tokens are deterministic (same person always produces same token)
- Frequency analysis may reveal population patterns
- Mitigate by limiting token distribution and enforcing access controls

### User Responsibilities

Open Link Token provides cryptographic primitives but **users are responsible for:**

- **Secret management**: Storing, rotating, and protecting hashing secrets and encryption keys
- **Access control**: Limiting who can generate, access, or decrypt tokens
- **Token storage**: Encrypting token files at rest (file system encryption, database encryption)
- **Audit logging**: Tracking token generation, access, and decryption events
- **Data minimization**: Deleting raw person data after token generation
- **Compliance**: Ensuring usage aligns with HIPAA, GDPR, or organizational policies

### Threat Model Assumptions

**Assumptions:**

- Secrets are stored securely and not accessible to unauthorized parties
- Execution environment is trusted (no malware or unauthorized access)
- Token outputs are protected with access controls
- Users validate data quality before token generation

**Out of scope:**

- Protection against compromised execution environments
- Protection after decryption (decrypted tokens are plaintext hashes)
- Protection against authorized users misusing tokens

### Data Quality: Normalization and Validation

Normalization and validation rules are documented separately to keep this page focused on cryptography and secret management.

See [Concepts: Normalization and Validation](concepts/normalization-and-validation.md).

---

## Next Steps

- **View detailed crypto pipeline**: [Specification](specification.md)
- **Understand metadata security**: [Reference: Metadata Format](reference/metadata-format.md)
- **Review validation rules**: [Concepts: Normalization and Validation](concepts/normalization-and-validation.md)
- **Configure Open Link Token**: [Configuration](config/configuration.md)
- **Share tokens across organizations**: [Sharing Tokenized Data](operations/sharing-tokenized-data.md)
