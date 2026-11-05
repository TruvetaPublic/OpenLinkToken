#!/usr/bin/env python3
"""Prepare and validate the ML1 model assets published to GHCR."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import onnx
import onnxruntime as ort
from onnx import TensorProto
from onnxruntime.transformers.float16 import convert_float_to_float16
from onnxruntime.transformers.onnx_model import OnnxModel
from onnxruntime.transformers.optimizer import optimize_model

MODEL_FILES = ("model.onnx", "model.onnx.data", "tokenizer.json")
REQUIRED_FILES = (*MODEL_FILES, "asset-manifest.json")
MODEL_TAG_PATTERN = re.compile(r"^v[0-9]+(?:-fp16)?$")
ORT_INPUT_DTYPES = {
    "tensor(bool)": np.bool_,
    "tensor(double)": np.float64,
    "tensor(float)": np.float32,
    "tensor(float16)": np.float16,
    "tensor(int8)": np.int8,
    "tensor(int16)": np.int16,
    "tensor(int32)": np.int32,
    "tensor(int64)": np.int64,
    "tensor(uint8)": np.uint8,
    "tensor(uint16)": np.uint16,
    "tensor(uint32)": np.uint32,
    "tensor(uint64)": np.uint64,
}


def _validate_model_tag(model_tag: str) -> bool:
    """Validate a supported model tag and return whether it selects FP16.

    Args:
        model_tag: Immutable OCI tag requested by the publisher.

    Returns:
        True when the tag selects the v1 FP16 conversion.
    """
    if not MODEL_TAG_PATTERN.fullmatch(model_tag):
        raise ValueError(f"Invalid ML1 model tag: {model_tag} (expected vN or vN-fp16)")
    if model_tag.endswith("-fp16") and model_tag != "v1-fp16":
        raise ValueError("FP16 model preparation currently supports only v1-fp16")
    return model_tag == "v1-fp16"


def _sha256_file(path: Path) -> str:
    """Return a file's SHA-256 digest.

    Args:
        path: File to hash.

    Returns:
        Lowercase hexadecimal SHA-256 digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_manifest(asset_dir: Path) -> dict[str, Any]:
    """Read and validate the required entries in an ML1 asset manifest.

    Args:
        asset_dir: Directory containing the model assets.

    Returns:
        Parsed manifest mapping.
    """
    manifest_path = asset_dir / "asset-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("assets"), dict):
        raise ValueError(f"Invalid ML1 asset manifest: {manifest_path}")

    for filename in MODEL_FILES:
        metadata = manifest["assets"].get(filename)
        if (
            not isinstance(metadata, dict)
            or not isinstance(metadata.get("size"), int)
            or isinstance(metadata.get("size"), bool)
            or not isinstance(metadata.get("sha256"), str)
            or not re.fullmatch(r"[0-9a-fA-F]{64}", metadata["sha256"])
        ):
            raise ValueError(f"Invalid ML1 asset manifest entry for {filename}")

        asset_path = asset_dir / filename
        if not asset_path.is_file():
            raise ValueError(f"ML1 asset is missing: {asset_path}")
        if asset_path.stat().st_size != metadata["size"]:
            raise ValueError(f"Unexpected size for ML1 asset {filename}")
        if _sha256_file(asset_path) != metadata["sha256"].lower():
            raise ValueError(f"SHA-256 verification failed for {filename}")

    return manifest


def _write_manifest(asset_dir: Path) -> None:
    """Write a manifest for the three staged ML1 assets.

    Args:
        asset_dir: Directory containing the staged model assets.
    """
    assets = {
        filename: {
            "sha256": _sha256_file(asset_dir / filename),
            "size": (asset_dir / filename).stat().st_size,
        }
        for filename in MODEL_FILES
    }
    (asset_dir / "asset-manifest.json").write_text(
        json.dumps({"assets": assets}, indent=2) + "\n",
        encoding="utf-8",
    )


