#!/usr/bin/env python3
"""Calculate an ML1 dimension-bias vector from saved embeddings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

DEFAULT_DIMENSION = 1024
DEFAULT_SAMPLE_SIZE = 100_000


def calculate_embedding_bias(
    input_path: Path,
    output_path: Path,
    dimension: int,
    sample_size: int,
    seed: int,
) -> None:
    """Calculate the per-dimension median of valid sampled embeddings."""
    if dimension <= 0 or sample_size <= 0:
        raise ValueError("dimension and sample_size must be positive")

    vectors = np.load(input_path, mmap_mode="r", allow_pickle=False)
    if vectors.ndim != 2 or vectors.shape[0] == 0:
        raise ValueError("Expected a non-empty two-dimensional embedding array")
    if vectors.shape[1] != dimension:
        raise ValueError(f"Expected {dimension}-dimensional embeddings")

    sample_count = min(sample_size, vectors.shape[0])
    if sample_count < vectors.shape[0]:
        indices = np.random.default_rng(seed).choice(vectors.shape[0], sample_count, replace=False)
        sampled_vectors = np.asarray(vectors[indices], dtype=np.float32)
    else:
        sampled_vectors = np.asarray(vectors, dtype=np.float32)
    if not np.isfinite(sampled_vectors).all():
        raise ValueError("Embeddings must contain only finite values")

    bias = np.median(sampled_vectors, axis=0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(bias.tolist(), output_file)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Input .npy embedding file")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON bias file")
    parser.add_argument("--dimension", type=int, default=DEFAULT_DIMENSION)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    """Run the embedding-bias calculator."""
    args = parse_args()
    calculate_embedding_bias(
        args.input,
        args.output,
        args.dimension,
        args.sample_size,
        args.seed,
    )


if __name__ == "__main__":
    main()
