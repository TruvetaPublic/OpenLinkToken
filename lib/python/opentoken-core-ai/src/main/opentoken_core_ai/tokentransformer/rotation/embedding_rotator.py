"""
Copyright (c) Truveta. All rights reserved.
"""

from typing import List


def rotate(
    embedding: List[float],
    matrices: List[List[List[float]]],
    bias: List[float],
    k: int,
) -> List[List[float]]:
    """Apply rotation matrices to an embedding vector and project to k dimensions.

    Args:
        embedding: Source float vector of length N.
        matrices: List of orthogonal rotation matrices, each N×N (row-major).
        bias: Float vector of length N subtracted before rotation (zeros = no centering).
        k: Number of output dimensions to retain (k ≤ N).

    Returns:
        List of k-dimensional float lists, one per rotation matrix.
    """
    n = len(embedding)
    x_centered = [float(embedding[i]) - float(bias[i]) for i in range(n)]
    results = []
    for R in matrices:
        rotated = [sum(R[row][col] * x_centered[col] for col in range(n)) for row in range(k)]
        results.append(rotated)
    return results
