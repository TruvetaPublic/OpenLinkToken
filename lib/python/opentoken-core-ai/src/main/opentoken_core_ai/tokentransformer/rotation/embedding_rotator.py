"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import List, Union

import numpy as np


def rotate(
    embedding: List[float],
    matrices: List[Union[List[List[float]], np.ndarray]],
    bias: List[float],
    k: int,
) -> List[List[float]]:
    """Apply rotation matrices to an embedding vector and project to k dimensions.

    Args:
        embedding: Source float vector of length N.
        matrices: List of orthogonal rotation matrices, each N×N.  Each matrix
            may be a numpy ndarray (preferred for performance) or a row-major
            list-of-lists.
        bias: Float vector of length N subtracted before rotation (zeros = no centering).
        k: Number of output dimensions to retain (k ≤ N).

    Returns:
        List of k-dimensional float lists, one per rotation matrix.
    """
    x_centered = np.asarray(embedding, dtype=np.float64) - np.asarray(bias, dtype=np.float64)
    results = []
    for R in matrices:
        R_arr = R if isinstance(R, np.ndarray) else np.asarray(R, dtype=np.float64)
        # Q[:k, :] @ x  — only the first k rows of the rotation matrix are needed.
        rotated = (R_arr[:k, :] @ x_centered).tolist()
        results.append(rotated)
    return results
