#!/usr/bin/env python3
"""
Quantize the T6 ONNX model from FP32 to INT8 (dynamic weight quantization).

INT8 quantization reduces model size from ~1.2 GB to ~321 MB and improves
CPU inference throughput by ~25% with negligible accuracy loss for embeddings.

IMPORTANT: The INT8 model produces slightly different float values than FP32.
           All systems (Java + Python) must use the same model version to
           produce identical T6 tokens.

Usage:
    python3 tools/quantize_t6_model.py

Inputs (must exist):
    lib/java/opentoken/src/main/resources/t6/model.onnx
    lib/java/opentoken/src/main/resources/t6/model.onnx.data

Output:
    lib/java/opentoken/src/main/resources/t6/model_int8.onnx  (321 MB, self-contained)
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
T6_DIR = REPO_ROOT / "lib/java/opentoken/src/main/resources/t6"
INPUT_MODEL = T6_DIR / "model.onnx"
OUTPUT_MODEL = T6_DIR / "model_int8.onnx"


def main() -> None:
    try:
        from onnxruntime.quantization import QuantType, quantize_dynamic
    except ImportError:
        print("ERROR: onnxruntime not installed. Run: pip3 install onnxruntime onnx")
        sys.exit(1)

    if not INPUT_MODEL.exists():
        print(f"ERROR: FP32 model not found at {INPUT_MODEL}")
        print("       Ensure model.onnx and model.onnx.data are present in the t6/ directory.")
        sys.exit(1)

    if OUTPUT_MODEL.exists():
        print(f"INT8 model already exists at {OUTPUT_MODEL} ({OUTPUT_MODEL.stat().st_size // 1_048_576} MB)")
        print("Delete it and re-run to regenerate.")
        sys.exit(0)

    print(f"Quantizing {INPUT_MODEL} → {OUTPUT_MODEL}")
    print("This may take 5–10 minutes...")

    quantize_dynamic(
        model_input=INPUT_MODEL,
        model_output=OUTPUT_MODEL,
        weight_type=QuantType.QInt8,
        optimize_model=False,  # avoid shape inference issues with external data
    )

    size_mb = OUTPUT_MODEL.stat().st_size // 1_048_576
    print(f"Done. Output: {OUTPUT_MODEL} ({size_mb} MB)")


if __name__ == "__main__":
    main()
