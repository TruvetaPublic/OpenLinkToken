"""Runtime configuration for rotation-based T6 token generation."""

from typing import ClassVar, Optional


class RotationConfig:
    """Static configuration for rotation-based T6 embedding token generation.

    Call RotationConfig.configure(...) from the CLI entry point before processing.
    Call RotationConfig.is_enabled() to check whether rotation is active.
    """

    DEFAULT_ROTATION_COUNT: ClassVar[int] = 30
    DEFAULT_HASH_DIMENSION: ClassVar[int] = 32
    DEFAULT_BIN_WIDTH: ClassVar[float] = 0.05
    DEFAULT_MIN_VAL: ClassVar[float] = -5.0
    DEFAULT_MAX_VAL: ClassVar[float] = 5.0

    _enabled: ClassVar[bool] = False
    _rotation_iv: ClassVar[Optional[str]] = None
    _rotation_count: ClassVar[int] = DEFAULT_ROTATION_COUNT
    _hash_dimension: ClassVar[int] = DEFAULT_HASH_DIMENSION
    _bin_width: ClassVar[float] = DEFAULT_BIN_WIDTH
    _min_val: ClassVar[float] = DEFAULT_MIN_VAL
    _max_val: ClassVar[float] = DEFAULT_MAX_VAL

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
    ) -> None:
        """Configure the rotation token generation parameters.

        Args:
            enable: Whether rotation token generation is active.
            rotation_iv: Initialization vector for matrix generation (required when enable=True).
            rotation_count: Number of rotation matrices to generate (must be > 0).
            hash_dimension: Projected dimensions to keep and quantize (must be > 0).
            bin_width: Quantizer bin width (must be > 0).
            min_val: Quantizer lower bound.
            max_val: Quantizer upper bound.
        """
        if enable and not rotation_iv:
            raise ValueError("rotation_iv is required when rotation is enabled.")
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

    @classmethod
    def is_enabled(cls) -> bool:
        """Return whether rotation token generation is enabled."""
        return cls._enabled and cls._rotation_iv is not None

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
