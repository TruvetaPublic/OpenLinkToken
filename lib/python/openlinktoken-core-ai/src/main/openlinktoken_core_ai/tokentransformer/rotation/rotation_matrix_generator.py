"""
Copyright (c) Truveta. All rights reserved.
"""

import hashlib
import hmac
import math
from typing import List, Optional

import numpy as np

# 2^53 used to convert 53-bit integers to uniform doubles.
_MANTISSA_BITS = 1 << 53
_MANTISSA_SCALE = 1.0 / _MANTISSA_BITS
# Smallest representable uniform value, avoids log(0) in Box-Muller.
_MIN_UNIFORM = _MANTISSA_SCALE
_TWO_PI = 2.0 * math.pi


def generate(
    iv: str,
    rotation_count: int,
    dimension: int,
    hash_dimension: Optional[int] = None,
) -> List[np.ndarray]:
    """Generate a list of deterministic orthogonal rotation matrices from an IV.

    The matrices are derived from the IV using HMAC-SHA256 in counter mode for
    pseudo-random number generation, Box-Muller transform for standard normal
    values, and Modified Gram-Schmidt for orthonormalization. The algorithm is
    fully specified in terms of standard operations and produces bit-exact
    results across Python and Java implementations when ``hash_dimension`` is
    not provided or equals ``dimension``.

    When ``hash_dimension < dimension``, a fast k×N path is used: only the
    first ``hash_dimension`` rows of each raw column are generated, and
    row-based Modified Gram-Schmidt orthonormalizes these k N-dimensional row
    vectors.  This reduces PRNG calls from O(N²) to O(k·N) and Gram-Schmidt
    from O(N³) to O(k²·N), making large embedding dimensions (e.g. 1024)
    practical.  The resulting k×N projection matrices satisfy Q @ Q^T = I_k
    (orthonormal rows) and may be used directly as projection matrices.

    Args:
        iv: Initialization vector string. Same IV always produces the same matrices.
        rotation_count: Number of rotation matrices to generate.
        dimension: Number of columns in each matrix (= size of the input embedding).
        hash_dimension: Number of rows in each output matrix.  When ``None``
            (default) the full ``dimension × dimension`` algorithm is used.
            Pass ``hash_dimension < dimension`` to use the fast k-row path.

    Returns:
        A list of ``rotation_count`` matrices, each a numpy float64 array of
        shape ``(hash_dimension, dimension)`` (fast path) or
        ``(dimension, dimension)`` (full path).  Rows of each matrix are
        orthonormal in R^N.
    """
    key_material = hashlib.sha256(iv.encode("utf-8")).digest()
    k = hash_dimension if hash_dimension is not None and hash_dimension < dimension else dimension
    return [_generate_one(key_material, r, dimension, k) for r in range(rotation_count)]


def _generate_one(key_material: bytes, rotation_index: int, n: int, k: int) -> np.ndarray:
    """Generate a single k×N orthogonal projection matrix.

    When k == n: produces a full NxN proper-rotation matrix (det = +1).
    When k < n: produces a k×N matrix with orthonormal rows (Q @ Q^T = I_k)
    using only the first k rows of each raw random column vector.

    The PRNG counter for element (row r, column j) uses the same counter as
    the full N×N algorithm:  ``counter = (rotation_index * n + j) * pairs_per_col + r//2``
    where ``pairs_per_col = (n + 1) // 2``.

    Args:
        key_material: 32-byte SHA-256 digest of the IV.
        rotation_index: Zero-based matrix index.
        n: Embedding (input) dimension — number of columns.
        k: Output (hash) dimension — number of rows to produce.

    Returns:
        A k×N numpy float64 array with orthonormal rows (Q @ Q^T ≈ I_k).
    """
    pairs_per_col = (n + 1) // 2  # full counter stride (for PRNG parity with Java)
    pairs_needed = (k + 1) // 2  # only need first k rows

    # Build the k×N raw matrix.
    # raw[r, j] = the r-th element of the j-th raw random column vector.
    # Uses the SAME counter as the full N×N algorithm (matches Java).
    raw = np.empty((k, n), dtype=np.float64)
    for col in range(n):
        offset = 0
        for pair in range(pairs_needed):
            counter = (rotation_index * n + col) * pairs_per_col + pair
            h = hmac.new(key_material, counter.to_bytes(8, "big"), hashlib.sha256).digest()
            u1 = max(_extract_uniform(h, 0), _MIN_UNIFORM)
            u2 = _extract_uniform(h, 8)
            r_val = math.sqrt(-2.0 * math.log(u1))
            theta = _TWO_PI * u2
            raw[offset, col] = r_val * math.cos(theta)
            offset += 1
            if offset < k:
                raw[offset, col] = r_val * math.sin(theta)
                offset += 1

    if k == n:
        # Full N×N path: column-based MGS then fix det sign.
        return _column_mgs(raw, n)
    else:
        # Fast k×N path: row-based MGS gives orthonormal rows.
        return _row_mgs(raw, k, n)


def _column_mgs(raw_cols: np.ndarray, n: int) -> np.ndarray:
    """Full N×N Modified Gram-Schmidt on columns, with det=+1 fix."""
    q = np.empty((n, n), dtype=np.float64)
    for j in range(n):
        v = raw_cols[:, j].copy()
        if j > 0:
            proj = np.einsum("ij,i->j", q[:, :j], v)
            v -= np.einsum("ij,j->i", q[:, :j], proj)
        q[:, j] = v / np.linalg.norm(v)
    if np.sign(np.linalg.det(q)) < 0:
        q[:, n - 1] = -q[:, n - 1]
    return q


def _row_mgs(raw: np.ndarray, k: int, n: int) -> np.ndarray:
    """Row-based Modified Gram-Schmidt: orthonormalize k N-dimensional row vectors.

    The input ``raw`` (k×N) has the raw random values; output ``q`` (k×N) has
    orthonormal rows satisfying q @ q^T ≈ I_k.
    """
    q = np.empty((k, n), dtype=np.float64)
    for i in range(k):
        v = raw[i, :].copy()  # N-dimensional row vector
        if i > 0:
            # Project v (length N) onto each previous row (length N)
            proj = q[:i, :] @ v  # shape (i,) — dot products in R^N
            v -= q[:i, :].T @ proj  # subtract aggregate projection
        q[i, :] = v / np.linalg.norm(v)
    return q


def _extract_uniform(h: bytes, offset: int) -> float:
    """Extract 53 bits from 8 bytes of HMAC output and scale to [0, 1).

    Args:
        h: HMAC-SHA256 digest bytes (at least ``offset + 8`` bytes long).
        offset: Byte offset within ``h`` to start reading from.

    Returns:
        A float in the range [0, 1) derived from the 53 most-significant bits
        of the 64-bit big-endian integer at ``h[offset:offset+8]``.
    """
    value = int.from_bytes(h[offset : offset + 8], "big")
    return ((value >> 11) & (_MANTISSA_BITS - 1)) * _MANTISSA_SCALE
