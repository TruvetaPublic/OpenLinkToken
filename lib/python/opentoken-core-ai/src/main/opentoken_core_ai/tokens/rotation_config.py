"""Runtime configuration for rotation-based T6 token generation."""

from typing import ClassVar, List, Optional


class RotationConfig:
    """Static configuration for rotation-based T6 embedding token generation.

    Rotation is active by default when the AI module is installed; ``DEFAULT_IV``
    is used automatically so no explicit call to ``configure()`` is required for
    the common case.

    Call RotationConfig.configure(...) from the CLI entry point to override
    settings or to explicitly disable rotation.
    Call RotationConfig.is_enabled() to check whether rotation is active.
    """

    DEFAULT_IV: ClassVar[str] = "opentoken-t6-v1"
    DEFAULT_ROTATION_COUNT: ClassVar[int] = 30
    DEFAULT_HASH_DIMENSION: ClassVar[int] = 4
    DEFAULT_BIN_WIDTH: ClassVar[float] = 0.05
    DEFAULT_MIN_VAL: ClassVar[float] = -5.0
    DEFAULT_MAX_VAL: ClassVar[float] = 5.0

    _enabled: ClassVar[bool] = True
    _rotation_iv: ClassVar[Optional[str]] = DEFAULT_IV
    _rotation_count: ClassVar[int] = DEFAULT_ROTATION_COUNT
    _hash_dimension: ClassVar[int] = DEFAULT_HASH_DIMENSION
    _bin_width: ClassVar[float] = DEFAULT_BIN_WIDTH
    _min_val: ClassVar[float] = DEFAULT_MIN_VAL
    _max_val: ClassVar[float] = DEFAULT_MAX_VAL
    _dimension_bias: ClassVar[Optional[List[float]]] = None

    @classmethod
    def configure(
        cls,
        enable: bool,
        rotation_iv: Optional[str] = None,
        rotation_count: int = DEFAULT_ROTATION_COUNT,
        hash_dimension: int = DEFAULT_HASH_DIMENSION,
        bin_width: float = DEFAULT_BIN_WIDTH,
        min_val: float = DEFAULT_MIN_VAL,
        max_val: float = DEFAULT_MAX_VAL,
        dimension_bias: Optional[List[float]] = None,
    ) -> None:
        """Configure the rotation token generation parameters.

        Args:
            enable: Whether rotation token generation is active.
            rotation_iv: Initialization vector for matrix generation.
                         When ``enable=True`` and no IV is supplied, ``DEFAULT_IV``
                         is used automatically.
            rotation_count: Number of rotation matrices to generate (must be > 0).
            hash_dimension: Projected dimensions to keep and quantize (must be > 0).
            bin_width: Quantizer bin width (must be > 0).
            min_val: Quantizer lower bound.
            max_val: Quantizer upper bound.
            dimension_bias: Bias vector subtracted before rotation. None or empty
                            means all zeros (no centering).
        """
        if enable and not rotation_iv:
            rotation_iv = cls.DEFAULT_IV
        if rotation_count <= 0:
            raise ValueError("rotation_count must be greater than zero.")
        if hash_dimension <= 0:
            raise ValueError("hash_dimension must be greater than zero.")
        if bin_width <= 0.0:
            raise ValueError("bin_width must be greater than zero.")
        cls._enabled = enable
        cls._rotation_iv = rotation_iv
        cls._rotation_count = rotation_count
        cls._hash_dimension = hash_dimension
        cls._bin_width = bin_width
        cls._min_val = min_val
        cls._max_val = max_val
        cls._dimension_bias = dimension_bias if dimension_bias else None

    @classmethod
    def is_enabled(cls) -> bool:
        """Return whether rotation token generation is enabled."""
        return cls._enabled

    @classmethod
    def get_rotation_iv(cls) -> Optional[str]:
        """Return the rotation initialization vector."""
        return cls._rotation_iv

    @classmethod
    def get_rotation_count(cls) -> int:
        """Return the number of rotation matrices to generate."""
        return cls._rotation_count

    @classmethod
    def get_hash_dimension(cls) -> int:
        """Return the number of projected dimensions to quantize."""
        return cls._hash_dimension

    @classmethod
    def get_bin_width(cls) -> float:
        """Return the quantizer bin width."""
        return cls._bin_width

    @classmethod
    def get_min_val(cls) -> float:
        """Return the quantizer lower bound."""
        return cls._min_val

    @classmethod
    def get_max_val(cls) -> float:
        """Return the quantizer upper bound."""
        return cls._max_val

    @classmethod
    def get_dimension_bias(cls) -> Optional[List[float]]:
        """Return the dimension bias vector, or None for all-zeros default."""
        return cls._dimension_bias
