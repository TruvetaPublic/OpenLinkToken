# SPDX-License-Identifier: MIT

import math

import pytest
from openlinktoken_core_ai.tokentransformer.rotation.embedding_rotator import rotate

_IV = "test-rotation-iv-2024"
_DIMENSION = 4


class TestEmbeddingRotator:
    """Unit tests for the embedding rotator."""

    def test_result_list_size_equals_number_of_matrices(self):
        """Result list length must equal the number of rotation matrices."""
        matrices = [
            [[1.0, 0.0], [0.0, 1.0]],
            [[0.0, 1.0], [1.0, 0.0]],
            [[1.0, 0.0], [0.0, -1.0]],
        ]
        bias = [0.0, 0.0]
        result = rotate([1.0, 2.0], matrices, bias, k=2)
        assert len(result) == 3

    def test_each_result_has_length_k(self):
        """Each projected vector must have exactly k elements."""
        matrices = [[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]]
        bias = [0.0, 0.0, 0.0]
        result = rotate([1.0, 2.0, 3.0], matrices, bias, k=2)
        assert all(len(row) == 2 for row in result)

    def test_zero_bias_result_equals_matrix_product(self):
        """With zero bias, result[0] must equal R @ embedding exactly."""
        R = [[2.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 4.0]]
        matrices = [R]
        bias = [0.0, 0.0, 0.0]
        embedding = [1.0, 2.0, 3.0]
        result = rotate(embedding, matrices, bias, k=3)
        expected = [2.0, 6.0, 12.0]
        assert result[0] == pytest.approx(expected, abs=1e-9)

    def test_nonzero_bias_is_subtracted(self):
        """Bias is subtracted from embedding before rotation."""
        R = [[1.0, 0.0], [0.0, 1.0]]  # identity
        matrices = [R]
        embedding = [3.0, 5.0]
        bias = [1.0, 2.0]
        result = rotate(embedding, matrices, bias, k=2)
        # Identity rotation: result should be embedding - bias
        assert result[0] == pytest.approx([2.0, 3.0], abs=1e-9)

    def test_length_preservation_orthogonal_rotation(self):
        """For an orthogonal matrix, ||R @ x||₂ ≈ ||x||₂ within 1e-5."""
        # Build a 3×3 orthogonal matrix via Gram-Schmidt on a random-ish seed
        # Use a known orthogonal matrix (90-degree rotations)
        sq2 = math.sqrt(2.0) / 2.0
        R = [
            [sq2, -sq2, 0.0],
            [sq2, sq2, 0.0],
            [0.0, 0.0, 1.0],
        ]
        matrices = [R]
        bias = [0.0, 0.0, 0.0]
        embedding = [3.0, 4.0, 5.0]
        result = rotate(embedding, matrices, bias, k=3)
        original_norm = math.sqrt(sum(v * v for v in embedding))
        rotated_norm = math.sqrt(sum(v * v for v in result[0]))
        assert abs(original_norm - rotated_norm) < 1e-5

    def test_known_45_degree_rotation(self):
        """Test output of a 45° 2D rotation matrix against analytic values."""
        sq2 = math.sqrt(2.0) / 2.0
        # 45° CCW rotation: [[cos45, -sin45], [sin45, cos45]]
        R = [[sq2, -sq2], [sq2, sq2]]
        matrices = [R]
        bias = [0.0, 0.0]
        embedding = [1.0, 0.0]
        result = rotate(embedding, matrices, bias, k=2)
        # Rotating [1,0] by 45° → [cos45, sin45]
        assert result[0][0] == pytest.approx(sq2, abs=1e-9)
        assert result[0][1] == pytest.approx(sq2, abs=1e-9)

    def test_k_less_than_n_truncates_output(self):
        """When k < N, only the first k rows of the rotation are returned."""
        R = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        matrices = [R]
        bias = [0.0, 0.0, 0.0]
        embedding = [7.0, 8.0, 9.0]
        result = rotate(embedding, matrices, bias, k=2)
        assert len(result[0]) == 2
        assert result[0] == pytest.approx([7.0, 8.0], abs=1e-9)

    def test_sentinel_pass_through(self):
        """When a [[-1]] sentinel is the first matrix, it returns the first k values of x_centered."""
        import numpy as np

        sentinel = np.array([[-1.0]])
        regular_R = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]  # 3×3 identity
        matrices = [sentinel, regular_R]
        embedding = [3.0, 5.0, 7.0]
        bias = [1.0, 2.0, 3.0]
        # x_centered = [2.0, 3.0, 4.0]; sentinel result = first k=2 of x_centered
        result = rotate(embedding, matrices, bias, k=2)
        assert len(result) == 2
        assert result[0] == pytest.approx([2.0, 3.0], abs=1e-9), "Sentinel should return first k values of x_centered"
        # Identity rotation: result[:k] = x_centered[:k]
        assert result[1] == pytest.approx([2.0, 3.0], abs=1e-9)

    def test_sentinel_as_only_matrix(self):
        """Sentinel works when it is the only entry in matrices."""
        import numpy as np

        sentinel = np.array([[-1.0]])
        embedding = [10.0, 20.0, 30.0]
        bias = [0.0, 0.0, 0.0]
        result = rotate(embedding, [sentinel], bias, k=2)
        assert len(result) == 1
        assert result[0] == pytest.approx([10.0, 20.0], abs=1e-9)

    def test_sentinel_as_list_of_lists(self):
        """Sentinel detection works when the matrix is a list-of-lists, not an ndarray."""
        sentinel = [[-1.0]]
        embedding = [5.0, 6.0]
        bias = [1.0, 1.0]
        result = rotate(embedding, [sentinel], bias, k=1)
        assert result[0] == pytest.approx([4.0], abs=1e-9)
