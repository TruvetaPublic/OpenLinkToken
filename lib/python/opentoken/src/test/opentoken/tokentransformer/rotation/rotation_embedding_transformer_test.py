"""
Copyright (c) Truveta. All rights reserved.
"""

import re
import threading

from opentoken.tokentransformer.rotation.rotation_embedding_transformer import RotationEmbeddingTransformer

_IV = "test-rotation-iv-2024"
_DIMENSION = 4
_HASH_DIMENSION = 2
_ROTATION_COUNT = 3


class TestRotationEmbeddingTransformer:
    """Unit tests for RotationEmbeddingTransformer."""

    def _make_transformer(
        self, rotation_count=_ROTATION_COUNT, hash_dimension=_HASH_DIMENSION
    ) -> RotationEmbeddingTransformer:
        return RotationEmbeddingTransformer(
            iv=_IV,
            rotation_count=rotation_count,
            dimension=_DIMENSION,
            hash_dimension=hash_dimension,
        )

    def _sample_embedding(self) -> list:
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
        """Two transformers with different IVs should produce different tokens."""
        t1 = RotationEmbeddingTransformer(
            iv="iv-one", rotation_count=1, dimension=_DIMENSION, hash_dimension=_HASH_DIMENSION
        )
        t2 = RotationEmbeddingTransformer(
            iv="iv-two", rotation_count=1, dimension=_DIMENSION, hash_dimension=_HASH_DIMENSION
        )
        embedding = self._sample_embedding()
        assert t1.transform(embedding) != t2.transform(embedding)
