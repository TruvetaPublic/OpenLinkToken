# SPDX-License-Identifier: MIT

import logging
from threading import Lock
from typing import List, Optional

import numpy as np

from openlinktoken_core_ai.tokentransformer.rotation.embedding_rotator import rotate
from openlinktoken_core_ai.tokentransformer.rotation.rotation_matrix_generator import generate
from openlinktoken_core_ai.tokentransformer.rotation.rotation_quantizer import quantize

logger = logging.getLogger(__name__)

_SENTINEL = np.array([-1.0])


class RotationEmbeddingTransformer:
    """Composites matrix generation, rotation projection, and quantization into a
    single float-vector → token-list transformer.

    Rotation matrices are generated lazily from the IV and cached for the lifetime
    of the instance. Thread-safe initialization.
    """

    def __init__(
        self,
        iv: str,
        rotation_count: int,
        dimension: int,
        hash_dimension: int,
        bias: Optional[List[float]] = None,
        min_val: float = -5.0,
        max_val: float = 5.0,
        bin_width: float = 0.05,
    ):
        """Initialize the transformer with rotation configuration.

        Args:
            iv: Initialization vector string used to derive rotation matrices.
            rotation_count: Number of rotation matrices to generate.
            dimension: Size of the input embedding vector (N).
            hash_dimension: Number of projected dimensions to retain and quantize (k ≤ N).
            bias: Optional float vector of length N subtracted before rotation. Defaults to zeros.
            min_val: Quantizer lower bound (default -5.0).
            max_val: Quantizer upper bound (default +5.0).
            bin_width: Quantizer bin width (default 0.05).
        """
        self._iv = iv
        self._rotation_count = rotation_count
        self._dimension = dimension
        self._hash_dimension = hash_dimension
        self._bias = bias if bias is not None else [0.0] * dimension
        self._min_val = min_val
        self._max_val = max_val
        self._bin_width = bin_width
        self._matrices: Optional[List[List[List[float]]]] = None
        self._lock = Lock()

    def transform(self, embedding: List[float]) -> List[str]:
        """Transform a raw float embedding into rotation-quantized token strings.

        Returns one token string per rotation matrix.

        Args:
            embedding: Raw float vector of length N (must match the configured dimension).

        Returns:
            List of space-separated bin-index strings, one per rotation matrix.
        """
        self._ensure_matrices()
        projections = rotate(embedding, self._matrices, self._bias, self._hash_dimension)
        return [quantize(p, self._min_val, self._max_val, self._bin_width) for p in projections]

    def _ensure_matrices(self) -> None:
        """Lazily generate and cache rotation matrices in a thread-safe manner.

        The matrices list always starts with the ``[[-1]]`` sentinel at index 0,
        followed by ``rotation_count - 1`` actual rotation matrices.  The sentinel
        signals a pass-through projection for token[0]: the first ``hash_dimension``
        values of the bias-centred embedding are used directly without rotation.
        This matches the cloud backend token generation format exactly.
        """
        if self._matrices is None:
            with self._lock:
                if self._matrices is None:
                    actual = generate(
                        self._iv,
                        self._rotation_count - 1,
                        self._dimension,
                        hash_dimension=self._hash_dimension,
                    )
                    self._matrices = [_SENTINEL] + actual
