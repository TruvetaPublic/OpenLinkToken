# SPDX-License-Identifier: MIT

import threading

import numpy as np
import pytest

from openlinktoken.core.ai.tokentransformer.rotation.rotation_matrix_generator import generate

_IV = "test-rotation-iv-2024"
_ALT_IV = "different-iv-abc"
_DIMENSION = 4
_COUNT = 3


class TestRotationMatrixGenerator:
    """Unit tests for rotation matrix generation."""

    def test_returns_correct_count(self):
        """Generate exactly the requested number of matrices."""
        matrices = generate(_IV, _COUNT, _DIMENSION)
        assert len(matrices) == _COUNT

    def test_matrix_dimensions(self):
        """Ensure every generated matrix has the requested dimensions."""
        for matrix in generate(_IV, _COUNT, _DIMENSION):
            assert len(matrix) == _DIMENSION
            for row in matrix:
                assert len(row) == _DIMENSION

    def test_row_count_keeps_leading_rows_with_full_rotation_values(self):
        """A projected matrix should retain the leading rows of the full matrix."""
        full_matrix = generate(_IV, 1, _DIMENSION)[0]
        projected_matrix = generate(_IV, 1, _DIMENSION, row_count=2)[0]

        assert projected_matrix.shape == (2, _DIMENSION)
        np.testing.assert_array_equal(projected_matrix, full_matrix[:2, :])

    def test_row_count_must_be_within_dimension(self):
        """Invalid projected row counts should be rejected."""
        with pytest.raises(ValueError):
            generate(_IV, 1, _DIMENSION, row_count=0)
        with pytest.raises(ValueError):
            generate(_IV, 1, _DIMENSION, row_count=_DIMENSION + 1)

    def test_orthogonality(self):
        """Q @ Q^T must be the identity matrix within floating-point tolerance."""
        for matrix in generate(_IV, _COUNT, _DIMENSION):
            n = _DIMENSION
            for i in range(n):
                for j in range(n):
                    dot = sum(matrix[i][k] * matrix[j][k] for k in range(n))
                    expected = 1.0 if i == j else 0.0
                    assert abs(dot - expected) < 1e-10, f"Q @ Q^T[{i},{j}] = {dot}, expected {expected}"

    def test_proper_rotation_determinant(self):
        """det(Q) must equal +1 for a proper rotation matrix."""
        for matrix in generate(_IV, _COUNT, _DIMENSION):
            det = _det(matrix, _DIMENSION)
            assert abs(det - 1.0) < 1e-10, f"det(Q) = {det}, expected 1.0"

    def test_determinism_same_iv(self):
        """Same IV must always produce identical matrices."""
        matrices_a = generate(_IV, _COUNT, _DIMENSION)
        matrices_b = generate(_IV, _COUNT, _DIMENSION)
        for ma, mb in zip(matrices_a, matrices_b):
            assert np.array_equal(ma, mb)

    def test_different_ivs_produce_different_matrices(self):
        """Different IVs must produce different deterministic matrices."""
        matrices_a = generate(_IV, 1, _DIMENSION)
        matrices_b = generate(_ALT_IV, 1, _DIMENSION)
        assert not np.array_equal(matrices_a[0], matrices_b[0])

    def test_rotation_indices_differ(self):
        """Different rotation indices must produce different matrices."""
        matrices = generate(_IV, 3, _DIMENSION)
        assert not np.array_equal(matrices[0], matrices[1])
        assert not np.array_equal(matrices[1], matrices[2])

    def test_single_matrix(self):
        """Support generating a single rotation matrix."""
        matrices = generate(_IV, 1, _DIMENSION)
        assert len(matrices) == 1

    def test_rows_returns_only_leading_rows_without_changing_values(self):
        """A row limit should retain the exact leading rows of each full matrix."""
        full_matrices = generate(_IV, _COUNT, _DIMENSION)
        leading_rows = generate(_IV, _COUNT, _DIMENSION, rows=2)

        for actual, expected in zip(leading_rows, full_matrices):
            assert actual.shape == (2, _DIMENSION)
            np.testing.assert_array_equal(actual, expected[:2, :])

    def test_dimension_2(self):
        """Verify correctness for the smallest non-trivial dimension."""
        matrices = generate(_IV, 1, 2)
        matrix = matrices[0]
        n = 2
        for i in range(n):
            for j in range(n):
                dot = sum(matrix[i][k] * matrix[j][k] for k in range(n))
                expected = 1.0 if i == j else 0.0
                assert abs(dot - expected) < 1e-10
        det = _det(matrix, n)
        assert abs(det - 1.0) < 1e-10

    def test_dimension_8(self):
        """Preserve orthogonality and determinant for a larger dimension."""
        matrices = generate(_IV, 2, 8)
        n = 8
        for matrix in matrices:
            for i in range(n):
                for j in range(n):
                    dot = sum(matrix[i][k] * matrix[j][k] for k in range(n))
                    expected = 1.0 if i == j else 0.0
                    assert abs(dot - expected) < 1e-10
            det = _det(matrix, n)
            assert abs(det - 1.0) < 1e-10

    def test_matches_person_matching_qr_fixture(self):
        """Matrices must match the persisted PersonMatching QR-generation contract."""
        matrix = generate("qr-parity-fixture", 1, 8)[0]

        np.testing.assert_allclose(
            matrix[0],
            [
                -0.40747839357338234,
                -0.1408568566341346,
                -0.11969515964474949,
                0.2890408553442878,
                -0.6332317872229138,
                -0.03396738148325333,
                0.5422064923077496,
                0.14186260167654755,
            ],
            rtol=0.0,
            atol=1e-12,
        )

    def test_thread_safety(self):
        """Concurrent calls with the same IV must all produce the same result."""
        results = [None] * 100
        errors = []

        def worker(idx):
            """Generate one matrix concurrently and capture any exception."""
            try:
                results[idx] = generate(_IV, 1, _DIMENSION)[0]
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        reference = results[0]
        for r in results[1:]:
            assert np.array_equal(r, reference)


def _det(matrix, n):
    """Compute determinant via Gaussian elimination for test validation."""
    a = [list(row) for row in matrix]
    sign = 1
    for col in range(n):
        max_row = col
        for row in range(col + 1, n):
            if abs(a[row][col]) > abs(a[max_row][col]):
                max_row = row
        if max_row != col:
            a[col], a[max_row] = a[max_row], a[col]
            sign = -sign
        for row in range(col + 1, n):
            factor = a[row][col] / a[col][col]
            for j in range(col, n):
                a[row][j] -= factor * a[col][j]
    result = sign
    for i in range(n):
        result *= a[i][i]
    return result
