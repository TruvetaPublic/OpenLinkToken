import platform
from pathlib import Path
from unittest.mock import Mock

import onnxruntime as ort

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


def test_macos_resolves_coreml_with_all_compute_units(monkeypatch):
    """macOS should use CoreML with CPU, GPU, and Neural Engine availability."""
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        ort,
        "get_available_providers",
        lambda: ["CoreMLExecutionProvider", "CPUExecutionProvider"],
    )

    assert _resolve_providers() == [
        ("CoreMLExecutionProvider", {"MLComputeUnits": "ALL"}),
        "CPUExecutionProvider",
    ]


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
