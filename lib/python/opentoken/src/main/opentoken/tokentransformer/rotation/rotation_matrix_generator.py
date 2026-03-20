"""
Copyright (c) Truveta. All rights reserved.
"""

import hashlib
import hmac
import math
from typing import List

# 2^53 used to convert 53-bit integers to uniform doubles.
_MANTISSA_BITS = 1 << 53
_MANTISSA_SCALE = 1.0 / _MANTISSA_BITS
# Smallest representable uniform value, avoids log(0) in Box-Muller.
_MIN_UNIFORM = _MANTISSA_SCALE
_TWO_PI = 2.0 * math.pi


def generate(iv: str, rotation_count: int, dimension: int) -> List[List[List[float]]]:
    """Generate a list of deterministic orthogonal rotation matrices from an IV.

    The matrices are derived from the IV using HMAC-SHA256 in counter mode for
    pseudo-random number generation, Box-Muller transform for standard normal
    values, and Modified Gram-Schmidt for orthonormalization. The algorithm is
    fully specified in terms of standard operations and produces bit-exact
    results across Python and Java implementations.

    Args:
        iv: Initialization vector string. Same IV always produces the same matrices.
        rotation_count: Number of rotation matrices to generate.
        dimension: Number of rows and columns in each matrix (NxN).

    Returns:
        A list of ``rotation_count`` matrices, each represented as a
        ``dimension x dimension`` list-of-lists in row-major order, i.e.
        ``result[r][row][col]`` is the element at (row, col) of matrix r.
        Each matrix Q is an orthogonal proper-rotation matrix (Q @ Q^T = I,
        det(Q) = +1).
    """
    key_material = hashlib.sha256(iv.encode("utf-8")).digest()
    return [_generate_one(key_material, r, dimension) for r in range(rotation_count)]


def _generate_one(key_material: bytes, rotation_index: int, n: int) -> List[List[float]]:
    """Generate a single NxN orthogonal proper-rotation matrix.

    Fills the matrix column-by-column using paired Box-Muller samples drawn
    from an HMAC-SHA256 counter-mode PRNG, then orthonormalizes the columns
    via Modified Gram-Schmidt, and finally flips the last column sign if
    needed to guarantee det(Q) = +1.

    Args:
        key_material: 32-byte SHA-256 digest of the IV; used as the HMAC key.
        rotation_index: Zero-based index of this matrix within the batch.
            Incorporated into the HMAC counter so each matrix draws from a
            distinct, non-overlapping region of the PRNG stream.
        n: Matrix dimension; produces an NxN matrix.

    Returns:
        An NxN row-major list-of-lists ``q`` where ``q[row][col]`` is the
        element at (row, col).  The matrix satisfies Q @ Q^T = I and
        det(Q) = +1.
    """
    pairs_per_col = (n + 1) // 2

    # Build row-major raw matrix: raw[row][col] filled column-by-column via Box-Muller.
    raw = [[0.0] * n for _ in range(n)]
    for col in range(n):
        offset = 0
        for pair in range(pairs_per_col):
            counter = (rotation_index * n + col) * pairs_per_col + pair
            h = hmac.new(key_material, counter.to_bytes(8, "big"), hashlib.sha256).digest()
            u1 = max(_extract_uniform(h, 0), _MIN_UNIFORM)
            u2 = _extract_uniform(h, 8)
            r_val = math.sqrt(-2.0 * math.log(u1))
            theta = _TWO_PI * u2
            z0 = r_val * math.cos(theta)
            z1 = r_val * math.sin(theta)
            raw[offset][col] = z0
            offset += 1
            if offset < n:
                raw[offset][col] = z1
                offset += 1

    # Modified Gram-Schmidt orthonormalization on columns.
    # q[row][col] accumulates orthonormal column vectors.
    q = [[0.0] * n for _ in range(n)]
    for j in range(n):
        v = [raw[row][j] for row in range(n)]
        for k in range(j):
            proj = sum(v[row] * q[row][k] for row in range(n))
            v = [v[row] - proj * q[row][k] for row in range(n)]
        norm = math.sqrt(sum(x * x for x in v))
        for row in range(n):
            q[row][j] = v[row] / norm

    # Ensure det(Q) = +1 (proper rotation, no reflection).
    if _compute_det_sign(q, n) < 0:
        for row in range(n):
            q[row][n - 1] = -q[row][n - 1]

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


def _compute_det_sign(q: List[List[float]], n: int) -> int:
    """Return the sign of det(Q) via Gaussian elimination with partial pivoting.

    Args:
        q: NxN row-major matrix as a list-of-lists.
        n: Matrix dimension.

    Returns:
        ``+1`` if det(Q) > 0, ``-1`` if det(Q) < 0.
    """
    a = [row[:] for row in q]
    sign = 1
    for col in range(n):
        max_row = col
        for row in range(col + 1, n):
            if abs(a[row][col]) > abs(a[max_row][col]):
                max_row = row
        if max_row != col:
            a[col], a[max_row] = a[max_row], a[col]
            sign = -sign
        for row in range(col + 1, n):
            factor = a[row][col] / a[col][col]
            for j in range(col, n):
                a[row][j] -= factor * a[col][j]
    for i in range(n):
        if a[i][i] < 0:
            sign = -sign
    return sign
