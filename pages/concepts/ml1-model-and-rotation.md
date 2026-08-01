---
layout: default
---

# ML1 Model and Rotation

ML1 is the model-based matching token. It is enabled by default when the AI
module is available. ML1 has four distinct stages:

1. Normalize five person attributes and serialize them as JSON.
2. Tokenize the JSON and run the bundled ONNX model to obtain a CLS embedding.
3. Project, rotate, and quantize the embedding.
4. Hash each quantized projection into one `ML1` signature.

Rotation and quantization are transformations, not de-identification by
themselves. The security boundary is the final hashing step, and optional
transport encryption is applied after token generation.

## Input Contract

ML1 requires all five fields below. The provider validates and normalizes each
field before inference, then serializes the fields in this order:

| JSON field   | Source attribute | Role              |
| ------------ | ---------------- | ----------------- |
| `PostalCode` | Postal code      | Geographic signal |
| `Birthdate`  | Birth date       | Date signal       |
| `GivenName`  | First name       | Given-name signal |
| `Surname`    | Last name        | Surname signal    |
| `Gender`     | Sex              | Gender signal     |

The exact JSON field order is part of the cross-language contract. Java and
Python produce the same JSON representation for the same normalized values.
For example:

```json
{
  "PostalCode": "90210",
  "Birthdate": "1988-03-22",
  "GivenName": "MARIA",
  "Surname": "GARCIA",
  "Gender": "F"
}
```

If a required field is missing, invalid, or empty after normalization, ML1
does not produce a signature for that record.

## ONNX Model and Embedding

The default assets are:

```text
Model:     resources/inferencing/ml1/model.onnx
Tokenizer: resources/inferencing/ml1/tokenizer.json
```

The tokenizer converts each JSON string into integer tensors. The bundled
model accepts:

| Tensor           | Type    | Shape                      | Availability    |
| ---------------- | ------- | -------------------------- | --------------- |
| `input_ids`      | `int64` | `[batch, sequence_length]` | Required        |
| `attention_mask` | `int64` | `[batch, sequence_length]` | Required        |
| `token_type_ids` | `int64` | `[batch, sequence_length]` | Model-dependent |
| `position_ids`   | `int64` | `[batch, sequence_length]` | Model-dependent |

Sequence length is dynamically padded to the longest encoded row in a batch
and capped at `128`. The bundled model exposes:

```text
last_hidden_state: [batch, sequence_length, 1024]
pooler_output:     [batch, 1024]
```

The implementation uses the first token (CLS) from a three-dimensional output,
or the two-dimensional output directly. The resulting embedding has 1024
float32 values.

The model path, tokenizer path, maximum sequence length, batch size, and
thread count can be configured through the ML1 runtime configuration. See the
[CLI reference](../reference/cli.md) for command-line options.

## Rotation and Quantization

The default transformer returns 50 projections for each 1024-value embedding:

1. Projection 0 is the `[-1]` sentinel. It passes through the first four
   values after the bias is subtracted.
2. Projections 1 through 49 use deterministic 1024-by-1024 proper rotation
   matrices derived from the rotation IV.
3. Every projection keeps only its first four values.
4. Each value is clamped to `[-5.0, 5.0]` and quantized with a bin width of
   `0.05`.

The default quantizer therefore has 200 bins. With the implementation's
Python-compatible floor division, `-5.0` maps to bin `0`, `0.0` maps to bin
`99`, and `5.0` maps to bin `199`. A projection is represented as a
space-separated string such as:

```text
99 100 100 101
```

## Generating an Embedding Bias

The embedding bias is the component-wise median of a sample of valid model
embeddings. ML1 subtracts this vector before rotation, so its length must match
the model embedding dimension (1024 for the bundled model).

The repository provides separate scripts for generating the unrotated model
embeddings and calculating the bias:

- [`tools/ml1/generate_embeddings.py`](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/tools/ml1/generate_embeddings.py)
  loads `model.onnx` and `tokenizer.json` directly, normalizes the required
  person fields, and writes raw CLS embeddings to a NumPy `.npy` file.
- [`tools/ml1/calculate_embedding_bias.py`](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/tools/ml1/calculate_embedding_bias.py)
  calculates the component-wise median and writes a flat JSON bias file.

The embedding generator accepts one JSON object per line with the fields
required by ML1:

```json
{
  "PostalCode": "90210",
  "BirthDate": "1988-03-22",
  "FirstName": "Maria",
  "LastName": "Garcia",
  "Sex": "F"
}
```

Generate the raw embeddings using the bundled model and tokenizer:

```bash
python tools/ml1/generate_embeddings.py \
  --input records.jsonl \
  --output embeddings.npy
```

The script defaults to
`resources/inferencing/ml1/model.onnx` and
`resources/inferencing/ml1/tokenizer.json`. Use `--model` and `--tokenizer` to
reference another matched model/tokenizer pair. The output contains raw,
unrotated, unquantized 1024-dimensional CLS embeddings.

Calculate the bias from those embeddings:

```bash
python tools/ml1/calculate_embedding_bias.py \
  --input embeddings.npy \
  --output bias.json
```

