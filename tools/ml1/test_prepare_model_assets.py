"""Tests for preparing and validating ML1 model artifacts."""

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper
from prepare_model_assets import _io_contract, prepare_model_assets, validate_model_assets


def _write_manifest(asset_dir: Path) -> None:
    """Write fixture hashes and sizes for the three model assets."""
    assets = {}
    for filename in ("model.onnx", "model.onnx.data", "tokenizer.json"):
        asset_path = asset_dir / filename
        content = asset_path.read_bytes()
        assets[filename] = {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}
    (asset_dir / "asset-manifest.json").write_text(json.dumps({"assets": assets}), encoding="utf-8")


def _create_source_model(source_dir: Path) -> None:
    """Create a small FP32 model with external weights and fixture tokenizer data."""
    source_dir.mkdir()
    graph = helper.make_graph(
        [helper.make_node("MatMul", ["input", "weights"], ["output"])],
        "ml1-fixture",
        [helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 32])],
        [helper.make_tensor_value_info("output", TensorProto.FLOAT, [1, 32])],
        [
            onnx.numpy_helper.from_array(
                np.eye(32, dtype=np.float32),
                name="weights",
            )
        ],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    onnx.save_model(
        model,
        str(source_dir / "model.onnx"),
        save_as_external_data=True,
        all_tensors_to_one_file=True,
        location="model.onnx.data",
        size_threshold=1024,
    )
    (source_dir / "tokenizer.json").write_text('{"fixture":"tokenizer"}', encoding="utf-8")
    _write_manifest(source_dir)


def test_prepares_fp16_assets_without_changing_the_fp32_source(tmp_path):
    """FP16 staging preserves the source and public model contract."""
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "fp16"
    _create_source_model(source_dir)
    source_model_path = source_dir / "model_fp32.onnx"
    shutil.copyfile(source_dir / "model.onnx", source_model_path)
    shutil.copyfile(source_dir / "model.onnx.data", source_dir / "model_fp32.onnx.data")
    source_files = {path.name: path.read_bytes() for path in source_dir.iterdir()}
    source_model = onnx.load_model(str(source_model_path), load_external_data=False)

    prepare_model_assets(source_dir, output_dir, "v1-fp16", source_model_path)

    validate_model_assets(output_dir, "v1-fp16")
    converted_model = onnx.load_model(str(output_dir / "model.onnx"), load_external_data=False)
    assert _io_contract(converted_model) == _io_contract(source_model)
    assert any(initializer.data_type == TensorProto.FLOAT16 for initializer in converted_model.graph.initializer)
    assert (output_dir / "tokenizer.json").read_bytes() == source_files["tokenizer.json"]
    assert (output_dir / "model.onnx.data").stat().st_size < len(source_files["model.onnx.data"])
    assert {path.name: path.read_bytes() for path in source_dir.iterdir()} == source_files

    manifest = json.loads((output_dir / "asset-manifest.json").read_text(encoding="utf-8"))
    for filename in ("model.onnx", "model.onnx.data", "tokenizer.json"):
        content = (output_dir / filename).read_bytes()
        assert manifest["assets"][filename] == {
            "sha256": hashlib.sha256(content).hexdigest(),
            "size": len(content),
        }


def test_stages_fp32_assets_unchanged(tmp_path):
    """FP32 staging preserves the original files and validates CPU inference."""
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "fp32"
    _create_source_model(source_dir)

    prepare_model_assets(source_dir, output_dir, "v1")

    validate_model_assets(output_dir, "v1")
    assert {path.name: path.read_bytes() for path in output_dir.iterdir()} == {
        path.name: path.read_bytes() for path in source_dir.iterdir()
    }


def test_rejects_bad_source_manifest_before_creating_output(tmp_path):
    """An invalid FP32 source cannot produce a staged artifact."""
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "fp16"
    _create_source_model(source_dir)
    (source_dir / "model.onnx.data").write_bytes(b"corrupt")

    try:
        prepare_model_assets(source_dir, output_dir, "v1-fp16")
    except ValueError as error:
        assert "Unexpected size" in str(error)
    else:
        raise AssertionError("Expected source manifest verification to fail")

    assert not output_dir.exists()


def test_rejects_explicit_source_model_for_fp32_tag(tmp_path):
    """An alternate FP32 source is only valid for preparing v1-fp16."""
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "fp32"
    _create_source_model(source_dir)

    try:
        prepare_model_assets(source_dir, output_dir, "v1", source_dir / "model.onnx")
    except ValueError as error:
        assert "only be used to prepare v1-fp16" in str(error)
    else:
        raise AssertionError("Expected an explicit FP32 source model to be rejected for v1")

    assert not output_dir.exists()


def test_rejects_fp16_tag_without_a_matching_source_model(tmp_path):
    """Only v1-fp16 can be generated from the currently checked-in v1 model."""
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "fp16"
    _create_source_model(source_dir)

    try:
        prepare_model_assets(source_dir, output_dir, "v2-fp16")
    except ValueError as error:
        assert "only v1-fp16" in str(error)
    else:
        raise AssertionError("Expected unsupported FP16 source tag to fail")

    assert not output_dir.exists()
