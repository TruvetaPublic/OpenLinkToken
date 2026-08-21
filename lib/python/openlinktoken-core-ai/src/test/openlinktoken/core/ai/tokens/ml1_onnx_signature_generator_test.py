import pytest

from openlinktoken.core.ai.tokens.ml1_onnx_signature_generator import (
    ML1OnnxSignatureGenerator,
)


def test_empty_signatures_do_not_initialize_onnx():
    """Empty input should return without initializing ONNX resources."""
    assert ML1OnnxSignatureGenerator.generate_signatures([]) == []


def test_empty_signatures_and_embeddings_are_empty():
    """The internal batched path should return parallel empty collections."""
    assert ML1OnnxSignatureGenerator._generate_signatures_with_embeddings([]) == ([], [])


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
