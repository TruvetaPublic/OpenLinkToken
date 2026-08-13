import platform
from pathlib import Path
from unittest.mock import Mock

import onnxruntime as ort

from openlinktoken.core.ai.tokens.ml1_onnx_signature_generator import (
    ML1OnnxSignatureGenerator,
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
