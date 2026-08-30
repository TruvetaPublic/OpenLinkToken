import platform
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import onnxruntime as ort
import pytest

from openlinktoken.core.ai.tokens.ml1_inference_config import ML1InferenceConfig
from openlinktoken.core.ai.tokens.ml1_onnx_signature_generator import (
    ML1OnnxSignatureGenerator,
    _preload_cuda_libraries,
    _resolve_providers,
)


def test_empty_signatures_do_not_initialize_onnx():
    """Empty input should return without initializing ONNX resources."""
    assert ML1OnnxSignatureGenerator.generate_signatures([]) == []


def test_empty_signatures_and_embeddings_are_empty():
    """The internal batched path should return parallel empty collections."""
    assert ML1OnnxSignatureGenerator._generate_signatures_with_embeddings([]) == ([], [])


def test_final_inference_batch_is_not_padded(monkeypatch):
    """The final dynamic ONNX batch should contain only real input rows."""
    batch_sizes = []

    def fake_run_batch(cls, rows):
        """Capture the requested batch size without starting an ONNX session."""
        batch_sizes.append(len(rows))
        return np.zeros((len(rows), 2), dtype=np.float32), 0.0

    monkeypatch.setattr(ML1InferenceConfig, "get_batch_size", lambda: 4)
    monkeypatch.setattr(ML1OnnxSignatureGenerator, "_initialize_if_needed", classmethod(lambda cls: None))
    monkeypatch.setattr(ML1OnnxSignatureGenerator, "_run_batch_inference", classmethod(fake_run_batch))
    monkeypatch.setattr(ML1OnnxSignatureGenerator, "_serialize_embedding", staticmethod(lambda embedding: "raw"))

    signatures, embeddings = ML1OnnxSignatureGenerator._generate_signatures_with_embeddings(
        ["row-1", "row-2", "row-3", "row-4", "row-5", "row-6"],
    )

    assert batch_sizes == [4, 2]
    assert signatures == ["raw"] * 6
    assert len(embeddings) == 6


def test_rotated_inference_can_skip_unused_raw_serialization(monkeypatch):
    """Batched callers can request embeddings without serializing discarded raw signatures."""

    def fake_run_batch(cls, rows):
        """Return one deterministic embedding per requested row."""
        return np.zeros((len(rows), 2), dtype=np.float32), 0.0

    monkeypatch.setattr(ML1OnnxSignatureGenerator, "_initialize_if_needed", classmethod(lambda cls: None))
    monkeypatch.setattr(ML1OnnxSignatureGenerator, "_run_batch_inference", classmethod(fake_run_batch))
    monkeypatch.setattr(
        ML1OnnxSignatureGenerator,
        "_serialize_embedding",
        staticmethod(lambda embedding: pytest.fail("raw embedding should not be serialized")),
    )

    signatures, embeddings = ML1OnnxSignatureGenerator._generate_signatures_with_embeddings(
        ["row-1"],
        include_raw_signatures=False,
    )

    assert signatures == [""]
    assert len(embeddings) == 1


def test_serialize_embedding_uses_float32_big_endian_bytes():
    """Embedding serialization must preserve the existing big-endian float32 contract."""

    class NonIterableEmbedding(np.ndarray):
        """Reject element-by-element iteration so the vectorized path is exercised."""

        def __iter__(self):
            """Fail if serialization falls back to Python-level iteration."""
            raise AssertionError("serialization should use NumPy bytes directly")

    embedding = np.array([1.0, -2.5], dtype=np.float32).view(NonIterableEmbedding)
    assert ML1OnnxSignatureGenerator._serialize_embedding(embedding) == ("3f800000c0200000")


def test_macos_uses_cpu_for_the_large_ml1_model(monkeypatch):
    """macOS should avoid CoreML's unsafe memory growth for the ML1 model."""
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        ort,
        "get_available_providers",
        lambda: ["CoreMLExecutionProvider", "CPUExecutionProvider"],
    )

    assert _resolve_providers() == ["CPUExecutionProvider"]


