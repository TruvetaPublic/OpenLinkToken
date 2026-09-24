#!/usr/bin/env python3
"""Generate ML1 embeddings directly with the bundled ONNX model."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterator, Mapping

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from openlinktoken.attributes.person.birth_date_attribute import BirthDateAttribute
from openlinktoken.attributes.person.first_name_attribute import FirstNameAttribute
from openlinktoken.attributes.person.last_name_attribute import LastNameAttribute
from openlinktoken.attributes.person.postal_code_attribute import PostalCodeAttribute
from openlinktoken.attributes.person.sex_attribute import SexAttribute
from openlinktoken.core.ai.tokens.ml1_onnx_signature_generator import (
    ML1OnnxSignatureGenerator,
    _resolve_providers,
)

MODEL_FIELDS = (
    ("PostalCode", "PostalCode", PostalCodeAttribute),
    ("BirthDate", "Birthdate", BirthDateAttribute),
    ("FirstName", "GivenName", FirstNameAttribute),
    ("LastName", "Surname", LastNameAttribute),
    ("Sex", "Gender", SexAttribute),
)
DEFAULT_MODEL = "resources/inferencing/ml1/model.onnx"
DEFAULT_TOKENIZER = "resources/inferencing/ml1/tokenizer.json"
DEFAULT_MAX_SEQUENCE_LENGTH = 128
DEFAULT_BATCH_SIZE = 64
DEFAULT_NUM_THREADS = os.cpu_count() or 1


def _payloads_from_jsonl(path: Path) -> Iterator[str]:
    """Read person records, normalize ML1 fields, and serialize model payloads."""
    with path.open(encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, Mapping):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")

            payload: dict[str, str] = {}
            for input_field, model_field, attribute_type in MODEL_FIELDS:
                value = record.get(input_field)
                if not isinstance(value, str) or not value:
                    raise ValueError(f"{path}:{line_number}: missing or empty {input_field}")
                attribute = attribute_type()
                if not attribute.validate(value):
                    raise ValueError(f"{path}:{line_number}: invalid {input_field}")
                normalized = attribute.normalize(value)
                if not normalized:
                    raise ValueError(f"{path}:{line_number}: empty normalized {input_field}")
                payload[model_field] = normalized
            yield json.dumps(payload)


def _copy_values(target: np.ndarray, values: list[int]) -> None:
    """Copy token values into a padded tensor, truncating at its sequence length."""
    copy_length = min(len(values), target.shape[0])
    if copy_length:
        target[:copy_length] = np.asarray(values[:copy_length], dtype=np.int64)


def _embed_batch(
    session: ort.InferenceSession,
    tokenizer: Tokenizer,
    payloads: list[str],
    max_sequence_length: int,
) -> np.ndarray:
    """Run one padded batch and return its CLS embeddings."""
    encodings = tokenizer.encode_batch(payloads)
    sequence_length = min(max((len(encoding.ids) for encoding in encodings), default=1), max_sequence_length)
    input_ids = np.zeros((len(payloads), sequence_length), dtype=np.int64)
    attention_mask = np.zeros_like(input_ids)
    token_type_ids = np.zeros_like(input_ids)
    position_ids = np.tile(np.arange(sequence_length, dtype=np.int64), (len(payloads), 1))

    for row_index, encoding in enumerate(encodings):
        _copy_values(input_ids[row_index], encoding.ids or [])
        _copy_values(attention_mask[row_index], encoding.attention_mask or [])
        _copy_values(token_type_ids[row_index], encoding.type_ids or [])

    model_inputs: dict[str, np.ndarray] = {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
    }
    input_names = {model_input.name for model_input in session.get_inputs()}
    if "token_type_ids" in input_names:
        model_inputs["token_type_ids"] = token_type_ids
    if "position_ids" in input_names:
        model_inputs["position_ids"] = position_ids

    outputs = session.run(None, model_inputs)
    output = outputs[0]
    if output.ndim == 3:
        embeddings = output[:, 0, :]
    elif output.ndim == 2:
        embeddings = output
    else:
        raise RuntimeError(f"Unexpected ONNX output shape: {output.shape}")
    return np.asarray(embeddings, dtype=np.float32)


def generate_embeddings(
    input_path: Path,
    output_path: Path,
    model_path: Path,
    tokenizer_path: Path,
    batch_size: int,
    max_sequence_length: int,
    num_threads: int,
) -> None:
    """Generate and save one embedding vector for each JSONL input record."""
    if batch_size <= 0 or max_sequence_length <= 0 or num_threads <= 0:
        raise ValueError("batch_size, max_sequence_length, and num_threads must be positive")

    session_options = ort.SessionOptions()
    session_options.intra_op_num_threads = num_threads
    session_options.inter_op_num_threads = num_threads
    session = ML1OnnxSignatureGenerator._create_session(
        ort,
        session_options,
        model_path.resolve(),
        _resolve_providers(),
    )
    tokenizer = Tokenizer.from_file(str(tokenizer_path))

    embeddings: list[np.ndarray] = []
    batch: list[str] = []
    for payload in _payloads_from_jsonl(input_path):
        batch.append(payload)
        if len(batch) == batch_size:
            embeddings.append(_embed_batch(session, tokenizer, batch, max_sequence_length))
            batch.clear()
    if batch:
        embeddings.append(_embed_batch(session, tokenizer, batch, max_sequence_length))
    if not embeddings:
        raise ValueError(f"{input_path} contains no person records")

    result = np.concatenate(embeddings, axis=0)
    if not np.isfinite(result).all():
        raise RuntimeError("The model produced non-finite embedding values")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, result)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="JSONL person-record input")
    parser.add_argument("--output", type=Path, required=True, help="Output .npy embedding file")
    parser.add_argument("--model", type=Path, default=Path(DEFAULT_MODEL))
    parser.add_argument("--tokenizer", type=Path, default=Path(DEFAULT_TOKENIZER))
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-sequence-length", type=int, default=DEFAULT_MAX_SEQUENCE_LENGTH)
    parser.add_argument("--num-threads", type=int, default=DEFAULT_NUM_THREADS)
    return parser.parse_args()


def main() -> None:
    """Run the embedding generator."""
    args = parse_args()
    generate_embeddings(
        args.input,
        args.output,
        args.model,
        args.tokenizer,
        args.batch_size,
        args.max_sequence_length,
        args.num_threads,
    )


if __name__ == "__main__":
    main()
