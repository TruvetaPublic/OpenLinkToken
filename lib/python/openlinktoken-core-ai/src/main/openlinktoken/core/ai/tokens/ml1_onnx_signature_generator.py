"""Generates deterministic ML1 signatures from ONNX CLS embeddings."""

from __future__ import annotations

import contextlib
import importlib.resources
import json
import logging
import os
import platform
import struct
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

import numpy as np
from tokenizers import Tokenizer

from openlinktoken.core.ai.tokens.ml1_inference_config import ML1InferenceConfig

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def _suppress_ort_stderr():
    """Redirect C-level stderr to /dev/null to silence ORT native error messages."""
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    saved_fd = os.dup(2)
    os.dup2(devnull_fd, 2)
    os.close(devnull_fd)
    try:
        yield
    finally:
        os.dup2(saved_fd, 2)
        os.close(saved_fd)


def _resolve_providers() -> List[str | tuple]:
    """Return the best available ORT execution provider list for this environment.

    On macOS, attempts CoreMLExecutionProvider in subgraph-only mode (flag 0x002),
    which lets CoreML accelerate supported ops while CPU handles the rest.
    Falls back to CPU-only if CoreML is unavailable or fails.
    """
    import onnxruntime as ort

    available = ort.get_available_providers()
    is_macos_native = platform.system() == "Darwin"
    if is_macos_native and "CoreMLExecutionProvider" in available:
        # EnableOnSubgraphOnly: CoreML handles only the ops it supports;
        # unsupported ops fall through to CPU automatically (avoids EP errors
        # from partial graph coverage on BERT-like models).
        return [
            ("CoreMLExecutionProvider", {"EnableOnSubgraphOnly": "1"}),
            "CPUExecutionProvider",
        ]
    return ["CPUExecutionProvider"]


