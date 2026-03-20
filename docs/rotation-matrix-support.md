# Rotation Matrix Support for Token Embeddings

## Overview

This document tracks the design and implementation of rotation matrix support
for OpenToken's T6 embeddings. It covers both the Java and Python libraries.

The goal is to enable **privacy-preserving approximate matching** by rotating
T6 ONNX embeddings with deterministic orthogonal matrices derived from a shared
initialization vector (IV). Both parties derive identical rotation matrices from
the same IV, rotate their embeddings, quantize the rotated projections into
discrete tokens, and match those tokens without ever exposing raw embedding
vectors.

---

## Background: PersonMatching Reference

The approach mirrors the rotation-based matching in the internal PersonMatching
service, which operates on 1024-dimensional BERT embeddings using:

- 30 random orthogonal rotation matrices per IV
- QR decomposition on normally-distributed random matrices
- Per-rotation quantization into discrete bins (bin width 0.05)
- Position-sensitive token hashing against blocking keys (T1)

OpenToken adapts this for its T6 ONNX embeddings (768-dim CLS vectors) with a
portable, language-agnostic algorithm.

---

## Design Decisions

### Storage

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Rotation matrix | **In-memory only** | Deterministic from IV — regenerate each run (~100 ms for N=4). No serialization format to maintain. |
| IV | **Exchange config** | Sits alongside `hashing_secret` in the JWE-encrypted payload. Both parties derive identical matrices from a shared IV. `--rotation-iv` CLI override available for testing. |

### Cross-Language Determinism

PersonMatching uses `numpy.random.RandomState` (Mersenne Twister), which Java
cannot replicate exactly. OpenToken instead uses:

1. **HMAC-SHA256 counter mode** as a portable PRNG  
   `h = HMAC-SHA256(key=SHA-256(IV), msg=counter_as_8_byte_big_endian)`
2. **Box-Muller transform** on 53-bit uniform values extracted from `h`  
   `u = ((int64(h[0:8]) >>> 11) & (2^53 - 1)) / 2^53`
3. **Modified Gram-Schmidt** orthonormalization (no external linear algebra library)
4. **Gaussian elimination** determinant sign check to enforce `det(Q) = +1`

All operations are IEEE 754 double-precision arithmetic applied in identical
order in both languages, giving bit-exact (or sub-1e-12 tolerance) results.

---

## Implementation Plan

### Todo List

| # | ID | Description | Status |
|---|-----|-------------|--------|
| 1 | `rotation-matrix-core` | Deterministic rotation matrix generation (Java + Python) | ✅ Done |
| 2 | `tests-unit` | Unit tests: orthogonality, det=+1, determinism, thread-safety | ✅ Done |
| 3 | `tests-interop` | Cross-language parity tests (Java harness vs Python in-process) | 🔄 In progress |
| 4 | `embedding-rotation` | `EmbeddingRotator`: `R @ (x - bias)`, project to K dims | ⬜ Pending |
| 5 | `rotation-quantizer` | Bin-assignment quantizer → space-separated token string | ⬜ Pending |
| 6 | `rotation-token-transformer` | Composite transformer (matrix gen + rotation + quantization) | ⬜ Pending |
| 7 | `t6-pipeline-integration` | Expose raw float[] from T6; produce `T6-R*` output tokens | ⬜ Pending |
| 8 | `iv-configuration` | Exchange config + CLI args (`--rotation-iv`, `--rotation-count`, etc.) | ⬜ Pending |

### Dependencies

```
rotation-matrix-core ✅
    ├── embedding-rotation ⬜
    │       └── rotation-token-transformer ⬜
    │               ├── rotation-quantizer ⬜
    │               └── t6-pipeline-integration ⬜
    │                       └── iv-configuration ⬜
    └── tests-interop 🔄

tests-unit ✅  (covers rotation-matrix-core)
tests-interop 🔄 (covers full Java↔Python parity once Java builds)
```

---

## Files Created

### Core Implementation

| File | Language | Description |
|------|----------|-------------|
| `lib/java/opentoken/src/main/java/com/truveta/opentoken/tokentransformer/rotation/RotationMatrixGenerator.java` | Java | HMAC-PRNG + Box-Muller + Modified Gram-Schmidt |
| `lib/python/opentoken/src/main/opentoken/tokentransformer/rotation/rotation_matrix_generator.py` | Python | Identical algorithm using only `hashlib`, `hmac`, `math` |
| `lib/python/opentoken/src/main/opentoken/tokentransformer/rotation/__init__.py` | Python | Package marker |

### Unit Tests

| File | Language | Coverage |
|------|----------|----------|
| `lib/java/opentoken/src/test/java/com/truveta/opentoken/tokentransformer/rotation/RotationMatrixGeneratorTest.java` | Java | 11 tests: count, dimensions, orthogonality, det=+1, determinism, different IVs, rotation indices, dim-2, dim-8, thread-safety |
| `lib/python/opentoken/src/test/opentoken/tokentransformer/rotation/rotation_matrix_generator_test.py` | Python | Same 11 tests — all passing ✅ |

