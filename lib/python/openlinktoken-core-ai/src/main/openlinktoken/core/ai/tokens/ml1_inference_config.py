"""Runtime configuration for optional ONNX-backed ML1 token generation."""

import os
from pathlib import Path
from typing import Optional, Union


class ML1InferenceConfig:
    """Holds process-wide settings for ML1 ONNX inference."""

    DEFAULT_MODEL_PATH = "classpath:/inferencing/ml1/model.onnx"
    DEFAULT_TOKENIZER_PATH = "classpath:/inferencing/ml1/tokenizer.json"
    DEFAULT_ASSET_REPOSITORY = "TruvetaPublic/OpenLinkToken"
    DEFAULT_ASSET_REF = "release/2.1.1"
    DEFAULT_ASSET_BASE_URL = f"https://media.githubusercontent.com/media/{DEFAULT_ASSET_REPOSITORY}"
    DEFAULT_ASSET_RAW_BASE_URL = f"https://raw.githubusercontent.com/{DEFAULT_ASSET_REPOSITORY}"
    DEFAULT_ASSET_CACHE_DIRECTORY = str((Path.home() / ".openlinktoken" / "ml1").absolute())
    DEFAULT_CACHE_DIR = Path(DEFAULT_ASSET_CACHE_DIRECTORY)
    ASSET_MANIFEST_FILENAME = "asset-manifest.json"
    DEFAULT_MAX_SEQUENCE_LENGTH = 128
    DEFAULT_BATCH_SIZE = 64
    DEFAULT_NUM_THREADS = os.cpu_count() or 1

    _enabled = True
    _model_path = DEFAULT_MODEL_PATH
    _tokenizer_path = DEFAULT_TOKENIZER_PATH
    _asset_ref = os.environ.get("OPENLINKTOKEN_ML1_ASSET_REF", DEFAULT_ASSET_REF).strip() or DEFAULT_ASSET_REF
    _cache_dir = (
        Path(os.environ.get("OPENLINKTOKEN_ML1_CACHE_DIR", "").strip() or DEFAULT_ASSET_CACHE_DIRECTORY)
        .expanduser()
        .absolute()
    )
    _max_sequence_length = DEFAULT_MAX_SEQUENCE_LENGTH
    _batch_size = DEFAULT_BATCH_SIZE
    _num_threads = DEFAULT_NUM_THREADS

    @classmethod
    def configure(
        cls,
        enable_ml1: bool,
        configured_model_path: str,
        configured_tokenizer_path: str,
        configured_max_sequence_length: int,
        configured_batch_size: int = DEFAULT_BATCH_SIZE,
        configured_num_threads: int = DEFAULT_NUM_THREADS,
        configured_asset_ref: Optional[str] = None,
        configured_cache_dir: Optional[Union[str, os.PathLike[str]]] = None,
    ) -> None:
        """Apply ML1 runtime configuration."""
        if configured_max_sequence_length <= 0:
            raise ValueError("ML1 max sequence length must be greater than zero.")
        if configured_batch_size <= 0:
            raise ValueError("ML1 batch size must be greater than zero.")
        if configured_num_threads <= 0:
            raise ValueError("ML1 num threads must be greater than zero.")

        cls._enabled = enable_ml1
        cls._model_path = (
            configured_model_path.strip()
            if configured_model_path and configured_model_path.strip()
            else cls.DEFAULT_MODEL_PATH
        )
        cls._tokenizer_path = (
            configured_tokenizer_path.strip()
            if configured_tokenizer_path and configured_tokenizer_path.strip()
            else cls.DEFAULT_TOKENIZER_PATH
        )
        cls.configure_asset_storage(configured_asset_ref, configured_cache_dir)
        cls._max_sequence_length = configured_max_sequence_length
        cls._batch_size = configured_batch_size
        cls._num_threads = configured_num_threads

    @classmethod
    def is_enabled(cls) -> bool:
        """Return whether ML1 inference is enabled."""
        return cls._enabled

    @classmethod
    def get_model_path(cls) -> str:
        """Return configured ONNX model path."""
        return cls._model_path

    @classmethod
    def get_tokenizer_path(cls) -> str:
        """Return configured tokenizer path."""
        return cls._tokenizer_path

    @classmethod
    def get_asset_ref(cls) -> str:
        """Return the Git ref used for lazy ML1 asset downloads."""
        return cls._asset_ref

    @classmethod
    def configure_asset_storage(
        cls,
        configured_asset_ref: Optional[str],
        configured_cache_dir: Optional[Union[str, os.PathLike[str]]],
    ) -> None:
        """Configure the Git ref and local cache directory for ML1 assets."""
        environment_asset_ref = os.environ.get("OPENLINKTOKEN_ML1_ASSET_REF", "").strip()
        cls._asset_ref = (
            configured_asset_ref.strip()
            if configured_asset_ref and configured_asset_ref.strip()
            else environment_asset_ref or cls.DEFAULT_ASSET_REF
        )
        environment_cache_dir = os.environ.get("OPENLINKTOKEN_ML1_CACHE_DIR", "").strip()
        cache_dir = (
            str(configured_cache_dir).strip()
            if configured_cache_dir
            else environment_cache_dir or cls.DEFAULT_ASSET_CACHE_DIRECTORY
        )
        cls._cache_dir = Path(cache_dir).expanduser().absolute()

    @classmethod
    def get_cache_dir(cls) -> Path:
        """Return the root directory used for cached ML1 assets."""
        return cls._cache_dir

    @classmethod
    def get_asset_cache_directory(cls) -> str:
        """Return the absolute directory used for cached ML1 assets."""
        return str(cls._cache_dir)

    @classmethod
    def get_max_sequence_length(cls) -> int:
        """Return configured maximum sequence length."""
        return cls._max_sequence_length

    @classmethod
    def get_batch_size(cls) -> int:
        """Return configured inference batch size."""
        return cls._batch_size

    @classmethod
    def get_num_threads(cls) -> int:
        """Return configured ORT intra/inter-op thread count."""
        return cls._num_threads
