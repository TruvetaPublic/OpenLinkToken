"""Runtime configuration for optional ONNX-backed ML1 token generation."""

import os


class ML1InferenceConfig:
    """Holds process-wide settings for ML1 ONNX inference."""

    DEFAULT_MODEL_PATH = "classpath:/inferencing/ml1/model.onnx"
    DEFAULT_TOKENIZER_PATH = "classpath:/inferencing/ml1/tokenizer.json"
    DEFAULT_MAX_SEQUENCE_LENGTH = 128
    DEFAULT_BATCH_SIZE = 64
    DEFAULT_NUM_THREADS = os.cpu_count() or 1

    _enabled = True
    _model_path = DEFAULT_MODEL_PATH
    _tokenizer_path = DEFAULT_TOKENIZER_PATH
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
        configured_num_threads: int = 0,
    ) -> None:
        """Apply ML1 runtime configuration."""
        if configured_max_sequence_length <= 0:
            raise ValueError("ML1 max sequence length must be greater than zero.")
        if configured_batch_size <= 0:
            raise ValueError("ML1 batch size must be greater than zero.")

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
        cls._max_sequence_length = configured_max_sequence_length
        cls._batch_size = configured_batch_size
        cls._num_threads = configured_num_threads if configured_num_threads > 0 else cls.DEFAULT_NUM_THREADS

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
