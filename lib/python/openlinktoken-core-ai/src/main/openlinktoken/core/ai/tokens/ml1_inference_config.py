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
        configured_num_threads: int = DEFAULT_NUM_THREADS,
    ) -> None:
        """
        Apply ML1 runtime configuration.

        Args:
            enable_ml1: Whether to enable ml1.
            configured_model_path: Filesystem path to the configured model handled by the operation.
            configured_tokenizer_path: Filesystem path to the configured tokenizer handled by the operation.
            configured_max_sequence_length: Numeric configured max sequence length value used to configure.
            configured_batch_size: Numeric configured batch size value used to configure.
            configured_num_threads: Numeric configured num threads value used to configure.
        """
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
        cls._max_sequence_length = configured_max_sequence_length
        cls._batch_size = configured_batch_size
        cls._num_threads = configured_num_threads

    @classmethod
    def is_enabled(cls) -> bool:
        """
        Return whether ML1 inference is enabled.

        Returns:
            Whether ML1 inference is enabled.
        """
        return cls._enabled

    @classmethod
    def get_model_path(cls) -> str:
        """
        Return configured ONNX model path.

        Returns:
            The model path value returned by the operation.
        """
        return cls._model_path

    @classmethod
    def get_tokenizer_path(cls) -> str:
        """
        Return configured tokenizer path.

        Returns:
            The tokenizer path value returned by the operation.
        """
        return cls._tokenizer_path

    @classmethod
    def get_max_sequence_length(cls) -> int:
        """
        Return configured maximum sequence length.

        Returns:
            The max sequence length value returned by the operation.
        """
        return cls._max_sequence_length

    @classmethod
    def get_batch_size(cls) -> int:
        """
        Return configured inference batch size.

        Returns:
            The batch size value returned by the operation.
        """
        return cls._batch_size

    @classmethod
    def get_num_threads(cls) -> int:
        """
        Return configured ORT intra/inter-op thread count.

        Returns:
            The num threads value returned by the operation.
        """
        return cls._num_threads
