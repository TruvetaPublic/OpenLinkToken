import pytest

from openlinktoken.core.ai.tokens.ml1_inference_config import ML1InferenceConfig


@pytest.fixture(autouse=True)
def reset_config():
    """Restore process-wide ML1 settings after each test."""

    def restore():
        ML1InferenceConfig.configure(
            True,
            ML1InferenceConfig.DEFAULT_MODEL_PATH,
            ML1InferenceConfig.DEFAULT_TOKENIZER_PATH,
            ML1InferenceConfig.DEFAULT_MAX_SEQUENCE_LENGTH,
            ML1InferenceConfig.DEFAULT_BATCH_SIZE,
            ML1InferenceConfig.DEFAULT_NUM_THREADS,
        )

    restore()
    yield
    restore()


def test_blank_paths_use_defaults():
    """Blank model and tokenizer paths should use their bundled defaults."""
    ML1InferenceConfig.configure(True, " ", "", 32, 8, 2)

    assert ML1InferenceConfig.is_enabled()
    assert ML1InferenceConfig.get_model_path() == ML1InferenceConfig.DEFAULT_MODEL_PATH
    assert ML1InferenceConfig.get_tokenizer_path() == ML1InferenceConfig.DEFAULT_TOKENIZER_PATH
    assert ML1InferenceConfig.get_max_sequence_length() == 32
    assert ML1InferenceConfig.get_batch_size() == 8
    assert ML1InferenceConfig.get_num_threads() == 2


@pytest.mark.parametrize(
    "sequence_length,batch_size,thread_count",
    [(0, 1, 1), (1, 0, 1), (1, 1, 0), (1, 1, -1)],
)
def test_non_positive_numeric_values_raise(sequence_length, batch_size, thread_count):
    """Non-positive ML1 numeric settings should be rejected."""
    with pytest.raises(ValueError):
        ML1InferenceConfig.configure(True, "", "", sequence_length, batch_size, thread_count)
