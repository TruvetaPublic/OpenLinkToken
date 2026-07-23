# SPDX-License-Identifier: MIT

import hashlib
import hmac
import math
from typing import List

import numpy as np

# 2^53 used to convert 53-bit integers to uniform doubles.
_MANTISSA_BITS = 1 << 53
_MANTISSA_SCALE = 1.0 / _MANTISSA_BITS
# Smallest representable uniform value, avoids log(0) in Box-Muller.
_MIN_UNIFORM = _MANTISSA_SCALE
_TWO_PI = 2.0 * math.pi


def generate(iv: str, rotation_count: int, dimension: int) -> List[np.ndarray]:
    """Generate a list of deterministic orthogonal rotation matrices from an IV.

    The matrices are derived from the IV using HMAC-SHA256 in counter mode for
    pseudo-random number generation, Box-Muller transform for standard normal
    values, and QR decomposition for orthonormalization. The algorithm is
    fully specified in terms of standard operations and produces bit-exact
    results across Python and Java implementations.

    Args:
        iv: Initialization vector string. Same IV always produces the same matrices.
        rotation_count: Number of rotation matrices to generate.
        dimension: Number of rows and columns in each matrix.

    Returns:
        A list of ``rotation_count`` full ``dimension x dimension`` numpy float64
        proper-rotation matrices.
    """
    key_material = hashlib.sha256(iv.encode("utf-8")).digest()
    return [_generate_one(key_material, r, dimension) for r in range(rotation_count)]


def _generate_one(key_material: bytes, rotation_index: int, n: int) -> np.ndarray:
    """Generate a single ``n x n`` proper-rotation matrix."""
    pairs_per_col = (n + 1) // 2
    raw = np.empty((n, n), dtype=np.float64)
    for col in range(n):
        offset = 0
        for pair in range(pairs_per_col):
            counter = (rotation_index * n + col) * pairs_per_col + pair
            h = hmac.new(key_material, counter.to_bytes(8, "big"), hashlib.sha256).digest()
            u1 = max(_extract_uniform(h, 0), _MIN_UNIFORM)
            u2 = _extract_uniform(h, 8)
            r_val = math.sqrt(-2.0 * math.log(u1))
            theta = _TWO_PI * u2
            raw[offset, col] = r_val * math.cos(theta)
            offset += 1
            if offset < n:
                raw[offset, col] = r_val * math.sin(theta)
                offset += 1

    q, r = np.linalg.qr(raw)
    q = q * np.sign(np.diag(r))[np.newaxis, :]
    if np.sign(np.linalg.det(q)) < 0:
        q[:, n - 1] = -q[:, n - 1]
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
