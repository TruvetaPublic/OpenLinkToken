/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer.rotation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;

import org.junit.jupiter.api.Test;

class EmbeddingRotatorTest {

    private static final double TOLERANCE = 1e-5;

    /**
     * Build a trivial 2×2 rotation matrix for angle θ (in radians):
     *   [[ cos θ, -sin θ ],
     *    [ sin θ,  cos θ ]]
     */
    private static double[][] rotation2d(double theta) {
        double c = Math.cos(theta);
        double s = Math.sin(theta);
        return new double[][] { { c, -s }, { s, c } };
    }

    @Test
    void testResultListSizeEqualsMatrixCount() {
        List<double[][]> matrices = RotationMatrixGenerator.generate("test-iv", 5, 4);
        float[] embedding = { 1.0f, 2.0f, 3.0f, 4.0f };
        float[] bias = new float[4];

        List<float[]> result = EmbeddingRotator.rotate(embedding, matrices, bias, 4);

        assertEquals(5, result.size());
    }

    @Test
    void testEachResultHasLengthK() {
        int k = 3;
        List<double[][]> matrices = RotationMatrixGenerator.generate("test-iv", 4, 4);
        float[] embedding = { 0.5f, -0.5f, 1.0f, -1.0f };
        float[] bias = new float[4];

        List<float[]> result = EmbeddingRotator.rotate(embedding, matrices, bias, k);

        for (float[] projected : result) {
            assertEquals(k, projected.length);
        }
    }

    @Test
    void testZeroBiasOutputMatchesDirectProjection() {
        double[][] r = rotation2d(Math.PI / 4.0); // 45-degree rotation
        float[] embedding = { 1.0f, 0.0f };
        float[] bias = new float[2];

        List<float[]> result = EmbeddingRotator.rotate(embedding, List.<double[][]>of(r), bias, 2);
        float[] projected = result.get(0);
        double cos45 = Math.cos(Math.PI / 4.0);
        double sin45 = Math.sin(Math.PI / 4.0);
        assertEquals(cos45, projected[0], TOLERANCE);
        assertEquals(sin45, projected[1], TOLERANCE);
    }

    @Test
    void testNonZeroBiasIsSubtracted() {
        double[][] r = new double[][] { { 1.0, 0.0 }, { 0.0, 1.0 } }; // identity
        float[] embedding = { 3.0f, 5.0f };
        float[] bias = { 1.0f, 2.0f };

        List<float[]> result = EmbeddingRotator.rotate(embedding, List.<double[][]>of(r), bias, 2);
        float[] projected = result.get(0);

        // identity rotation: output = embedding - bias
        assertEquals(2.0f, projected[0], (float) TOLERANCE);
        assertEquals(3.0f, projected[1], (float) TOLERANCE);
    }

    @Test
    void testKnown2dRotation45Degrees() {
        double[][] r = rotation2d(Math.PI / 4.0);
        float[] embedding = { 1.0f, 1.0f };
        float[] bias = new float[2];

        List<float[]> result = EmbeddingRotator.rotate(embedding, List.<double[][]>of(r), bias, 2);
        float[] projected = result.get(0);

        // [cos45-sin45, sin45+cos45] = [0, sqrt(2)]
        assertEquals(0.0, projected[0], TOLERANCE);
        assertEquals(Math.sqrt(2.0), projected[1], TOLERANCE);
    }

    @Test
    void testRotationPreservesVectorLength() {
        List<double[][]> matrices = RotationMatrixGenerator.generate("length-test-iv", 3, 8);
        float[] embedding = { 1.0f, -2.0f, 3.0f, 0.5f, -1.5f, 2.5f, -0.5f, 1.0f };
        float[] bias = new float[8];

        double inputNorm = 0.0;
        for (float v : embedding) {
            inputNorm += v * v;
        }
        inputNorm = Math.sqrt(inputNorm);

        List<float[]> result = EmbeddingRotator.rotate(embedding, matrices, bias, 8);

        for (float[] projected : result) {
            double outputNorm = 0.0;
            for (float v : projected) {
                outputNorm += v * v;
            }
            outputNorm = Math.sqrt(outputNorm);
            assertEquals(inputNorm, outputNorm, TOLERANCE,
                    "Rotation should preserve vector length");
        }
    }

    @Test
    void testBiasLengthMismatchThrows() {
        List<double[][]> matrices = RotationMatrixGenerator.generate("test-iv", 1, 4);
        float[] embedding = { 1.0f, 2.0f, 3.0f, 4.0f };
        float[] wrongBias = { 0.0f, 0.0f }; // wrong length

        assertThrows(IllegalArgumentException.class,
                () -> EmbeddingRotator.rotate(embedding, matrices, wrongBias, 4));
    }

    @Test
    void testKExceedsMatrixRowsThrows() {
        List<double[][]> matrices = RotationMatrixGenerator.generate("test-iv", 1, 4);
        float[] embedding = { 1.0f, 2.0f, 3.0f, 4.0f };
        float[] bias = new float[4];

        assertThrows(IllegalArgumentException.class,
                () -> EmbeddingRotator.rotate(embedding, matrices, bias, 5)); // k=5 > N=4
    }

    @Test
    void testOnlyFirstKRowsUsed() {
        // 4×4 identity matrix; k=2 should yield first 2 rows applied to embedding
        double[][] identity4 = {
            { 1.0, 0.0, 0.0, 0.0 },
            { 0.0, 1.0, 0.0, 0.0 },
            { 0.0, 0.0, 1.0, 0.0 },
            { 0.0, 0.0, 0.0, 1.0 }
        };
        float[] embedding = { 5.0f, 7.0f, 11.0f, 13.0f };
        float[] bias = new float[4];

        List<float[]> result = EmbeddingRotator.rotate(embedding, List.<double[][]>of(identity4), bias, 2);
        float[] projected = result.get(0);

        assertEquals(2, projected.length);
        assertEquals(5.0f, projected[0], (float) TOLERANCE);
        assertEquals(7.0f, projected[1], (float) TOLERANCE);
    }

    @Test
    void testMultipleMatricesProduceDifferentResults() {
        List<double[][]> matrices = RotationMatrixGenerator.generate("multi-test-iv", 3, 4);
        float[] embedding = { 1.0f, 2.0f, 3.0f, 4.0f };
        float[] bias = new float[4];

        List<float[]> result = EmbeddingRotator.rotate(embedding, matrices, bias, 4);

        // Different rotation matrices should produce different projections
        boolean anyDiffers = false;
        for (int j = 0; j < result.get(0).length; j++) {
            if (Math.abs(result.get(0)[j] - result.get(1)[j]) > 1e-6) {
                anyDiffers = true;
                break;
            }
        }
        assertTrue(anyDiffers, "Different rotation matrices should produce different projections");
    }
}
