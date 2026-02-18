# Privacy-Preserving Record Linkage (PPRL) Demonstration <!-- omit in toc -->

This demonstration shows how to use OpenToken for privacy-preserving record linkage between two organizations sharing patient data.

For a step-by-step walkthrough, start with the Jupyter notebook: [PPRL_Superhero_Demo.ipynb](PPRL_Superhero_Demo.ipynb). You can also run the full demo end-to-end with `./run_end_to_end.sh`.

## Table of Contents <!-- omit in toc -->

- [Overview](#overview)
- [Tokenization basics](#tokenization-basics)
- [Run the demo](#run-the-demo)
- [Outputs](#outputs)
- [Decryption and privacy](#decryption-and-privacy)
- [Customize and next steps](#customize-and-next-steps)

## Overview

### 5-minute explanation <!-- omit in toc -->

### Goal <!-- omit in toc -->

Help two organizations figure out which records refer to the same person, **without exchanging raw identifiers** (like names or Social Security Numbers).

### What gets shared <!-- omit in toc -->

- **Encrypted tokens**: Random-looking strings generated from identifiers. These are safe to share and store for matching.
- **Match results**: A list of matching record IDs (e.g., which hospital record matches which pharmacy record).
- **Metadata**: Counts and run information (and hashes of the secrets), but not the secrets themselves.

### What never gets shared <!-- omit in toc -->

- Raw identifiers from the source data (names, birth dates, Social Security Numbers, postal codes).
- The secret keys in any public place. (This demo uses example keys for convenience; real deployments must manage keys securely.)

### What you should expect to see after running the demo <!-- omit in toc -->

- Two synthetic CSV datasets created under `datasets/`.
- Two token CSV files under `outputs/` (one per organization), plus metadata JSON files.
- A `matching_records.csv` file with about **40 matching pairs**.

One important detail: because tokens are encrypted with random “salt” each time, the encrypted token strings will **not** match across independent runs. The matching step decrypts tokens to a consistent, one-way fingerprint (a hash) that can be compared for equality. This does **not** reveal the original names or IDs.

> **Important demo disclaimer:** This example uses fully synthetic data and example secrets that are safe for illustration only. Never reuse these keys or patterns in production. Real deployments must use proper key management, strict access controls around decryption and matching, and clear governance over who can run linkage jobs and how results are used.

### Who does what (roles) <!-- omit in toc -->

This demo focuses on two organizations that want to link their datasets without sharing raw identifiers.

In this demo, assume the **hospital** runs the overlap analysis step (it receives the pharmacy token file and compares tokens to find matches).

> **Note (optional deployment patterns):** In real deployments, the overlap analysis can be run by either party, in a jointly operated shared environment, or (optionally) by a third-party matching service. OpenToken does not require a third party.

| Role     | What they hold                                       | What they share             | Needs hashing secret?                              | Needs encryption key?                  |
| -------- | ---------------------------------------------------- | --------------------------- | -------------------------------------------------- | -------------------------------------- |
| Hospital | Raw hospital dataset (identifiers + hospital fields) | Encrypted tokens + metadata | Yes (to generate the comparable fingerprint layer) | Yes (to encrypt tokens before sharing) |
| Pharmacy | Raw pharmacy dataset (identifiers + pharmacy fields) | Encrypted tokens + metadata | Yes (to generate the comparable fingerprint layer) | Yes (to encrypt tokens before sharing) |

Why “decrypting to compare” does **not** reveal raw identifiers:

- The encrypted token contains an encrypted, one-way fingerprint (a deterministic HMAC hash) of the identifiers after normalization.
- Decrypting a token reveals that fingerprint, which is useful for checking **equality** (same person attributes → same fingerprint), but it does not contain the original names/SSNs/birth dates.
- In this demo, the hospital can learn **which records match** across datasets because it runs the overlap analysis step. That is the point of record linkage, and it’s why decryption should happen only in a trusted environment.

### Flow diagram and glossary <!-- omit in toc -->

### Flow diagram (what happens to the data) <!-- omit in toc -->

```text
Hospital/Pharmacy (separately)
  Raw identifiers (name, DOB, SSN, etc.)
    → Normalize (standardize formatting)
    → HMAC (one-way fingerprint; deterministic)
    → Encrypt (random IV; produces different ciphertext each run)
    → Share encrypted tokens

Hospital (overlap analysis in this demo)
  Encrypted tokens from both organizations
    → Decrypt (back to the HMAC fingerprint)
    → Compare fingerprints (equality check)
    → Output matches (record IDs that link)
```

### Glossary (quick definitions) <!-- omit in toc -->

- **Token**: A privacy-preserving stand-in for identifiers. In this demo, the token you share is an encrypted value.
- **Normalization**: Cleaning/standardizing input so the same real-world value formats consistently (e.g., casing, whitespace).
- **Hash / HMAC**: A one-way “fingerprint” of data. HMAC is keyed (it uses a secret) so only parties with the secret can create the same fingerprint.
- **Encryption**: Scrambling data so only someone with the key can recover what was encrypted.
- **IV (initialization vector)**: Random value used during encryption so encrypting the same thing twice produces different encrypted outputs.
- **Deterministic vs. randomized**: Deterministic means “same input → same output” (the HMAC layer). Randomized means “same input → different output each run” (the encryption layer because of the IV).

### What this demo demonstrates (and what it does not) <!-- omit in toc -->

### What it demonstrates <!-- omit in toc -->

- Two organizations can create encrypted tokens from identifiers and share only those tokens for linkage.
- A trusted matching step can decrypt tokens back to one-way fingerprints and compare them to find overlaps.
- In this demo, the hospital performs the overlap analysis; more generally, either party can do this in a trusted environment, and a third-party matching service is optional.
- You get a simple, auditable output: which record IDs match between the two datasets.

### What it does not demonstrate (limitations) <!-- omit in toc -->

- **Exact-match linkage**: This demo treats records as a match only when the required token set matches exactly.
- **Clean, synthetic data**: The datasets are synthetic and intentionally constructed to have a known overlap.
- **Shared secrets assumption**: The demo assumes both organizations use the same hashing secret and encryption key.
- **No typo tolerance**: If identifiers differ (typos, nicknames, missing fields), tokens may not match.
- **Not SMPC**: This is not secure multi-party computation; decryption and matching happen inside a trusted environment.

### Next steps <!-- omit in toc -->

- Try threshold matching (for example, require 4 out of 5 tokens to match) and then do clerical review for borderline pairs.
- Add real-world key management: keep secrets in a key management system (KMS) or hardware security module (HSM).
- Define governance: who is allowed to decrypt, where matching runs, how long outputs are kept, and what gets audited.

### Scenario <!-- omit in toc -->

**Super Hero Hospital** and **Super Hero Pharmacy** want to link their patient records to improve care coordination, but they need to protect patient privacy. They use OpenToken to:

1. Generate encrypted tokens from patient identifiers (name, birthdate, SSN, etc.)
2. Share only the encrypted tokens (not raw patient data)
3. Find matching patients by comparing tokens

### Dataset Overview <!-- omit in toc -->

- **Hospital Dataset**: 100 super hero patients with hospital-specific information
  - Columns: RecordId, FirstName, LastName, Sex, BirthDate, SocialSecurityNumber, PostalCode, Department, VisitReason
  
- **Pharmacy Dataset**: 120 super hero patients with pharmacy-specific information
  - Columns: RecordId, FirstName, LastName, Sex, BirthDate, SocialSecurityNumber, PostalCode, MedicationType, PrescriptionType
  
- **Expected Overlap**: 40 patients (40% of hospital dataset) appear in both datasets with identical person attributes

## Tokenization basics

### How OpenToken Works <!-- omit in toc -->

OpenToken generates 5 different tokens (T1-T5) for each patient using different combinations of attributes:

| Token ID | Token Components                                         |
| -------- | -------------------------------------------------------- |
| T1       | `U(last-name)\|U(first-name-1)\|U(sex)\|birth-date`      |
| T2       | `U(last-name)\|U(first-name)\|birth-date\|postal-code-3` |
| T3       | `U(last-name)\|U(first-name)\|U(sex)\|birth-date`        |
| T4       | `social-security-number\|U(sex)\|birth-date`             |
| T5       | `U(last-name)\|U(first-name-3)\|U(sex)`                  |

> **Note**: U(X) means uppercase(X), and attribute-N means taking the first N characters

Each token is:

1. Normalized (standardized format)
2. Hashed with HMAC-SHA256
3. Encrypted with AES-256-GCM (with random IV for security)

### Match policy (how you decide what counts as a match) <!-- omit in toc -->

OpenToken does **not** define a single, universal “match policy.” A match policy is something the parties agree on up front: it determines **which token IDs must match** (and how many) before you treat two records as referring to the same person.

This matters because different token combinations trade off **false positives** vs. **missed matches** depending on your data quality and your risk tolerance.

**In this demo**: a record pair is considered a match only if **all 5 tokens (T1–T5) match exactly**. This is intentionally strict: it reduces false positives, but it can miss matches when there are typos, nicknames, or missing fields.

### Custom tokens (optional) <!-- omit in toc -->

T1–T5 are **standard** token definitions provided by OpenToken, but they are not the only possible approach.

If needed, the parties can define **additional custom token rules** (new token IDs) based on different attribute combinations or matching goals. The key requirement is that **both parties must use the exact same token definitions and normalization rules**, otherwise tokens won’t be comparable.

### Important Note About Token Comparison <!-- omit in toc -->

OpenToken uses **AES-256-GCM encryption with random initialization vectors (IVs)** for enhanced security. This means:

- Each tokenization run produces different encrypted values, even for identical input data
- To compare tokens across independently tokenized datasets, **tokens must be decrypted first**
- Decryption reveals the underlying HMAC-SHA256 hash (not the original data)
- The HMAC-SHA256 hashes are deterministic and can be compared for matching

This demonstration shows how to properly compare tokens from two organizations that tokenized their data independently.

## Run the demo

### Prerequisites <!-- omit in toc -->

- Java 17 or higher
- Maven 3.6 or higher
- Python 3.7+ (for data generation and analysis)

### Quick Start Guide <!-- omit in toc -->

### Notebook walkthrough (recommended) <!-- omit in toc -->

For a step-by-step walkthrough, start with the Jupyter notebook:

- Open [PPRL_Superhero_Demo.ipynb](PPRL_Superhero_Demo.ipynb)
- Run the cells from top to bottom

The notebook walks through dataset generation, tokenization, and overlap analysis (including an example of relaxing the match policy).

### End-to-end script (one command) <!-- omit in toc -->

If you want to run the same demo end-to-end without the notebook, use the script below.

### Run End-to-End (one command, recommended) <!-- omit in toc -->

```bash
cd demos/pprl-superhero-example
chmod +x run_end_to_end.sh
./run_end_to_end.sh
```

This runs dataset generation, tokenization (building Java if needed), and overlap analysis.

### What the script does (step-by-step) <!-- omit in toc -->

You can also run the same three steps manually. These commands assume you are in the demo directory:

```bash
cd demos/pprl-superhero-example
```

#### Step 1: Generate Datasets <!-- omit in toc -->

```bash
python scripts/generate_superhero_datasets.py
```

This creates:

- `datasets/hospital_superhero_data.csv` (100 records)
- `datasets/pharmacy_superhero_data.csv` (120 records with 40 overlapping)

#### Step 2: Tokenize the Data <!-- omit in toc -->

Each organization tokenizes their own dataset independently:

```bash
chmod +x scripts/tokenize_hospital.sh scripts/tokenize_pharmacy.sh

# Hospital tokenizes hospital data
./scripts/tokenize_hospital.sh

# Pharmacy tokenizes pharmacy data
./scripts/tokenize_pharmacy.sh
```

These scripts simulate two separate tokenization processes:

1. **Hospital tokenizes their dataset** → `outputs/hospital_tokens.csv`
2. **Pharmacy tokenizes their dataset** → `outputs/pharmacy_tokens.csv`
3. Metadata files are created for both datasets

**Critical Requirements**:

- Both organizations must use the **same hashing and encryption keys**
- Keys must be shared securely between organizations before tokenization
- In production, use strong keys and secure key exchange protocols

#### Step 3: Measure Overlap <!-- omit in toc -->

```bash
python scripts/analyze_overlap.py
```

This script performs the record linkage analysis:

1. **Loads** encrypted tokens from both datasets
2. **Decrypts** tokens to get the underlying HMAC-SHA256 hashes
   - Decryption is necessary because OpenToken uses random IVs for encryption
   - Each tokenization produces different encrypted values for the same data
   - Decryption reveals the deterministic hash values that can be compared
3. **Compares** decrypted tokens to find matches
4. **Reports** matching statistics
5. **Saves** results to `outputs/matching_records.csv`

**Note**: The analysis script requires the encryption key to decrypt tokens. This key must match the one used during tokenization.

## Outputs

### Expected Results <!-- omit in toc -->

After running the analysis, you should see:

```text
MATCH SUMMARY
======================================================================
Total matching record pairs: 40

Matches with 5 tokens: 40

OVERLAP STATISTICS
======================================================================
Hospital records with matches: 40 out of 100 (40.0%)
Pharmacy records with matches: 40 out of 120 (33.3%)
======================================================================
```

### Understanding the Output <!-- omit in toc -->

This demo creates files under `datasets/` (raw synthetic data) and `outputs/` (tokens, metadata, and match results). You can open the CSV files in any spreadsheet tool or text editor.

### Step-by-step: what files are created <!-- omit in toc -->

1. **Raw synthetic datasets** (created by the data generation step)

    - `datasets/hospital_superhero_data.csv`: The hospital’s source dataset (includes identifiers + hospital fields).
    - `datasets/pharmacy_superhero_data.csv`: The pharmacy’s source dataset (includes identifiers + pharmacy fields).

1. **Encrypted token files** (created by the tokenization step)

    - `outputs/hospital_tokens.csv`
    - `outputs/pharmacy_tokens.csv`

    Each row is one token for one record. Each record should have 5 rows (T1–T5).

    | Column   | Description                                    |
    | -------- | ---------------------------------------------- |
    | RuleId   | Token type (T1, T2, T3, T4, or T5)             |
    | Token    | Encrypted match token (ot.V1 format)           |
    | RecordId | The original record ID from the source dataset |

1. **Metadata JSON files** (created alongside tokenization)

    - `outputs/hospital_tokens.metadata.json`
    - `outputs/pharmacy_tokens.metadata.json`

    These include counts (processed/valid/invalid), a timestamp/version, and SHA-256 hashes of the secrets used (but not the secrets themselves).

1. **Matching results** (created by the overlap analysis step)

    - `outputs/matching_records.csv`: The strict match results (expects all 5 tokens to match).
    - `outputs/matching_records_alt.csv`: An alternate match output (if you run a relaxed rule set).

    `matching_records.csv` has one row per matching pair:

    | Column           | Description                                                      |
    | ---------------- | ---------------------------------------------------------------- |
    | HospitalRecordId | Record ID from the hospital dataset                              |
    | PharmacyRecordId | Record ID from the pharmacy dataset                              |
    | MatchingTokens   | Which tokens matched (for strict matching: `T1\|T2\|T3\|T4\|T5`) |
    | TokenCount       | Number of matching tokens (for strict matching: `5`)             |

### Simple checks you can do (no special tools) <!-- omit in toc -->

1. Open `outputs/hospital_tokens.csv` and pick a `RecordId`. You should see 5 rows for that `RecordId`, with `RuleId` values `T1` through `T5`.
2. Re-run the demo and compare any one `Token` value for the same `RecordId` and `RuleId`: the encrypted `Token` text should change between runs (because encryption is randomized).
3. Open `outputs/matching_records.csv`: you should see about **40** rows, and most (or all) rows should have `TokenCount` = `5`.

## Decryption and privacy

### Understanding Token Decryption in PPRL <!-- omit in toc -->

### Why Decryption is Necessary <!-- omit in toc -->

OpenToken uses **AES-256-GCM encryption with random IVs** (initialization vectors) for each encryption operation. This is a security best practice that prevents pattern analysis attacks. However, it creates a challenge for multi-party record linkage:

1. **Problem**: Hospital tokenizes their data → produces encrypted tokens with random IVs
2. **Problem**: Pharmacy tokenizes their data → produces different encrypted tokens (different IVs)
3. **Result**: Even for identical patients, encrypted tokens differ and won't match directly

### The Solution <!-- omit in toc -->

To enable record linkage across independently tokenized datasets:

1. **Decrypt** tokens to reveal the underlying HMAC-SHA256 hash layer
2. **Compare** the decrypted hashes (which are deterministic and identical for matching data)
3. **Important**: Decryption only reveals the hash, NOT the original patient data

**Example**:

```text
Hospital encrypts:
  Patient "John Doe" → HMAC-SHA256 hash → AES encrypt with IV₁ → Token A

Pharmacy encrypts:
  Patient "John Doe" → HMAC-SHA256 hash → AES encrypt with IV₂ → Token B

Token A ≠ Token B (different IVs)

But decrypt(Token A) = decrypt(Token B) = same HMAC-SHA256 hash ✓
```

### Decryption Layer Structure <!-- omit in toc -->

```text
Raw Data → Normalization → HMAC-SHA256 → AES-GCM Encryption
                              ↑               ↑
                         Deterministic    Random IV
                         (comparable)    (not comparable)
```

For matching: We decrypt to the HMAC layer, which is deterministic and comparable.

### Privacy Considerations <!-- omit in toc -->

### What is Protected <!-- omit in toc -->

- **Raw patient data** is never shared between organizations
- **HMAC-SHA256 hashes** cannot be reversed to get original data
- **Encryption key** controls who can decrypt and perform linkage
- **Hashing secret** ensures only parties with the key can generate comparable tokens

### What is Shared <!-- omit in toc -->

- **Encrypted tokens** for secure transmission between organizations
- **Decrypted hashes** (within secure matching environment only)
- **Matching statistics** - organizations see overlap counts without raw identities

### Security Best Practices <!-- omit in toc -->

1. **Key Management**:
   - Use strong, cryptographically random keys (not the demo keys!)
   - Share keys only through secure channels (encrypted email, key management systems)
   - Rotate keys periodically (requires re-tokenization)

2. **Access Control**:
   - Limit decryption capability to authorized matching systems only
   - Log all decryption and matching operations
   - Use separate environments for tokenization vs. matching

3. **Data Governance**:
   - Establish data use agreements before sharing tokens
   - Define permitted uses of matching results
   - Implement audit trails for all token operations

4. **Technical Controls**:
   - Never store decrypted hashes long-term
   - Perform matching in secure, isolated environments
   - Delete tokens after matching is complete (per agreement)

### FAQ <!-- omit in toc -->

### Can you reverse the tokens to get names or SSNs? <!-- omit in toc -->

No – the design is intentionally one-way. Even after decryption, you only see a deterministic HMAC-SHA256 fingerprint of the normalized identifiers, not the original names or SSNs. In practice, re-identification would require both key compromise and additional side information, which is why strong key management and governance are critical in real deployments.

### Why do encrypted tokens differ between runs? <!-- omit in toc -->

OpenToken uses AES-GCM encryption with a fresh random IV for each token, so encrypting the same fingerprint twice produces different ciphertexts. This prevents attackers from learning when two encrypted values are the same just by looking at the bytes. Under the hood, the deterministic HMAC fingerprint is the same for identical input, which is what the matching step compares after decryption.

### Who should be allowed to decrypt? <!-- omit in toc -->

Only a tightly controlled, trusted environment should hold the decryption key. In this demo, assume the hospital has access to the decryption key so it can run the overlap analysis. In production, you typically restrict decryption to a minimal set of systems (run by one party, jointly operated), following least privilege.

### What happens with typos or missing fields? <!-- omit in toc -->

This demo uses exact-match tokens built from normalized values, so typos, nicknames, or missing attributes usually lead to different fingerprints and therefore no match. In other words, if a key field changes, the corresponding token changes and the pair will be treated as non-matching. Production systems often add more robust strategies on top of this (such as alternate token definitions, phonetic encodings, or "4 out of 5" token thresholds) to handle real-world data quality.

### File Structure <!-- omit in toc -->

```text
pprl-superhero-example/
├── README.md                          # This file
├── run_end_to_end.sh                  # Complete demo runner (all 3 steps)
├── datasets/                          # Generated datasets
│   ├── hospital_superhero_data.csv
│   └── pharmacy_superhero_data.csv
├── scripts/                           # Individual scripts for demo
│   ├── generate_superhero_datasets.py # Generate test data
│   ├── tokenize_hospital.sh           # Tokenize hospital dataset
│   ├── tokenize_pharmacy.sh           # Tokenize pharmacy dataset
│   ├── tokenize_datasets.sh           # Wrapper (calls both scripts)
│   └── analyze_overlap.py            # Analyze overlaps
└── outputs/                           # Tokenization outputs
    ├── hospital_tokens.csv
    ├── hospital_tokens.metadata.json
    ├── pharmacy_tokens.csv
    ├── pharmacy_tokens.metadata.json
    └── matching_records.csv
```

## Customize and next steps

### Customization <!-- omit in toc -->

### Changing Dataset Size <!-- omit in toc -->

Edit `generate_superhero_datasets.py`:

```python
num_hospital = 200      # Hospital records
num_pharmacy = 250      # Pharmacy records
overlap_percentage = 0.30  # 30% overlap
```

### Using Different Secrets <!-- omit in toc -->

Edit both tokenization scripts (and keep them identical across parties):

- `scripts/tokenize_hospital.sh`
- `scripts/tokenize_pharmacy.sh`

```bash
HASHING_SECRET="YourCustomHashingKey"
ENCRYPTION_KEY="YourCustomEncryptionKey-32"
```

**Important**: Both datasets must use the same secrets for tokens to be comparable!

### Adjusting Match Criteria <!-- omit in toc -->

Edit `analyze_overlap.py` to require fewer matching tokens:

```python
# Find matches with at least 4 out of 5 tokens matching
matches = find_matches(hospital_tokens, pharmacy_tokens, required_token_matches=4)
```

### Troubleshooting <!-- omit in toc -->

### "No matches found" <!-- omit in toc -->

**Cause**: Datasets were tokenized with different secrets.

**Solution**: Ensure both tokenizations use identical hashing and encryption keys.

### "Invalid attribute" errors during tokenization <!-- omit in toc -->

**Cause**: Some generated data doesn't meet OpenToken validation rules.

**Solution**: This is expected. OpenToken validates data (e.g., SSN format, birthdate ranges) and skips invalid records. Check the metadata file for details.

### Build errors <!-- omit in toc -->

**Cause**: Maven or Java not installed/configured.

**Solution**:

```bash
# Check Java
java -version  # Should be 11+

# Check Maven
mvn -version   # Should be 3.6+
```

### Real-World Applications <!-- omit in toc -->

This demonstration can be adapted for:

- **Healthcare**: Hospital-to-hospital patient matching
- **Insurance**: Claims linkage across providers
- **Research**: Multi-site study participant matching
- **Government**: Cross-agency identity resolution
- **Financial Services**: Anti-fraud systems

### Additional Resources <!-- omit in toc -->

- [OpenToken Main README](../../README.md)
- [Development Guide](../../docs/dev-guide-development.md)
- [Metadata Format Documentation](../../docs/metadata-format.md)

### Questions? <!-- omit in toc -->

For issues or questions about OpenToken, please visit the [GitHub repository](https://github.com/mattwise-42/OpenToken).
