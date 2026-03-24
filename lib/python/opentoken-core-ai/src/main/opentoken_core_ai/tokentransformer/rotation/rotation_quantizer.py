"""
Copyright (c) Truveta. All rights reserved.
"""

import math
from typing import List


def quantize(
    x: List[float],
    min_val: float = -5.0,
    max_val: float = 5.0,
    bin_width: float = 0.05,
) -> str:
    """Convert a low-dimensional float vector into a space-separated bin-index string.

    Args:
        x: Input float values.
        min_val: Lower bound of the quantization range (default -5.0).
        max_val: Upper bound of the quantization range (default +5.0).
        bin_width: Width of each bin (default 0.05).

    Returns:
        Space-separated string of integer bin indices.
    """
    num_bins = math.ceil((max_val - min_val) / bin_width)
    bins = []
    for v in x:
        b = int(math.floor((v - min_val) / bin_width))
        bins.append(max(0, min(b, num_bins - 1)))
    return " ".join(str(b) for b in bins)
