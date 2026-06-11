# SPDX-License-Identifier: MIT

from typing import List, Union

import numpy as np


def rotate(
    embedding: List[float],
    matrices: List[Union[List[List[float]], np.ndarray]],
    bias: List[float],
    k: int,
) -> List[List[float]]:
    """Apply rotation matrices to an embedding vector and project to k dimensions.

    The first entry in ``matrices`` may be the ``[[-1]]`` sentinel, which signals a
    pass-through projection: the first ``k`` values of the bias-centred embedding are
    returned directly without any rotation.  This matches the cloud backend's index-0
    pass-through token.  All subsequent entries must be valid N×N rotation matrices.

    Args:
        embedding: Source float vector of length N.
        matrices: List whose first entry may be the ``[[-1]]`` sentinel and whose
            remaining entries are orthogonal rotation matrices, each N×N.  Each matrix
            may be a numpy ndarray (preferred for performance) or a row-major list-of-lists.
        bias: Float vector of length N subtracted before rotation (zeros = no centering).
        k: Number of output dimensions to retain (k ≤ N).

    Returns:
        List of k-dimensional float lists, one per entry in ``matrices``.
    """
    # Cast the input to float32 first, then promote to float64 for the arithmetic.
    # This matches the Java EmbeddingRotator contract (float[] embedding → double arithmetic)
    # and ensures cross-language parity: both sides start from identical float32 precision
    # regardless of whether the caller holds the embedding as float32 or float64.
    x_centered = np.asarray(embedding, dtype=np.float32).astype(np.float64) - np.asarray(bias, dtype=np.float64)
    results = []
    for R in matrices:
        R_arr = R if isinstance(R, np.ndarray) else np.asarray(R, dtype=np.float64)
        if R_arr.size == 1 and R_arr.ravel()[0] == -1.0:
            # Sentinel: pass-through — return first k values of the centred embedding.
            # Cast back to float32 to match Java's (float) xCentered[i] cast.
            results.append(x_centered[:k].astype(np.float32).tolist())
        else:
            # Q[:k, :] @ x  — only the first k rows of the rotation matrix are needed.
            # Cast back to float32 to match Java's (float) sum cast.
            results.append((R_arr[:k, :] @ x_centered).astype(np.float32).tolist())
    return results