def _value_info_contract(value_info: Any) -> tuple[str, int, tuple[int | str | None, ...]]:
    """Return a tensor value's public name, element type, and dimensions.

    Args:
        value_info: ONNX graph input or output metadata.

    Returns:
        Tuple containing the name, ONNX element type, and shape dimensions.
    """
    tensor_type = value_info.type.tensor_type
    dimensions = tuple(
        dimension.dim_value if dimension.HasField("dim_value") else dimension.dim_param or None
        for dimension in tensor_type.shape.dim
    )
    return value_info.name, tensor_type.elem_type, dimensions


def _io_contract(model: onnx.ModelProto) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    """Return the input and output contracts for an ONNX model.

    Args:
        model: ONNX model to inspect.

    Returns:
        Input and output contracts, preserving graph order.
    """
    inputs = tuple(_value_info_contract(value) for value in model.graph.input)
    outputs = tuple(_value_info_contract(value) for value in model.graph.output)
    return inputs, outputs


def _sample_inputs(session: ort.InferenceSession) -> dict[str, np.ndarray]:
    """Build small deterministic tensors matching an ONNX session's inputs.

    Args:
        session: ONNX Runtime session to inspect.

    Returns:
        Mapping of model input names to synthetic tensors.
    """
    inputs: dict[str, np.ndarray] = {}
    for model_input in session.get_inputs():
        dtype = ORT_INPUT_DTYPES.get(model_input.type)
        if dtype is None:
            raise ValueError(f"Unsupported ONNX input type for validation: {model_input.type}")
        shape = tuple(
            dimension if isinstance(dimension, int) and dimension > 0 else (1 if index == 0 else 8)
            for index, dimension in enumerate(model_input.shape)
        )
        values = np.zeros(shape, dtype=dtype)
        if model_input.name == "attention_mask":
            values.fill(1)
        inputs[model_input.name] = values
    return inputs


def _validate_inference(model_path: Path, provider: str) -> None:
    """Run a synthetic inference and validate provider use and finite outputs.

    Args:
        model_path: Path to the ONNX graph.
        provider: ONNX Runtime execution provider to validate.
    """
    session_options = ort.SessionOptions()
    profile_directory: tempfile.TemporaryDirectory[str] | None = None
    if provider == "CUDAExecutionProvider":
        profile_directory = tempfile.TemporaryDirectory(prefix="ml1-onnx-profile-")
        session_options.enable_profiling = True
        session_options.profile_file_prefix = str(Path(profile_directory.name) / "ml1")

    try:
        session = ort.InferenceSession(str(model_path), sess_options=session_options, providers=[provider])
        if provider not in session.get_providers():
            raise RuntimeError(f"ONNX Runtime did not enable the requested provider: {provider}")

        outputs = session.run(None, _sample_inputs(session))
        if not outputs:
            raise RuntimeError("The ML1 model produced no inference outputs")

        output_metadata = session.get_outputs()
        if len(outputs) != len(output_metadata):
            raise RuntimeError("The ML1 model returned an unexpected number of outputs")
        for output, metadata in zip(outputs, output_metadata):
            values = np.asarray(output)
            if not values.size or not np.isfinite(values).all():
                raise RuntimeError(f"The ML1 model produced empty or non-finite output for {metadata.name}")
            if values.ndim != len(metadata.shape):
                raise RuntimeError(f"The ML1 model produced an unexpected output rank for {metadata.name}")
            for expected, actual in zip(metadata.shape, values.shape):
                if isinstance(expected, int) and expected > 0 and expected != actual:
                    raise RuntimeError(f"The ML1 model produced an unexpected output shape for {metadata.name}")

        if provider == "CUDAExecutionProvider":
            profile_path = Path(session.end_profiling())
            events = json.loads(profile_path.read_text(encoding="utf-8"))
            if not any(
                event.get("cat") == "Node" and event.get("args", {}).get("provider") == provider for event in events
            ):
                raise RuntimeError("The ML1 model did not execute any nodes with CUDAExecutionProvider")
    finally:
        if profile_directory is not None:
            profile_directory.cleanup()


