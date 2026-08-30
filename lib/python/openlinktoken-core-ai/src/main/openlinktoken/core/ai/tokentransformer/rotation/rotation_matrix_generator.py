# SPDX-License-Identifier: MIT

import hashlib
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
    rows: Optional[int] = None,
) -> List[np.ndarray]:
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
        rows: Optional number of leading rows to retain from each matrix.

    Returns:
        A list of ``rotation_count`` numpy float64 proper-rotation matrices.
        When ``rows`` is provided, each matrix has shape ``(rows, dimension)``.
    """
    if rows is not None and (rows <= 0 or rows > dimension):
        raise ValueError("rows must be in the range [1, dimension].")

    key_material = hashlib.sha256(iv.encode("utf-8")).digest()
    return [_generate_one(key_material, r, dimension, rows) for r in range(rotation_count)]


def _generate_one(
    key_material: bytes,
    rotation_index: int,
    n: int,
    rows: Optional[int] = None,
) -> np.ndarray:
    """Generate a single ``n x n`` proper-rotation matrix."""
    pairs_per_col = (n + 1) // 2
    sample_count = n * pairs_per_col

    # Reuse HMAC's padded key state and vectorize the Box-Muller transform. The
    # resulting digest bytes and QR input remain identical to the scalar path.
    padded_key = key_material.ljust(64, b"\x00")
    inner_pad = bytes(value ^ 0x36 for value in padded_key)
    outer_pad = bytes(value ^ 0x5C for value in padded_key)
    inner_hash = hashlib.sha256(inner_pad)
    outer_hash = hashlib.sha256(outer_pad)
    digest_bytes = bytearray(sample_count * 16)
    counter_base = rotation_index * sample_count

    for sample_index in range(sample_count):
        inner = inner_hash.copy()
        inner.update((counter_base + sample_index).to_bytes(8, "big"))
        outer = outer_hash.copy()
        outer.update(inner.digest())
        digest_start = sample_index * 16
        digest_bytes[digest_start : digest_start + 16] = outer.digest()[:16]

    digest_words = np.frombuffer(bytes(digest_bytes), dtype=">u8").reshape(sample_count, 2)
    uniforms = ((digest_words >> np.uint64(11)) & np.uint64(_MANTISSA_BITS - 1)).astype(np.float64) * _MANTISSA_SCALE
    u1 = np.maximum(uniforms[:, 0], _MIN_UNIFORM)
    u2 = uniforms[:, 1]
    radius = np.sqrt(-2.0 * np.log(u1))
    theta = _TWO_PI * u2

    interleaved = np.empty(sample_count * 2, dtype=np.float64)
    interleaved[0::2] = radius * np.cos(theta)
    interleaved[1::2] = radius * np.sin(theta)
    raw = interleaved.reshape(n, pairs_per_col * 2)[:, :n].T.copy()

    q, r = np.linalg.qr(raw)
    q = q * np.sign(np.diag(r))[np.newaxis, :]
    if np.sign(np.linalg.det(q)) < 0:
        q[:, n - 1] = -q[:, n - 1]
    return q if rows is None else q[:rows, :].copy()


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
