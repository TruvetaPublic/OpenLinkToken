---
layout: default
---

# PPRL Demo Walkthrough (What Data Gets Exchanged)

This walkthrough explains the **data flow and artifacts** produced by the demo under `demos/pprl-superhero-example/`, with a focus on what gets **generated locally**, what gets **shared between organizations**, and what gets produced during **overlap analysis**.

If you want the full, runnable demo guide, see:

- [Demo notebook (PPRL_Superhero_Demo.ipynb)](https://github.com/TruvetaPublic/OpenToken/blob/main/demos/pprl-superhero-example/PPRL_Superhero_Demo.ipynb)
- [Demo README](https://github.com/TruvetaPublic/OpenToken/blob/main/demos/pprl-superhero-example/README.md)

## Scenario and roles

The demo models two organizations:

- **Hospital**: generates tokens from its raw dataset.
- **Pharmacy**: generates tokens from its raw dataset.

Then (in the demo) the **hospital runs the overlap analysis** after receiving the pharmacy’s token file.

## What gets shared vs. what does not

**Shared (in this demo):**

- Encrypted token files (CSV)
- Tokenization metadata (JSON)
- Match results (CSV of RecordId pairs)

**Not shared:**

- Raw identifiers (names, birth date, SSN, postal code)
- Secrets (hashing secret and encryption key)

> Note: The demo uses example secrets for convenience. Real deployments must use proper key management and access controls.

## Step-by-step: inputs and outputs

### Step 1 — Generate synthetic datasets

The demo creates two CSV datasets locally:

- `demos/pprl-superhero-example/datasets/hospital_superhero_data.csv`
- `demos/pprl-superhero-example/datasets/pharmacy_superhero_data.csv`

These include person-identifier columns used for tokenization (e.g., first/last name, sex, birth date, SSN, postal code) plus organization-specific columns.

### Step 2 — Tokenize each dataset (separately)

Each party runs OpenToken tokenization locally (demo scripts use the Python CLI):

- Hospital script: `demos/pprl-superhero-example/scripts/tokenize_hospital.sh`
- Pharmacy script: `demos/pprl-superhero-example/scripts/tokenize_pharmacy.sh`

Each script produces:

- `demos/pprl-superhero-example/outputs/<org>_tokens.csv`
- `demos/pprl-superhero-example/outputs/<org>_tokens.metadata.json`

#### What is inside `*_tokens.csv`

Token outputs are in a long/row-oriented form:

- **`RecordId`**: the record identifier from the source file
- **`RuleId`**: which token rule produced the token (T1–T5)
- **`Token`**: the encrypted token string

Conceptually, tokenization is:

1. Normalize and validate attributes
2. Compute a deterministic HMAC-based fingerprint for each token rule
3. Encrypt that fingerprint with AES-GCM (random IV)

Because encryption uses a random IV, the encrypted `Token` values are intentionally **not stable across runs**, even for identical inputs.

#### What is inside `*_tokens.metadata.json`

The metadata file contains run statistics and audit information such as counts of processed records and hashes of secrets (not the secrets themselves).

See [Metadata Format](../reference/metadata-format.md).

### Step 3 — Exchange encrypted tokens (the “shared artifact”)

At this point, each party can share:

- `outputs/hospital_tokens.csv` + `outputs/hospital_tokens.metadata.json`
- `outputs/pharmacy_tokens.csv` + `outputs/pharmacy_tokens.metadata.json`

This is the core idea: share **tokens** rather than raw identifiers.

### Step 4 — Overlap analysis (decrypt → compare → match)

To find overlaps across datasets that were tokenized independently, the demo runs an analysis step:

- Script: `demos/pprl-superhero-example/scripts/analyze_overlap.py`

This script:

1. Loads each token CSV
2. **Decrypts** each encrypted token to recover the underlying deterministic fingerprint
3. Compares fingerprints across records
4. Writes match results

Output:

- `demos/pprl-superhero-example/outputs/matching_records.csv`

The demo’s default match policy is strict (all 5 of T1–T5 must match), but it also supports relaxing the threshold.

## What a reader should take away

- The exchange unit is **encrypted tokens + metadata**, not raw PII.
- The “matching” step works by decrypting tokens back to a **one-way fingerprint** that can be compared for equality.
- Operationally, you should treat the overlap analysis environment as **trusted**, with strong controls around key access and outputs.

## Next steps

- See [Sharing Tokenized Data](sharing-tokenized-data.md) for operational guidance.
- See [Decrypting Tokens](decrypting-tokens.md) for key-handling considerations.
- If you’re new, start at [Quickstarts](../quickstarts/index.md).
