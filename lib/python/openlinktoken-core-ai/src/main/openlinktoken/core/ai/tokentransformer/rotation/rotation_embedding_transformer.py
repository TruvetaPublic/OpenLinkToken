# SPDX-License-Identifier: MIT

import hashlib
import hmac
import logging
import os
import tempfile
import zipfile
from pathlib import Path
from threading import Lock
from typing import List, Optional

import numpy as np

from openlinktoken.core.ai.tokentransformer.rotation.embedding_rotator import rotate
from openlinktoken.core.ai.tokentransformer.rotation.rotation_matrix_generator import (
    _generate_one,
    generate,
)
from openlinktoken.core.ai.tokentransformer.rotation.rotation_quantizer import quantize
from openlinktoken.ec_key_utils import ensure_directory

logger = logging.getLogger(__name__)

_SENTINEL = np.array([-1.0])
_CACHE_VERSION = "v1"
_CACHE_DIRECTORY = "rotation-matrices"
_CACHE_ROOT_ENV = "OLT_ROTATION_CACHE_DIR"


def _algorithm_fingerprint() -> str:
    """Return a fingerprint that invalidates caches when generation code changes."""
    digest = hashlib.sha256()
    digest.update(_CACHE_VERSION.encode("utf-8"))
    digest.update(np.__version__.encode("utf-8"))
    for function in (generate, _generate_one):
        digest.update(function.__code__.co_code)
        digest.update(repr(function.__code__.co_consts).encode("utf-8"))
    return digest.hexdigest()


_CACHE_ALGORITHM_FINGERPRINT = _algorithm_fingerprint()


def _cache_root() -> Optional[Path]:
    """Return the configured cache root, or None when no home directory is available."""
    try:
        configured_root = os.getenv(_CACHE_ROOT_ENV, "").strip()
        if configured_root:
            return Path(configured_root).expanduser()
        return Path.home() / ".openlinktoken"
    except (OSError, RuntimeError, ValueError) as error:
        logger.warning("Rotation matrix cache is unavailable: %s", error)
        return None


def _matrix_cache_path(
    iv: str,
    rotation_count: int,
    dimension: int,
    hash_dimension: int,
) -> Optional[Path]:
    """Return the private cache path for one deterministic matrix configuration."""
    cache_key = "\x00".join(
        (
            _CACHE_VERSION,
            _CACHE_ALGORITHM_FINGERPRINT,
            iv,
            str(rotation_count),
            str(dimension),
            str(hash_dimension),
        ),
    )
    digest = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
    root = _cache_root()
    return None if root is None else root / _CACHE_DIRECTORY / f"{digest}.npz"


def _load_cached_matrices(
    iv: str,
    rotation_count: int,
    dimension: int,
    hash_dimension: int,
) -> Optional[List[np.ndarray]]:
    """Load validated leading matrix rows from the local cache when available."""
    if rotation_count <= 0:
        return []

    cache_path = _matrix_cache_path(iv, rotation_count, dimension, hash_dimension)
    if cache_path is None:
        return None

    try:
        if not cache_path.is_file():
            return None
        with np.load(cache_path, allow_pickle=False) as cache:
            cached = cache["matrices"]
            stored_digest = cache["digest"]
    except (OSError, ValueError, EOFError, KeyError, TypeError, IndexError, MemoryError, zipfile.BadZipFile) as error:
        logger.warning("Ignoring unreadable rotation matrix cache: %s", error)
        return None

    expected_shape = (rotation_count, hash_dimension, dimension)
    if (
        not isinstance(cached, np.ndarray)
        or cached.shape != expected_shape
        or cached.dtype != np.dtype(np.float64)
        or not np.isfinite(cached).all()
        or stored_digest.dtype != np.dtype(np.uint8)
        or stored_digest.shape != (hashlib.sha256().digest_size,)
    ):
        logger.warning("Ignoring invalid rotation matrix cache: unexpected shape or values")
        return None

    cached = np.ascontiguousarray(cached)
    actual_digest = hashlib.sha256(cached.tobytes()).digest()
    if not hmac.compare_digest(actual_digest, stored_digest.tobytes()):
        logger.warning("Ignoring invalid rotation matrix cache: digest mismatch")
        return None

    return [cached[index] for index in range(rotation_count)]


def _write_cached_matrices(
    iv: str,
    rotation_count: int,
    dimension: int,
    hash_dimension: int,
    matrices: List[np.ndarray],
) -> None:
    """Atomically write leading matrix rows to a private best-effort cache."""
    if rotation_count <= 0:
        return

    cache_path = _matrix_cache_path(iv, rotation_count, dimension, hash_dimension)
    if cache_path is None:
        return

    temporary_path: Optional[Path] = None
    try:
        matrix_array = np.ascontiguousarray(np.stack(matrices, axis=0), dtype=np.float64)
        digest = np.frombuffer(hashlib.sha256(matrix_array.tobytes()).digest(), dtype=np.uint8)
        ensure_directory(cache_path.parent.parent)
        ensure_directory(cache_path.parent)
        with tempfile.NamedTemporaryFile(
            dir=cache_path.parent,
            prefix=f".{cache_path.stem}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            os.chmod(temporary_path, 0o600)
            np.savez(temporary_file, matrices=matrix_array, digest=digest)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, cache_path)
        temporary_path = None
    except (OSError, ValueError) as error:
        logger.warning("Unable to write rotation matrix cache: %s", error)
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                logger.debug("Unable to remove incomplete rotation matrix cache", exc_info=True)


class RotationEmbeddingTransformer:
    """Composites matrix generation, rotation, truncation, and quantization into a
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
            hash_dimension: Number of leading rotated dimensions to retain and quantize (k ≤ N).
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
        self._matrices: Optional[List[np.ndarray]] = None
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
                    actual = _load_cached_matrices(
                        self._iv,
                        self._rotation_count - 1,
                        self._dimension,
                        self._hash_dimension,
                    )
                    if actual is None:
                        actual = generate(
                            self._iv,
                            self._rotation_count - 1,
                            self._dimension,
                            row_count=self._hash_dimension,
                        )
                        _write_cached_matrices(
                            self._iv,
                            self._rotation_count - 1,
                            self._dimension,
                            self._hash_dimension,
                            actual,
                        )
                    self._matrices = [_SENTINEL] + actual