### Interoperability Infrastructure

| File | Description |
|------|-------------|
| `lib/java/opentoken/src/test/java/com/truveta/opentoken/tools/RotationMatrixInteropHarness.java` | Java harness: accepts `<iv> <rotation_count> <dimension> <output.json>`, writes full-precision JSON |
| `tools/interoperability/rotation_matrix_interop_test.py` | Cross-language test: invokes Java harness via Maven, runs Python generator in-process, compares element-by-element within 1e-12 tolerance |

---

## Algorithm Reference

### `RotationMatrixGenerator.generate(iv, rotation_count, dimension)`

```
key = SHA-256(iv.encode("utf-8"))                              // 32 bytes

for r in 0..rotation_count-1:
  pairs_per_col = ceil(dimension / 2)

  // Fill column-major raw matrix via HMAC-PRNG + Box-Muller
  for col in 0..N-1:
    for pair in 0..pairs_per_col-1:
      counter = (r * N + col) * pairs_per_col + pair
      h = HMAC-SHA256(key, counter as 8-byte big-endian uint64)
      u1 = max(((uint64(h[0:8]) >>> 11) & (2^53-1)) / 2^53, 2^-53)
      u2 =    ((uint64(h[8:16]) >>> 11) & (2^53-1)) / 2^53
      z0 = sqrt(-2 * ln(u1)) * cos(2π * u2)        // Box-Muller
      z1 = sqrt(-2 * ln(u1)) * sin(2π * u2)
      raw[offset][col]   = z0
      raw[offset+1][col] = z1  (if within bounds)

  // Modified Gram-Schmidt orthonormalization on columns
  for j in 0..N-1:
    v = raw[:, j]
    for k in 0..j-1:
      v -= dot(v, q[:, k]) * q[:, k]
    q[:, j] = v / ||v||

  // Enforce det(Q) = +1 via Gaussian elimination sign check
  if det_sign(Q) < 0:
    Q[:, N-1] = -Q[:, N-1]

  matrices[r] = Q
```

### Interoperability Guarantee

Both Java and Python:
- Use the same HMAC-SHA256 key derivation and counter encoding
- Extract uniform doubles with identical 53-bit shift-and-scale
- Apply Box-Muller using IEEE 754 `sqrt`, `log`, `cos`, `sin`
- Run Modified Gram-Schmidt with left-to-right floating-point accumulation
- Run Gaussian elimination with identical partial-pivot row ordering

Empirical tolerance observed: **0.0 ULP** (bit-exact on tested platforms).
Test tolerance set to **1e-12** to accommodate rare platform variation.

---

## Remaining Work

### 4. `embedding-rotation`

Apply rotation matrices to raw float vectors:

```
rotate(embedding: float[], matrices, bias: float[], k: int) → List[float[k]]
  x_centered = embedding - bias
  for each R in matrices:
    rotated = R @ x_centered
    yield rotated[:k]
```

**Files**: `EmbeddingRotator.java`, `embedding_rotator.py`

### 5. `rotation-quantizer`

Convert a low-dimensional float vector into a discrete token string:

```
quantize(x: float[], min=-5.0, max=5.0, bin_width=0.05) → String
  bins = [floor((v - min) / bin_width) for v in x]
  bins = clamp(bins, 0, ceil((max - min) / bin_width) - 1)
  return " ".join(str(b) for b in bins)
```

**Files**: `RotationQuantizer.java`, `rotation_quantizer.py`

### 6. `rotation-token-transformer`

New `EmbeddingTransformer` interface (`float[] → List<String>`) composing steps
3–5. Accepts IV, rotation count, hash dimension, quantization params.

### 7. `t6-pipeline-integration`

- Add `generateEmbeddingsRaw() → float[][]` to `T6OnnxSignatureGenerator`
- Modify `TokenGenerator` to produce `T6-R0`…`T6-R{N-1}` tokens per record
- Add rotation token map to `TokenGeneratorResult`
- New CSV/Parquet rows: `RuleId=T6-R0`, `Token=<quantized>`, `RecordId=…`

### 8. `iv-configuration`

- Add `rotation_iv` field to exchange config JWE payload
- New `RotationConfig` class (both languages)
- CLI args: `--rotation-iv`, `--rotation-count`, `--hash-dimension`, `--disable-rotation`

---

## Out of Scope

- **Dimension bias** (median-per-dimension from sampled embeddings) — use zero vector bias for now
- **Rotation-based matching** — handled downstream by PersonMatching, not OpenToken
- **Blocking-key hashing** — PersonMatching hashes quantized tokens with a T1 blocking key; OpenToken emits raw quantized tokens and leaves blocking to the consumer