class ML1OnnxSignatureGenerator:
    """Stateful ONNX inference helper for ML1 signature generation."""

    _session = None  # ort.InferenceSession, initialized lazily
    _tokenizer: Optional[Tokenizer] = None
    _active_model_path: Optional[str] = None
    _active_tokenizer_path: Optional[str] = None
    _pad_input_json = "{}"
    _initialization_lock = Lock()

    @classmethod
    def generate_signature(cls, input_json: str) -> str:
        """Generate a deterministic ML1 signature for one input JSON row."""
        signatures = cls.generate_signatures([input_json])
        if not signatures:
            raise RuntimeError("Failed to generate ONNX-based ML1 signature.")
        return signatures[0]

    @classmethod
    def _generate_signature_with_embedding(cls, input_json: str) -> tuple[str, np.ndarray]:
        """Generate a deterministic ML1 signature and embedding for one input JSON row."""
        signatures, embeddings = cls._generate_signatures_with_embeddings([input_json])
        if not signatures:
            raise RuntimeError("Failed to generate ONNX-based ML1 signature.")
        return signatures[0], embeddings[0]

    @classmethod
    def generate_signatures(cls, input_json_rows: List[str]) -> List[str]:
        """Generate deterministic ML1 signatures for multiple rows using batched ONNX inference."""
        signatures, _ = cls._generate_signatures_with_embeddings(input_json_rows)
        return signatures

    @classmethod
    def _generate_signatures_with_embeddings(cls, input_json_rows: List[str]) -> tuple[List[str], List[np.ndarray]]:
        """Generate ML1 hex signatures and embeddings in a single inference pass.

        The embeddings are retained internally for ML1 rotation.

        Args:
            input_json_rows: list of JSON strings representing person records

        Returns:
            (signatures, embeddings) — parallel lists with same length as input
        """
        if not input_json_rows:
            return [], []

        cls._initialize_if_needed()

        configured_batch_size = ML1InferenceConfig.get_batch_size()
        signatures: List[str] = []
        all_embeddings: List[np.ndarray] = []
        total_inference_ms = 0.0

        for start in range(0, len(input_json_rows), configured_batch_size):
            end = min(start + configured_batch_size, len(input_json_rows))
            real_batch = input_json_rows[start:end]
            inference_batch = list(real_batch)
            while len(inference_batch) < configured_batch_size:
                inference_batch.append(cls._pad_input_json)

            batch_embeddings, batch_ms = cls._run_batch_inference(inference_batch)
            total_inference_ms += batch_ms

            for index in range(len(real_batch)):
                signatures.append(cls._serialize_embedding(batch_embeddings[index]))
                all_embeddings.append(batch_embeddings[index])

            if logger.isEnabledFor(logging.INFO):
                logger.info(
                    "ML1 ONNX batch inference: requestedSize=%s, inferenceSize=%s, totalMs=%s, avgMsPerRow=%s",
                    len(real_batch),
                    len(inference_batch),
                    batch_ms,
                    batch_ms / len(real_batch),
                )

        if logger.isEnabledFor(logging.INFO):
            logger.info(
                "ML1 ONNX batch inference summary: rowCount=%s, totalMs=%s, avgMsPerRow=%s",
                len(input_json_rows),
                total_inference_ms,
                total_inference_ms / len(input_json_rows),
            )

        return signatures, all_embeddings

    @classmethod
    def _run_batch_inference(cls, input_json_rows: List[str]) -> tuple[float, float]:
        """Run ONNX inference for one fixed-size batch and return embeddings with elapsed ms."""
        import time

        input_ids_batch, attention_mask_batch, token_type_ids_batch, position_ids_batch = cls._build_inputs(
            input_json_rows
        )
        inputs = {
            "input_ids": input_ids_batch,
            "attention_mask": attention_mask_batch,
        }

        input_names = {model_input.name for model_input in cls._session.get_inputs()}
        if "token_type_ids" in input_names:
            inputs["token_type_ids"] = token_type_ids_batch
        if "position_ids" in input_names:
            inputs["position_ids"] = position_ids_batch

        start = time.perf_counter()
        try:
            outputs = cls._session.run(None, inputs)
        except Exception as e:
            if "CoreML" in str(e) or "CoreMLExecutionProvider" in str(cls._session.get_providers()):
                logger.warning("ML1 ONNX: CoreML runtime error; falling back to CPU and retrying.")
                cls._reinitialize_with_cpu_only()
                outputs = cls._session.run(None, inputs)
            else:
                raise
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        output = outputs[0]
        if output.ndim == 3:
            return output[:, 0, :], elapsed_ms
        if output.ndim == 2:
            return output, elapsed_ms
        raise RuntimeError("Unexpected ONNX output shape for ML1 inference.")

    @classmethod
    def _build_inputs(cls, input_json_rows: List[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Build int64 ONNX tensors from input JSON rows using parallel batch tokenization and dynamic padding."""
        max_sequence_length = ML1InferenceConfig.get_max_sequence_length()
        batch_size = len(input_json_rows)

        # Parallel Rust tokenization — encode_batch processes all rows concurrently
        encodings = cls._tokenizer.encode_batch(input_json_rows)

        # Dynamic padding: use actual max token length in this batch (capped at max_sequence_length)
        dynamic_max = max((len(enc.ids) for enc in encodings), default=1)
        seq_len = min(dynamic_max, max_sequence_length)

        input_ids_batch = np.zeros((batch_size, seq_len), dtype=np.int64)
        attention_mask_batch = np.zeros((batch_size, seq_len), dtype=np.int64)
        token_type_ids_batch = np.zeros((batch_size, seq_len), dtype=np.int64)
        position_ids_batch = np.tile(np.arange(seq_len, dtype=np.int64), (batch_size, 1))

        for row_index, encoding in enumerate(encodings):
            cls._copy_fixed_length(input_ids_batch[row_index], encoding.ids or [])
            cls._copy_fixed_length(attention_mask_batch[row_index], encoding.attention_mask or [])
            cls._copy_fixed_length(token_type_ids_batch[row_index], encoding.type_ids or [])

        return input_ids_batch, attention_mask_batch, token_type_ids_batch, position_ids_batch

    @staticmethod
    def _copy_fixed_length(target: np.ndarray, values: List[int]) -> None:
        """Copy source values into fixed-length target array with truncation."""
        copy_length = min(len(values), target.shape[0])
        if copy_length > 0:
            target[:copy_length] = np.asarray(values[:copy_length], dtype=np.int64)

    @classmethod
    def _initialize_if_needed(cls) -> None:
        """Initialize ONNX session and tokenizer if configuration changed or not yet initialized."""
        with cls._initialization_lock:
            with _suppress_ort_stderr():
                import onnxruntime as ort

            model_path = ML1InferenceConfig.get_model_path()
            tokenizer_path = ML1InferenceConfig.get_tokenizer_path()

            already_initialized = (
                cls._session is not None
                and cls._tokenizer is not None
                and model_path == cls._active_model_path
                and tokenizer_path == cls._active_tokenizer_path
            )
            if already_initialized:
                return

            cls._close_session()

            resolved_model_path = cls._resolve_path(model_path)
            if resolved_model_path.name == "model.onnx":
                data_path = resolved_model_path.with_name("model.onnx.data")
                if not data_path.is_file():
                    raise FileNotFoundError(
                        f"ML1 model data file not found beside the model: {data_path}. "
                        "Place model.onnx.data beside model.onnx."
                    )
            resolved_tokenizer_path = cls._resolve_path(tokenizer_path)

            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            session_options.execution_mode = ort.ExecutionMode.ORT_PARALLEL
            session_options.enable_mem_pattern = True
            session_options.enable_cpu_mem_arena = True
            num_threads = ML1InferenceConfig.get_num_threads()
            session_options.intra_op_num_threads = num_threads
            session_options.inter_op_num_threads = num_threads

            with _suppress_ort_stderr():
                providers = _resolve_providers()
            try:
                with _suppress_ort_stderr():
                    cls._session = ort.InferenceSession(
                        str(resolved_model_path),
                        sess_options=session_options,
                        providers=providers,
                    )
            except Exception as e:
                logger.warning("ML1 ONNX: provider init failed (%s), retrying with CPUExecutionProvider only", e)
                with _suppress_ort_stderr():
                    cls._session = ort.InferenceSession(
                        str(resolved_model_path),
                        sess_options=session_options,
                        providers=["CPUExecutionProvider"],
                    )
            active = cls._session.get_providers()
            if "CoreMLExecutionProvider" in active:
                # Probe with a minimal input to detect runtime failures early
                try:
                    with _suppress_ort_stderr():
                        cls._probe_coreml()
                except Exception:
                    logger.warning("ML1 ONNX: CoreML probe failed; falling back to CPU.")
                    cls._reinitialize_with_cpu_only()
                else:
                    logger.info("ML1 ONNX: CoreML active (subgraph-only) — Neural Engine / GPU acceleration enabled")
            else:
                logger.info("ML1 ONNX: running on CPUExecutionProvider")

            cls._tokenizer = Tokenizer.from_file(str(resolved_tokenizer_path))
            cls._active_model_path = model_path
            cls._active_tokenizer_path = tokenizer_path

    @classmethod
    def _probe_coreml(cls) -> None:
        """Run a minimal inference to verify CoreML works at runtime for this model.

        Uses the configured batch size since CoreML may compile shape-specific
        subgraphs and fail if the real batch size differs from the probe size.
        """
        batch_size = ML1InferenceConfig.get_batch_size()
        max_seq = ML1InferenceConfig.get_max_sequence_length()
        dummy = np.zeros((batch_size, max_seq), dtype=np.int64)
        inputs = {"input_ids": dummy, "attention_mask": dummy}
        input_names = {m.name for m in cls._session.get_inputs()}
        if "token_type_ids" in input_names:
            inputs["token_type_ids"] = dummy
        if "position_ids" in input_names:
            inputs["position_ids"] = np.tile(np.arange(max_seq, dtype=np.int64), (batch_size, 1))
        cls._session.run(None, inputs)

    @classmethod
    def _close_session(cls) -> None:
        """Close active ONNX session."""
        cls._session = None

    @classmethod
    def _reinitialize_with_cpu_only(cls) -> None:
        """Reinitialize the ONNX session using CPUExecutionProvider only."""
        import onnxruntime as ort

        model_path = ML1InferenceConfig.get_model_path()
        resolved_model_path = cls._resolve_path(model_path)
        cls._close_session()
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session_options.execution_mode = ort.ExecutionMode.ORT_PARALLEL
        session_options.enable_mem_pattern = True
        session_options.enable_cpu_mem_arena = True
        num_threads = ML1InferenceConfig.get_num_threads()
        session_options.intra_op_num_threads = num_threads
        session_options.inter_op_num_threads = num_threads
        with _suppress_ort_stderr():
            cls._session = ort.InferenceSession(
                str(resolved_model_path),
                sess_options=session_options,
                providers=["CPUExecutionProvider"],
            )
        logger.info("ML1 ONNX: reinitialized with CPUExecutionProvider")

    @classmethod
    def _resolve_path(cls, configured_path: str) -> Path:
        """Resolve classpath-style paths and regular filesystem paths.

        Resolution order:
        1. Bundled package data via importlib.resources (installed wheel or CLI).
        2. Filesystem walk up from the source file (source checkout / development).
        """
        if not configured_path or not configured_path.strip():
            raise ValueError("ML1 asset path must not be blank.")
        if not configured_path.startswith("classpath:"):
            resolved_path = Path(configured_path).expanduser().absolute()
            if not resolved_path.is_file():
                raise FileNotFoundError(f"Configured ML1 asset path does not exist: {resolved_path}")
            return resolved_path

        resource_path = configured_path[len("classpath:") :]
        filename = Path(resource_path).name
        local_path = cls._find_local_asset(filename, resource_path)
        if local_path is not None:
            return local_path
        normalized = resource_path.lstrip("/")
        raise FileNotFoundError(
            f"ML1 resource not found: {filename}. Core-AI packages do not download ML1 assets. "
            f"Place it beside the installed package module at "
            f"openlinktoken/core/ai/tokens/{filename}, place it at resources/{normalized} "
            "in a source checkout, or configure an explicit filesystem path."
        )

    @classmethod
    def _find_local_asset(cls, filename: str, resource_path: str) -> Optional[Path]:
        """Find an asset in an installed package or source checkout."""
        try:
            ref = importlib.resources.files("openlinktoken.core.ai.tokens") / filename
            if ref.is_file():
                return Path(ref)
        except (FileNotFoundError, TypeError, AttributeError):
            pass

        normalized = resource_path.lstrip("/")
        this_file = Path(__file__).resolve()
        for parent in this_file.parents:
            candidate = parent / "resources" / normalized
            if candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _serialize_embedding(embedding: np.ndarray) -> str:
        """Serialize embedding as big-endian float32 bytes encoded to lowercase hex."""
        return b"".join(
            struct.pack(">I", struct.unpack(">I", struct.pack(">f", float(value)))[0]) for value in embedding
        ).hex()


def ml1_payload_to_json(payload: Dict[str, str]) -> str:
    """Convert an ordered payload map to JSON used for ML1 tokenization.

    Uses Python's default separators (", " and ": ") to match the format
    produced by generate_embeddings.py, ensuring identical tokenizer input.
    Non-ASCII characters are escaped as \\uXXXX (ensure_ascii=True default).
    """
    return json.dumps(payload)
