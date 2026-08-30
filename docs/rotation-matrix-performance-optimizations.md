# Rotation Matrix Performance Optimizations

This document summarizes the rotation-matrix optimizations implemented for
ML1 token generation. It is intended as a porting guide for another project
that generates deterministic rotation matrices from embedding vectors.

## Scope and constraints

The optimization targets a pipeline with these characteristics:

- An embedding has dimension `N` (the bundled ML1 model uses `N = 1024`).
- A deterministic rotation matrix is derived from an initialization vector (IV).
- The transformer emits only the first `k` projected values from each matrix
  (`k = 4` by default).
- The first projection is a sentinel pass-through projection.
- The remaining projections are quantized and optionally hashed into tokens.
- Token output must remain deterministic and compatible with another
  implementation, including the Java implementation.

The changes do not alter the IV, HMAC counter scheme, QR algorithm, quantizer,
hashing, or token format.

## Main findings

The original implementation had two avoidable costs:

1. It generated and retained complete `N x N` matrices even though only their
   first `k` rows were used.
2. It regenerated the same deterministic matrices every time a new process
   started.

For `N = 1024`, `49` actual rotations, and `k = 4`:

```text
Full retained matrices: 49 x 1024 x 1024 x 8 bytes = about 411 MB
Retained leading rows: 49 x 4 x 1024 x 8 bytes    = about 1.6 MB
```

The retained representation is approximately 256 times smaller.

## Changes implemented

### 1. Generate only the rows consumed by projection

The matrix generator now accepts an optional leading-row count:

```python
generate(iv, rotation_count, dimension, rows=hash_dimension)
```

The QR decomposition still runs on the full raw matrix. This is required
because the leading rows of the orthogonal factor depend on the complete QR
decomposition. After QR and the existing sign/determinant normalization, the
generator returns a copy of `Q[:rows, :]`.

Returning a copy is important: returning a view would keep the full `N x N`
matrix alive through NumPy's base-array reference.

The default `rows=None` behavior remains available for callers that require
complete matrices.

### 2. Preserve the deterministic random stream while reducing generation cost

The original scalar implementation performed one `hmac.new()` call for every
Box-Muller pair. The optimized implementation:

1. Builds the HMAC inner and outer padded SHA-256 states once per matrix.
2. Copies those prepared states for each counter value.
3. Writes the first 16 digest bytes for each pair into a byte buffer.
4. Converts the digest buffer to big-endian 64-bit words.
5. Vectorizes the 53-bit uniform extraction and Box-Muller calculations with
   NumPy.
6. Builds the raw matrix in the same column-major logical order as before.
7. Runs the same QR decomposition and sign corrections.

The counter remains:

```text
counter = (rotation_index * N + column) * ceil(N / 2) + pair
```

The HMAC key remains `SHA-256(UTF-8(iv))`. The generated digest bytes and QR
input were verified against the previous scalar implementation across even
and odd dimensions.

### 3. Cache deterministic projected rows across processes

The composite transformer now loads or creates a cache containing only the
projected matrix rows. The cache entry is keyed by:

- cache format version;
- an algorithm fingerprint derived from the generator implementation;
- NumPy version;
- IV;
- rotation count;
- embedding dimension; and
- hash dimension.

The default cache location is:

```text
~/.openlinktoken/rotation-matrices/
```

The cache root can be overridden for tests or controlled deployments with:

```text
OLT_ROTATION_CACHE_DIR
```

Each cache file is an `.npz` archive containing:

- the projected matrices as a contiguous `float64` array; and
- a SHA-256 digest of the canonical matrix bytes.

Cache loading performs these checks:

- archive keys exist;
- array type, shape, and dtype are expected;
- all matrix values are finite;
- the loaded array is normalized to contiguous layout; and
- the stored digest matches the loaded matrix bytes.

Cache writes are safe for concurrent processes:

1. create the cache directories with private permissions;
2. write to a temporary file in the cache directory;
3. flush and `fsync` the file;
4. atomically replace the destination with `os.replace`.

Cache failures are not tokenization failures. If the home directory is
unavailable, a cache file is corrupt, or the cache cannot be written, the
runtime logs a warning and regenerates the matrices in memory.

Do not use pickle-based cache formats. The implementation loads NumPy data
with `allow_pickle=False`.

### 4. Remove unnecessary final-batch padding

The ONNX model already supports dynamic batch dimensions. The previous code
padded a final partial batch to the configured batch size, causing inference
work for rows that did not exist.

The final batch now contains only real rows:

