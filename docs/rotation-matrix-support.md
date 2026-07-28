# Rotation Matrix Support for Token Embeddings

## Overview

Rotation-based ML1 token generation is implemented in both the Java and Python
AI libraries. It turns an ML1 ONNX embedding into a comma-separated value stored
under the single `ML1` rule. It does **not** emit separate `ML1-R0`,
`ML1-R1`, … output rows.

For each valid ML1 input, the provider:

1. obtains the raw ONNX embedding;
2. centres, projects, and quantizes the embedding with the configured rotation
   transformer;
3. derives a T1 blocking key when the record has a valid T1 signature;
4. hashes each quantized rotation value with that blocking key; and
5. joins the resulting values with commas for the `ML1` signature.

The Java provider is registered through
`META-INF/services/org.openlinktoken.tokens.InferenceSignatureProvider`. The
Python provider is registered as the `ml1` entry point in
`openlinktoken.inference_providers`.

## Rotation Pipeline

`RotationEmbeddingTransformer` creates `rotationCount` projected values for an
embedding of dimension `N`:

1. Entry 0 is the `[[ -1 ]]` sentinel. It passes through the first
   `hashDimension` values of the centred embedding without rotation.
2. The remaining `rotationCount - 1` entries are deterministic `N × N` proper
   rotation matrices derived from the IV.
3. For each entry, the transformer subtracts the per-dimension bias. For a
   proper rotation, it computes the first `hashDimension` rows of
   `R @ (embedding - bias)`.
4. Each projected vector is quantized to a space-separated string of integer
   bin indices.

Matrices are generated lazily and cached for the lifetime of a transformer.
The ML1 provider also caches its transformer after the first use.

### Quantization

The default quantizer range is `[-5.0, 5.0]` with a bin width of `0.05`.
Each value is clamped to the configured range and assigned with
`int((value - min) // binWidth)`, using Python-compatible floating-point floor
division. With the defaults, the tested bin values are `0` through `199`;
`-5.0` maps to `0`, `0.0` maps to `99`, and `5.0` maps to `199`.

### ML1 Signature Value

The raw quantized value for each projection is a string such as
`"99 100 100 101"`. When a T1 signature can be computed, the provider:

```text
blockingKey = SHA-256(T1-signature)
rotationToken = SHA-256(quantizedValue + blockingKey)
```

It returns the comma-separated `rotationToken` values as the `ML1` signature.
Those values are lowercase 64-character SHA-256 hexadecimal digests. If a T1
signature cannot be computed, the provider returns the un-hashed quantized
values instead.

The Python CLI's batched ML1 path stores this signature directly and does not
apply its normal token-transformer chain to it. Packaging can subsequently wrap
the single `ML1` token for transport.

## Deterministic Matrix Generation

`RotationMatrixGenerator.generate(iv, rotationCount, dimension)` derives each
matrix as follows:

```text
key = SHA-256(UTF-8(iv))

for each rotation index r:
  fill an N × N matrix column-by-column with Box-Muller normal values
  where each pair uses:
    HMAC-SHA256(key, counter as 8-byte big-endian integer)
    counter = (r * N + column) * ceil(N / 2) + pair

  Q, R = Householder QR decomposition of the raw matrix
  normalize columns of Q by sign(diag(R))
  if det(Q) < 0:
    negate the final column of Q
```

The resulting `Q` is orthogonal with determinant `+1`. Java implements the
Householder QR steps directly; Python uses `numpy.linalg.qr` and applies the
same diagonal-sign and determinant corrections. Both implementations use
HMAC-SHA256 counter-mode input, 53-bit uniform values, and Box-Muller
transformation.

Cross-language interoperability compares every matrix element with a tolerance
of `1e-12`. The implementation and tests do not promise bit-for-bit equality
on every platform.

## Configuration

### Runtime Defaults

`RotationConfig` enables rotation by default when the AI module is installed:

| Setting         | Default                |
| --------------- | ---------------------- |
| IV              | `openlinktoken-ml1-v1` |
| Rotation count  | `50`                   |
| Hash dimension  | `4`                    |
| Quantizer range | `[-5.0, 5.0]`          |
| Bin width       | `0.05`                 |
| Dimension bias  | all zeros              |

`rotationCount` is the total number of values returned by the transformer: one
sentinel pass-through value and `rotationCount - 1` proper rotations.

### Exchange Configuration and CLI

The Python `initiate-exchange` command writes `rotationIv`,
`rotationIvEncoding`, `rotationCount`, `binWidth`, and `dimensionBias` into the
encrypted exchange payload. Its defaults are a randomly generated IV,
`rotationCount=30`, `binWidth=0.05`, and a zero-filled `dimensionBias` with
`1024` entries. `--rotation-embedding-dimension` changes that bias length, and
`--rotation-embedding-bias` supplies an explicit JSON bias array.

`tokenize` and `package` apply the exchange rotation settings when an IV is
present. Their `--rotation-iv` option overrides only the IV; the count, bin
width, and bias still come from the exchange payload. If neither an exchange
IV nor an explicit override is supplied, those commands leave the existing
runtime rotation configuration unchanged.

The configured bias must have the same length as the ML1 embedding. No command
adjusts a supplied or generated bias to the model output dimension. The Java
transformer rejects a mismatched bias length; Python's array operation also
requires compatible lengths.

There is no CLI option for hash dimension or for disabling rotation alone.
`tokenize --disable-inferencing` and `package --disable-ml1` disable ML1
inference, rather than only the rotation stage.

For the encrypted payload field definitions, see
[Exchange Config Format](exchange-config-format.md).

## Implementation and Verification

| Area                  | Java                                                                                                                                 | Python                                                                                                                        |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| Matrix generation     | `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation/RotationMatrixGenerator.java`      | `lib/python/openlinktoken-core-ai/src/main/openlinktoken/core/ai/tokentransformer/rotation/rotation_matrix_generator.py`      |
| Projection            | `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation/EmbeddingRotator.java`             | `lib/python/openlinktoken-core-ai/src/main/openlinktoken/core/ai/tokentransformer/rotation/embedding_rotator.py`              |
| Quantization          | `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation/RotationQuantizer.java`            | `lib/python/openlinktoken-core-ai/src/main/openlinktoken/core/ai/tokentransformer/rotation/rotation_quantizer.py`             |
| Composite transformer | `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokentransformer/rotation/RotationEmbeddingTransformer.java` | `lib/python/openlinktoken-core-ai/src/main/openlinktoken/core/ai/tokentransformer/rotation/rotation_embedding_transformer.py` |
| ML1 integration       | `lib/java/openlinktoken-core-ai/src/main/java/org/openlinktoken/core/ai/tokens/OnnxML1SignatureProvider.java`                        | `lib/python/openlinktoken-core-ai/src/main/openlinktoken/core/ai/ml1_signature_provider.py`                                   |

Unit tests cover matrix generation, projection, quantization, transformer
caching, and ML1 blocking-key hashing in both implementations. The Java
`RotationMatrixInteropHarness` and
`tools/interoperability/rotation_matrix_interop_test.py` compare Java and
Python matrices across shared test vectors. See
[Interoperability Tests](../tools/interoperability/README.md) for the command
and prerequisites.
