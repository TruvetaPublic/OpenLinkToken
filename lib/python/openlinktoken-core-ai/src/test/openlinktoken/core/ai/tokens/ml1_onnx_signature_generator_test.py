import hashlib
import io
import platform
from pathlib import Path
from unittest.mock import Mock

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


def test_asset_url_uses_public_lfs_endpoint_and_configured_ref():
    """Asset URLs should preserve slash-separated Git refs."""
    assert (
        ML1OnnxSignatureGenerator._asset_url("tokenizer.json", "release/2.1.1")
        == "https://raw.githubusercontent.com/TruvetaPublic/OpenLinkToken/"
        "release/2.1.1/resources/inferencing/ml1/tokenizer.json"
    )


def test_asset_url_rejects_path_traversal_refs():
    """Asset refs must not escape the cache directory or URL path."""
    with pytest.raises(ValueError):
        ML1OnnxSignatureGenerator._asset_url("release/../other", "model.onnx")


def test_explicit_filesystem_paths_are_not_downloaded(monkeypatch, tmp_path):
    """Configured local paths should resolve directly and never trigger asset lookup."""
    monkeypatch.setenv("OPENLINKTOKEN_ML1_OFFLINE", "1")
    model_path = tmp_path / "model.onnx"
    model_path.touch()

    assert ML1OnnxSignatureGenerator._resolve_path(str(model_path)) == model_path


def test_offline_mode_rejects_missing_default_assets(monkeypatch):
    """Offline mode should fail clearly instead of attempting a remote download."""
    monkeypatch.setenv("OPENLINKTOKEN_ML1_OFFLINE", "1")
    monkeypatch.setattr(
        ML1OnnxSignatureGenerator,
        "_find_local_asset",
        classmethod(lambda cls, filename, resource_path: None),
    )

    with pytest.raises(RuntimeError, match="offline"):
        ML1OnnxSignatureGenerator._resolve_path("classpath:/inferencing/ml1/tokenizer.json")


def test_offline_mode_allows_bundled_package_assets(monkeypatch, tmp_path):
    """Offline mode should still use assets resolved from package resources."""
    tokenizer_path = tmp_path / "tokenizer.json"
    tokenizer_path.touch()
    monkeypatch.setenv("OPENLINKTOKEN_ML1_OFFLINE", "1")
    monkeypatch.setattr(
        ML1OnnxSignatureGenerator,
        "_find_local_asset",
        classmethod(lambda cls, filename, resource_path: tokenizer_path),
    )

    assert ML1OnnxSignatureGenerator._resolve_path("classpath:/inferencing/ml1/tokenizer.json") == tokenizer_path


def test_source_manifest_exposes_verified_asset_metadata():
    """The source checkout manifest should be readable without touching model assets."""
    manifest = ML1OnnxSignatureGenerator.read_asset_manifest()

    assert manifest["assets"]["model.onnx.data"]["size"] == 1340579840
    assert len(manifest["assets"]["tokenizer.json"]["sha256"]) == 64


def test_downloaded_asset_is_verified_and_atomically_cached(monkeypatch, tmp_path):
    """A small fake asset should be downloaded, verified, and cached without a large model."""
    payload = b"small tokenizer fixture"
    digest = hashlib.sha256(payload).hexdigest()
    manifest = {"assets": {"tokenizer.json": {"sha256": digest, "size": len(payload)}}}

    class FakeResponse(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

    monkeypatch.setattr(
        ML1OnnxSignatureGenerator,
        "_load_asset_manifest",
        classmethod(lambda cls: manifest),
    )
    monkeypatch.setattr(
        ML1OnnxSignatureGenerator,
        "_find_local_asset",
        classmethod(lambda cls, filename, resource_path: None),
    )
    monkeypatch.setattr(
        "openlinktoken.core.ai.tokens.ml1_onnx_signature_generator.urllib.request.urlopen",
        lambda *args, **kwargs: FakeResponse(payload),
    )
    ML1InferenceConfig.configure(True, "", "", 1, configured_cache_dir=str(tmp_path))

    cached_path = ML1OnnxSignatureGenerator._resolve_path("classpath:/inferencing/ml1/tokenizer.json")

    assert cached_path.name == "tokenizer.json"
    assert cached_path.parent == (tmp_path / "release" / "2.1.1").absolute()
    assert cached_path.read_bytes() == payload
    assert not list(cached_path.parent.glob("*.tmp"))