The bias script validates the embedding dimension, samples up to 100,000
vectors by default, and writes a flat JSON array. Use `--sample-size` and
`--seed` to control sampling. The resulting `bias.json` can be supplied with
[`--rotation-embedding-bias`](../reference/cli.md#initiate-exchange).

PersonMatching's `generate_rotation_matrices` mode performs the same
calculation from the `PersonMatch-Embeddings` table: it keeps non-null vectors
with the expected dimension, samples up to 100,000 rows by default, computes
the component-wise median, and writes `dimension_bias.json` alongside the
rotation artifacts. A bias is not a secret and does not provide
de-identification by itself; it is a centering parameter used by the rotation
pipeline.

### Deterministic Rotation Matrices

For each proper rotation, the matrix generator performs the following steps:

```text
key = SHA-256(UTF-8(iv))
HMAC-SHA256 counter stream -> Box-Muller normal samples
Householder QR in Java / NumPy QR in Python
sign(diag(R)) normalization
determinant +1 correction
```

The resulting matrices are orthogonal and have determinant `+1`. The Java and
Python implementations use the same HMAC counter inputs and numerical
corrections. Interoperability compares matrix elements with a tolerance of
`1e-12`; it does not promise bit-for-bit equality on every platform.

The default runtime configuration is:

| Setting             | Default                |
| ------------------- | ---------------------- |
| Rotation IV         | `openlinktoken-ml1-v1` |
| Rotation count      | `50`                   |
| Retained dimensions | `4`                    |
| Quantizer range     | `[-5.0, 5.0]`          |
| Bin width           | `0.05`                 |
| Dimension bias      | All zeros              |

An exchange configuration can carry a different rotation IV, count, bin width,
and dimension bias. A configured bias must have the same length as the model
embedding. See [Exchange Config Format](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/docs/exchange-config-format.md)
and the [rotation implementation reference](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/docs/rotation-matrix-support.md).

## ML1 Signature

When the normalized T1 fields are available, the provider derives a blocking
key and hashes every quantized projection:

```text
t1Signature = LASTNAME|FIRSTINITIAL|SEX|BIRTHDATE
blockingKey = SHA-256(t1Signature)
rotationToken = SHA-256(quantizedValue + blockingKey)
ML1 = rotationToken_0,rotationToken_1,...,rotationToken_49
```

The concatenation has no delimiter between `quantizedValue` and
`blockingKey`. Each `rotationToken` is a lowercase 64-character SHA-256
hexadecimal digest. The output is one comma-separated `ML1` signature; ML1
does not emit separate `ML1-R0`, `ML1-R1`, and similar rows.

If the T1 signature cannot be computed, the provider emits the canonical blank
ML1 token. It never emits unprotected quantized rotation values as the ML1
token.

The per-projection construction uses SHA-256 and a T1-derived blocking value.
That blocking value is deterministic and is not an independent secret. ML1's
rotation signature is therefore distinct from the HMAC-SHA256 pipeline used by
the standard T1-T5 tokens. Packaging can subsequently wrap the ML1 signature
for transport encryption.

If rotation is disabled through the library configuration, ML1 falls back to a
serialized raw embedding signature. That output is not a de-identified token
and should not be treated as one for production exchange.

## Security Boundaries and Limitations

Rotation preserves vector geometry up to a deterministic change of basis.
Quantization reduces precision but does not make an embedding cryptographically
irreversible. Neither operation, by itself, removes information about the
input fields.

Even with rotation enabled, deterministic ML1 signatures require appropriate
controls:

- Protect exchange configuration and any transport-encryption keys.
- Limit access to token outputs and the systems that generate them.
- Account for frequency analysis and auxiliary-data attacks.
- Do not treat a token as safe after the underlying secrets or trusted runtime
  have been compromised.

Validate ML1 matching quality and privacy risk against the intended population.
This repository does not establish universal precision, recall, or
re-identification guarantees.

## Model Card Availability

This repository documents the model's runtime tensor contract, but does not
provide an authoritative model card for:

- model architecture beyond the observed ONNX input/output contract;
- model provenance or version lineage;
- training data, training objective, or fine-tuning procedure;
- matching benchmarks or population-specific quality metrics; or
- fairness, subgroup performance, or bias evaluation.

Those facts must come from the model owner or a release-specific model card.
They should not be inferred from the embedding dimension or the rotation
implementation.

## Implementation and Verification

- [Matching Model](matching-model.md) - High-level matching strategy
- [CLI Reference](../reference/cli.md) - ML1 and rotation options
- [Rotation Matrix Support](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/docs/rotation-matrix-support.md)
  - Implementation-level rotation and quantization details
- [Interoperability Tests](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/tools/interoperability/README.md)
  - Java/Python matrix and ML1 parity checks
- [Java ML1 provider](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokens/ML1OnnxSignatureProvider.java)
- [Python ML1 provider](https://github.com/TruvetaPublic/OpenLinkToken/blob/main/lib/python/openlinktoken-core-ai/src/main/openlinktoken/core/ai/tokens/ml1_onnx_signature_provider.py)
