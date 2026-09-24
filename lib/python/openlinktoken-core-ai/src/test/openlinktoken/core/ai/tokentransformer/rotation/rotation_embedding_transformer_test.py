# SPDX-License-Identifier: MIT

import re
import threading
from pathlib import Path

import numpy as np
import pytest

from openlinktoken.core.ai.tokentransformer.rotation import rotation_embedding_transformer as transformer_module
from openlinktoken.core.ai.tokentransformer.rotation.rotation_embedding_transformer import RotationEmbeddingTransformer
from openlinktoken.core.ai.tokentransformer.rotation.rotation_matrix_generator import generate

_IV = "test-rotation-iv-2024"
_DIMENSION = 4
_HASH_DIMENSION = 2
_ROTATION_COUNT = 3


@pytest.fixture(autouse=True)
def isolate_rotation_cache(tmp_path, monkeypatch):
    """Keep matrix-cache tests and transforms isolated from the user's home."""
    monkeypatch.setenv("OLT_ROTATION_CACHE_DIR", str(tmp_path))


class TestRotationEmbeddingTransformer:
    """Unit tests for RotationEmbeddingTransformer."""

    def _make_transformer(
        self, rotation_count=_ROTATION_COUNT, hash_dimension=_HASH_DIMENSION
    ) -> RotationEmbeddingTransformer:
        """Create a transformer using the shared test configuration."""
        return RotationEmbeddingTransformer(
            iv=_IV,
            rotation_count=rotation_count,
            dimension=_DIMENSION,
            hash_dimension=hash_dimension,
        )

    def _sample_embedding(self) -> list:
        """Return a small embedding suitable for deterministic assertions."""
        return [0.1, -0.2, 0.3, -0.4]

    def test_transform_returns_rotation_count_tokens(self):
        """transform() must return exactly rotation_count token strings."""
        transformer = self._make_transformer()
        tokens = transformer.transform(self._sample_embedding())
        assert len(tokens) == _ROTATION_COUNT

    def test_each_token_is_nonempty(self):
        """Each returned token must be a non-empty string."""
        transformer = self._make_transformer()
        tokens = transformer.transform(self._sample_embedding())
        for token in tokens:
            assert isinstance(token, str)
            assert len(token) > 0

    def test_each_token_contains_only_space_separated_integers(self):
        """Each token must contain only space-separated integer strings."""
        transformer = self._make_transformer()
        tokens = transformer.transform(self._sample_embedding())
        int_pattern = re.compile(r"^\d+( \d+)*$")
        for token in tokens:
            assert int_pattern.match(token), f"Token did not match pattern: {token!r}"

    def test_token_has_hash_dimension_values(self):
        """Each token string must contain exactly hash_dimension space-separated values."""
        hash_dim = 2
        transformer = self._make_transformer(hash_dimension=hash_dim)
        tokens = transformer.transform(self._sample_embedding())
        for token in tokens:
            parts = token.split(" ")
            assert len(parts) == hash_dim

    def test_transformer_keeps_only_projected_rotation_rows(self):
        """The transformer should retain only the matrix rows used for projection."""
        transformer = self._make_transformer(hash_dimension=2)

        transformer.transform(self._sample_embedding())
        expected = generate(_IV, _ROTATION_COUNT - 1, _DIMENSION)

        assert len(transformer._matrices) == _ROTATION_COUNT
        for actual_matrix, expected_matrix in zip(transformer._matrices[1:], expected):
            assert np.asarray(actual_matrix).shape == (_HASH_DIMENSION, _DIMENSION)
            np.testing.assert_allclose(
                np.asarray(actual_matrix),
                expected_matrix[:_HASH_DIMENSION, :],
                rtol=0.0,
                atol=1e-12,
            )

    def test_hash_dimension_matches_standard_full_rotation_parity_fixture(self):
        """The Python transformer must match the standard full-rotation parity fixture."""
        transformer = RotationEmbeddingTransformer(
            iv="openlinktoken-ml1-v1",
            rotation_count=2,
            dimension=8,
            hash_dimension=3,
        )

        tokens = transformer.transform([0.125, -0.25, 0.375, -0.5, 0.625, -0.75, 0.875, -1.0])

        assert tokens == ["102 94 107", "95 126 103"]

    def test_matrix_caching_returns_identical_results(self):
        """Calling transform() twice on the same instance returns identical results."""
        transformer = self._make_transformer()
        embedding = self._sample_embedding()
        tokens_first = transformer.transform(embedding)
        tokens_second = transformer.transform(embedding)
        assert tokens_first == tokens_second

    def test_matrices_are_not_regenerated_on_second_call(self):
        """After the first call, _matrices should be populated and stable."""
        transformer = self._make_transformer()
        transformer.transform(self._sample_embedding())
        matrices_after_first = transformer._matrices
        transformer.transform(self._sample_embedding())
        matrices_after_second = transformer._matrices
        assert matrices_after_first is matrices_after_second

    def test_cached_matrices_are_reused_by_new_transformer(self, tmp_path, monkeypatch):
        """A second transformer should load the deterministic matrix cache."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        first = self._make_transformer()
        first_tokens = first.transform(self._sample_embedding())

        def fail_generate(*args, **kwargs):
            """Fail if the second transformer regenerates an existing cache entry."""
            raise AssertionError("rotation matrices were regenerated instead of loaded from cache")

        monkeypatch.setattr(transformer_module, "generate", fail_generate)
        second = self._make_transformer()

        assert second.transform(self._sample_embedding()) == first_tokens

    def test_corrupt_cached_matrices_are_regenerated(self, tmp_path):
        """A cache with a mismatched digest should not change emitted tokens."""
        transformer = self._make_transformer()
        expected_tokens = transformer.transform(self._sample_embedding())
        cache_path = next((tmp_path / "rotation-matrices").glob("*.npz"))

        with np.load(cache_path, allow_pickle=False) as cache:
            matrices = cache["matrices"].copy()
            digest = cache["digest"].copy()
        matrices[0, 0, 0] += 1.0
        np.savez(cache_path, matrices=matrices, digest=digest)

        regenerated = self._make_transformer()

        assert regenerated.transform(self._sample_embedding()) == expected_tokens

    def test_unresolvable_home_does_not_break_transform(self, monkeypatch):
        """Matrix caching should be skipped when the home directory is unavailable."""
        monkeypatch.delenv("OLT_ROTATION_CACHE_DIR")

        def fail_home():
            """Simulate a process without a resolvable home directory."""
            raise RuntimeError("Could not determine home directory")

        monkeypatch.setattr(Path, "home", fail_home)
        transformer = self._make_transformer()

        assert len(transformer.transform(self._sample_embedding())) == _ROTATION_COUNT

    def test_single_rotation_uses_only_the_sentinel(self):
        """A sentinel-only transformer should not attempt to cache a negative matrix count."""
        transformer = self._make_transformer(rotation_count=1)

        assert len(transformer.transform(self._sample_embedding())) == 1
        assert len(transformer._matrices) == 1

    def test_zero_rotation_count_keeps_the_sentinel_only_behavior(self):
        """The transformer should preserve its sentinel-only behavior for zero matrices."""
        transformer = self._make_transformer(rotation_count=0)

        assert len(transformer.transform(self._sample_embedding())) == 1
        assert len(transformer._matrices) == 1

    def test_thread_safety_concurrent_transforms(self):
        """Two threads calling transform() concurrently both succeed without error."""
        transformer = RotationEmbeddingTransformer(
            iv=_IV,
            rotation_count=_ROTATION_COUNT,
            dimension=_DIMENSION,
            hash_dimension=_HASH_DIMENSION,
        )
        embedding = self._sample_embedding()
        results = []
        errors = []

        def worker():
            """Run one concurrent transform and capture any exception."""
            try:
                tokens = transformer.transform(embedding)
                results.append(tokens)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        assert len(results) == 2
        # Both threads should produce the same output
        assert results[0] == results[1]

    def test_different_ivs_produce_different_tokens(self):
        """Two transformers with different IVs should produce different tokens for non-sentinel entries."""
        t1 = RotationEmbeddingTransformer(
            iv="iv-one", rotation_count=2, dimension=_DIMENSION, hash_dimension=_HASH_DIMENSION
        )
        t2 = RotationEmbeddingTransformer(
            iv="iv-two", rotation_count=2, dimension=_DIMENSION, hash_dimension=_HASH_DIMENSION
        )
        embedding = self._sample_embedding()
        # Token[0] is the sentinel and is IV-independent; token[1] varies by IV.
        assert t1.transform(embedding)[1] != t2.transform(embedding)[1]