def test_cuda_is_preferred_when_available(monkeypatch):
    """NVIDIA CUDA should be selected before the CPU fallback."""
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        "openlinktoken.core.ai.tokens.ml1_onnx_signature_generator._nvidia_device_available",
        lambda: True,
    )
    monkeypatch.setattr(
        ort,
        "get_available_providers",
        lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"],
    )

    assert _resolve_providers() == ["CUDAExecutionProvider", "CPUExecutionProvider"]


def test_cuda_falls_back_to_cpu_without_nvidia_device(monkeypatch):
    """A GPU wheel without a visible NVIDIA device should use CPU directly."""
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        "openlinktoken.core.ai.tokens.ml1_onnx_signature_generator._nvidia_device_available",
        lambda: False,
    )
    monkeypatch.setattr(
        ort,
        "get_available_providers",
        lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"],
    )

    assert _resolve_providers() == ["CPUExecutionProvider"]


def test_cuda_preloads_bundled_runtime_libraries():
    """CUDA sessions should preload the runtime libraries installed with the GPU wheel."""
    fake_ort = Mock()

    _preload_cuda_libraries(fake_ort, ["CUDAExecutionProvider", "CPUExecutionProvider"])

    fake_ort.preload_dlls.assert_called_once_with(directory="")


def test_coreml_loads_external_model_data_from_memory(tmp_path):
    """CoreML sessions should avoid the external-data file-path loading bug."""
    model_path = tmp_path / "model.onnx"
    external_data_path = Path(f"{model_path}.data")
    model_path.write_bytes(b"model")
    external_data_path.write_bytes(b"weights")

    session_options = Mock()
    session = object()
    fake_ort = Mock()
    fake_ort.InferenceSession.return_value = session

    result = ML1OnnxSignatureGenerator._create_session(
        fake_ort,
        session_options,
        model_path,
        [("CoreMLExecutionProvider", {"MLComputeUnits": "ALL"}), "CPUExecutionProvider"],
    )

    assert result is session
    fake_ort.InferenceSession.assert_called_once()
    assert fake_ort.InferenceSession.call_args.args[0] == b"model"
    assert session_options.add_external_initializers_from_files_in_memory.call_args.args[0] == ["model.onnx.data"]


def test_coreml_disables_matmul_add_fusion(tmp_path):
    """CoreML should not inline large MatMul weights into its compiled model."""
    model_path = tmp_path / "model.onnx"
    model_path.touch()
    session_options = ort.SessionOptions()
    fake_ort = Mock()

    ML1OnnxSignatureGenerator._create_session(
        fake_ort,
        session_options,
        model_path,
        [("CoreMLExecutionProvider", {"MLComputeUnits": "ALL"}), "CPUExecutionProvider"],
    )

    assert session_options.get_session_config_entry("optimization.disable_specified_optimizers") == "MatMulAddFusion"


def test_explicit_filesystem_paths_resolve_directly(tmp_path):
    """Configured local paths should resolve directly."""
    model_path = tmp_path / "model.onnx"
    model_path.touch()

    assert ML1OnnxSignatureGenerator._resolve_path(str(model_path)) == model_path.absolute()


def test_missing_explicit_path_has_clear_error(tmp_path):
    """Missing explicit paths should fail before ONNX initialization."""
    with pytest.raises(FileNotFoundError, match="Configured ML1 asset path does not exist"):
        ML1OnnxSignatureGenerator._resolve_path(str(tmp_path / "missing.onnx"))


def test_missing_default_assets_require_local_placement(monkeypatch):
    """Missing default assets should explain the required local placement."""
    monkeypatch.setattr(
        ML1OnnxSignatureGenerator,
        "_find_local_asset",
        classmethod(lambda cls, filename, resource_path: None),
    )

    with pytest.raises(FileNotFoundError, match="do not download"):
        ML1OnnxSignatureGenerator._resolve_path("classpath:/inferencing/ml1/tokenizer.json")


def test_bundled_package_assets_are_used(monkeypatch, tmp_path):
    """Bundled package assets should be used directly."""
    tokenizer_path = tmp_path / "tokenizer.json"
    tokenizer_path.touch()
    monkeypatch.setattr(
        ML1OnnxSignatureGenerator,
        "_find_local_asset",
        classmethod(lambda cls, filename, resource_path: tokenizer_path),
    )

    assert ML1OnnxSignatureGenerator._resolve_path("classpath:/inferencing/ml1/tokenizer.json") == tokenizer_path