def validate_model_assets(asset_dir: Path, model_tag: str, provider: str = "CPUExecutionProvider") -> None:
    """Verify an ML1 artifact and run it using the selected execution provider.

    Args:
        asset_dir: Directory containing the four OCI artifact files.
        model_tag: Tag describing the expected model precision.
        provider: ONNX Runtime execution provider to exercise.
    """
    fp16_expected = _validate_model_tag(model_tag)
    _read_manifest(asset_dir)
    model_path = asset_dir / "model.onnx"
    onnx.checker.check_model(str(model_path))
    model = onnx.load_model(str(model_path), load_external_data=False)

    external_locations = {
        entry.value
        for initializer in model.graph.initializer
        for entry in initializer.external_data
        if entry.key == "location"
    }
    if external_locations != {"model.onnx.data"}:
        raise ValueError(f"Unexpected ML1 external data locations: {sorted(external_locations)}")

    fp16_initializers = sum(initializer.data_type == TensorProto.FLOAT16 for initializer in model.graph.initializer)
    if fp16_expected and fp16_initializers == 0:
        raise ValueError("The v1-fp16 artifact contains no FP16 model weights")
    if not fp16_expected and fp16_initializers > 0:
        raise ValueError(f"The {model_tag} artifact unexpectedly contains FP16 model weights")

    _validate_inference(model_path, provider)


def _prepare_fp16_assets(source_model_path: Path, tokenizer_path: Path, staging_dir: Path) -> tuple[int, int]:
    """Convert and fuse the full-output FP32 ONNX model.

    Args:
        source_model_path: FP32 ONNX model with its external-data sidecar beside it.
        tokenizer_path: Tokenizer JSON to include with the converted model.
        staging_dir: New temporary directory for the converted artifact.

    Returns:
        Tuple containing the number of FP16 initializers and fused BiasGelu nodes.
    """
    source_model_path = source_model_path.resolve()
    source_data_path = source_model_path.with_name(f"{source_model_path.name}.data")
    if not source_model_path.is_file():
        raise FileNotFoundError(f"FP32 source model is missing: {source_model_path}")
    if not source_data_path.is_file():
        raise FileNotFoundError(f"FP32 source model external data is missing: {source_data_path}")

    onnx.checker.check_model(str(source_model_path))
    source_model = onnx.load_model(str(source_model_path), load_external_data=True)
    source_contract = _io_contract(source_model)
    with warnings.catch_warnings(record=True) as conversion_warnings:
        warnings.simplefilter("always", UserWarning)
        converted_model = convert_float_to_float16(source_model, keep_io_types=True)
    if conversion_warnings:
        examples = "; ".join(dict.fromkeys(str(item.message) for item in conversion_warnings[:3]))
        print(
            f"Warning: FP16 conversion adjusted {len(conversion_warnings)} values; examples: {examples}",
            file=sys.stderr,
        )
    if _io_contract(converted_model) != source_contract:
        raise RuntimeError("FP16 conversion changed the model input or output contract")

    OnnxModel(converted_model).topological_sort()
    del source_model
    with tempfile.TemporaryDirectory(dir=staging_dir, prefix=".ml1-fp16-build-") as build_directory:
        build_dir = Path(build_directory)
        fp16_path = build_dir / "model_fp16.onnx"
        fused_dir = build_dir / "fused"
        fused_dir.mkdir()
        fused_path = fused_dir / "model.onnx"
        onnx.save_model(
            converted_model,
            str(fp16_path),
            save_as_external_data=True,
            all_tensors_to_one_file=True,
            location=f"{fp16_path.name}.data",
            size_threshold=0,
        )
        del converted_model
        onnx.checker.check_model(str(fp16_path))

        optimized_model = optimize_model(
            str(fp16_path),
            model_type="bert",
            num_heads=16,
            hidden_size=1024,
            opt_level=0,
        )
        optimized_model.save_model_to_file(str(fused_path), use_external_data_format=True)
        onnx.checker.check_model(str(fused_path))

        fused_graph = onnx.load_model(str(fused_path), load_external_data=False)
        if _io_contract(fused_graph) != source_contract:
            raise RuntimeError("BERT optimization changed the model input or output contract")
        shutil.copyfile(fused_path, staging_dir / "model.onnx")
        shutil.copyfile(
            fused_path.with_name(f"{fused_path.name}.data"),
            staging_dir / "model.onnx.data",
        )
        onnx.checker.check_model(str(staging_dir / "model.onnx"))

    fp16_initializers = sum(
        initializer.data_type == TensorProto.FLOAT16 for initializer in fused_graph.graph.initializer
    )
    bias_gelu_count = sum(
        node.domain == "com.microsoft" and node.op_type == "BiasGelu" for node in fused_graph.graph.node
    )
    if fp16_initializers == 0:
        raise RuntimeError("FP16 conversion produced no FP16 model weights")

    shutil.copyfile(tokenizer_path, staging_dir / "tokenizer.json")
    converted_weights = (staging_dir / "model.onnx.data").stat().st_size
    source_weights = source_data_path.stat().st_size
    if converted_weights >= source_weights:
        raise RuntimeError("FP16 conversion did not reduce the external model weight size")
    return fp16_initializers, bias_gelu_count