```text
Before: requestedSize=36, inferenceSize=64
After:  requestedSize=36, inferenceSize=36
```

Keep fixed-shape padding only if the target runtime truly requires it. Verify
the model input shapes and provider behavior before removing padding in
another project.

### 5. Avoid redundant raw embedding serialization

When rotation is enabled, the provider consumes the embeddings to produce
rotated tokens and does not use the raw serialized embedding signature. The
batched inference helper therefore accepts an `include_raw_signatures` flag
and skips that work for rotated batches.

When raw signatures are required, serialization uses:

```python
np.asarray(embedding, dtype=">f4").tobytes().hex()
```

This preserves the existing big-endian float32 byte contract while avoiding a
Python loop and repeated `struct` conversions.

The provider retains a fallback that serializes the embedding if rotation
cannot be used.

## Data flow after optimization

```text
person rows
    |
    v
batched tokenizer and ONNX inference
    |
    v
float32 embeddings
    |
    +--> raw float32 hex signature (only when requested)
    |
    v
load projected rotation rows from cache
    |       \
    |        \ cache miss: generate full QR one matrix at a time,
    |                  retain only Q[:k, :], write validated cache
    v
sentinel pass-through + projected matrix rows
    |
    v
quantization
    |
    v
optional blocking-key hashing
    |
    v
deterministic token output
```

## Correctness and parity safeguards

Before porting the changes, establish a baseline output artifact from the
unmodified implementation. Compare deterministic tokenized output, not
encrypted transport bytes.

Required checks:

1. Compare the raw generated matrix values against a scalar reference for:
   - at least one even dimension;
   - at least one odd dimension;
   - multiple IVs; and
   - multiple rotation indices.
2. Verify the projected-row result equals the leading rows of the full result.
3. Verify sentinel-only and zero-actual-rotation behavior if the public API
   permits those configurations.
4. Verify cache miss, cache hit, corrupt cache, wrong shape, wrong dtype, and
   unavailable-home behavior.
5. Compare complete deterministic tokenized output byte-for-byte.
6. Run the other language implementation's rotation and interoperability
   tests.
7. Confirm that the final batch is not padded only when dynamic shapes are
   supported by every required execution provider.

Do not compare package ZIP bytes as the primary parity test. Encryption,
timestamps, archive names, or metadata can make otherwise equivalent package
outputs differ. Compare the deterministic tokenized records and separately
validate package row counts and rule IDs.

## Measurements from the implementation

The benchmark used the same 2,500-record input and exchange configuration
before and after the changes:

| Measurement                         |       Before |        After |
| ----------------------------------- | -----------: | -----------: |
| 2,500-record tokenization           |     295.71 s |     222.64 s |
| Rotation generation for 10 matrices |     11.534 s |      4.659 s |
| Retained 49-matrix memory           | about 411 MB | about 1.6 MB |

Observed improvements:

- 2,500-record end-to-end tokenization: 73.07 seconds, or 24.71 percent,
  faster in the measured runs.
- Matrix generation: 2.48 times faster in a scalar-versus-optimized
  comparison.
- Retained rotation-matrix memory: approximately 256 times smaller.
- A 100-record package run saved 45.70 seconds between cold-cache and
  warm-cache runs.

The end-to-end values are host-dependent. Sustained ONNX CPU execution caused
thermal/resource throttling in some long runs, so use repeated measurements on
the target hardware and report cold-cache and warm-cache values separately.

## Porting checklist

- [ ] Capture a deterministic pre-change tokenized output.
- [ ] Identify the actual projected dimension `k`.
- [ ] Confirm the sentinel and rotation-count contract.
- [ ] Add an optional leading-row API to the matrix generator.
- [ ] Preserve the existing HMAC counter and QR/sign normalization contract.
- [ ] Verify optimized matrix values against a scalar reference.
- [ ] Add a cache format with an algorithm-aware key.
- [ ] Store a digest and reject corrupted cache content.
- [ ] Use a safe, atomic cache write.
- [ ] Keep cache permissions private and avoid pickle.
- [ ] Use the project's existing private-home/directory helper where available.
- [ ] Make cache failure fall back to in-memory generation.
- [ ] Isolate cache paths in tests.
- [ ] Test corrupt, missing, unwritable, and unavailable-home cache cases.
- [ ] Remove final-batch padding only after verifying dynamic provider support.
- [ ] Skip unused raw embedding serialization in rotated batches.
- [ ] Compare complete deterministic output after the change.
- [ ] Run all relevant language/interoperability tests.
- [ ] Measure cold-start, warm-cache, and end-to-end performance separately.