def prepare_model_assets(
    source_dir: Path,
    output_dir: Path,
    model_tag: str,
    source_model_path: Path | None = None,
) -> None:
    """Stage an immutable FP32 or FP16 artifact without changing source assets.

    Args:
        source_dir: Directory containing checked-in FP32 model assets.
        output_dir: New directory to create for the staged artifact.
        model_tag: Immutable OCI model tag to prepare.
        source_model_path: Optional full-output FP32 ONNX model to convert for v1-fp16.
    """
    fp16 = _validate_model_tag(model_tag)
    source_dir = source_dir.resolve()
    output_dir = output_dir.resolve()
    if source_model_path is not None and not fp16:
        raise ValueError("An explicit source model can only be used to prepare v1-fp16")
    source_model_path = (source_model_path or source_dir / "model.onnx").resolve()
    if source_dir == output_dir:
        raise ValueError("The output directory must be separate from the source model directory")
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    _read_manifest(source_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=output_dir.parent, prefix=f".{output_dir.name}-") as temporary_dir:
        staging_dir = Path(temporary_dir) / "assets"
        staging_dir.mkdir()
        if fp16:
            initializer_count, bias_gelu_count = _prepare_fp16_assets(
                source_model_path,
                source_dir / "tokenizer.json",
                staging_dir,
            )
            _write_manifest(staging_dir)
            validate_model_assets(staging_dir, model_tag)
            source_data_path = source_model_path.with_name(f"{source_model_path.name}.data")
            source_size = source_data_path.stat().st_size
            converted_size = (staging_dir / "model.onnx.data").stat().st_size
            print(
                f"Converted {initializer_count} initializers to FP16 and fused {bias_gelu_count} BiasGelu nodes; "
                f"external weights {source_size} -> {converted_size} bytes."
            )
        else:
            for filename in REQUIRED_FILES:
                shutil.copyfile(source_dir / filename, staging_dir / filename)
            validate_model_assets(staging_dir, model_tag)

        staging_dir.rename(output_dir)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-tag", required=True, help="OCI tag to prepare or validate")
    parser.add_argument("--provider", default="CPUExecutionProvider", help="ONNX Runtime execution provider")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--source-dir", type=Path, help="Checked-in FP32 model asset directory to stage")
    mode.add_argument("--validate-dir", type=Path, help="Already-staged model asset directory to validate")
    parser.add_argument("--source-model", type=Path, help="Optional full-output FP32 ONNX model for v1-fp16")
    parser.add_argument("--output-dir", type=Path, help="New directory for staged assets")
    return parser.parse_args()


def main() -> None:
    """Prepare a staged artifact or validate an existing artifact."""
    args = _parse_args()
    if args.source_dir is not None:
        if args.output_dir is None:
            raise SystemExit("--output-dir is required when preparing model assets")
        prepare_model_assets(args.source_dir, args.output_dir, args.model_tag, args.source_model)
        return
    if args.source_model is not None:
        raise SystemExit("--source-model can only be used with --source-dir")
    if args.output_dir is not None:
        raise SystemExit("--output-dir cannot be used with --validate-dir")
    validate_model_assets(args.validate_dir, args.model_tag, args.provider)


if __name__ == "__main__":
    main()
