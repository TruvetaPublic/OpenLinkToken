/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer.rotation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import org.junit.jupiter.api.Test;

class RotationMatrixGeneratorTest {

    private static final String IV = "test-rotation-iv-2024";
    private static final String ALT_IV = "different-iv-abc";
    private static final int DIMENSION = 4;
    private static final int COUNT = 3;
    private static final double TOLERANCE = 1e-10;

    @Test
    void testReturnsCorrectCount() {
        List<double[][]> matrices = RotationMatrixGenerator.generate(IV, COUNT, DIMENSION);
        assertEquals(COUNT, matrices.size());
    }

    @Test
    void testMatrixDimensions() {
        for (double[][] m : RotationMatrixGenerator.generate(IV, COUNT, DIMENSION)) {
            assertEquals(DIMENSION, m.length);
            for (double[] row : m) {
                assertEquals(DIMENSION, row.length);
            }
        }
    }

    @Test
    void testOrthogonality() {
        for (double[][] m : RotationMatrixGenerator.generate(IV, COUNT, DIMENSION)) {
            int n = DIMENSION;
            for (int i = 0; i < n; i++) {
                for (int j = 0; j < n; j++) {
                    double dot = 0.0;
                    for (int k = 0; k < n; k++) {
                        dot += m[i][k] * m[j][k];
                    }
                    double expected = (i == j) ? 1.0 : 0.0;
                    assertTrue(
                            Math.abs(dot - expected) < TOLERANCE,
                            String.format("Q @ Q^T[%d,%d] = %f, expected %f", i, j, dot, expected));
                }
            }
        }
    }

    @Test
    void testProperRotationDeterminant() {
        for (double[][] m : RotationMatrixGenerator.generate(IV, COUNT, DIMENSION)) {
            double det = computeDet(m, DIMENSION);
            assertTrue(Math.abs(det - 1.0) < TOLERANCE,
                    String.format("det(Q) = %f, expected 1.0", det));
        }
    }

    @Test
    void testDeterminismSameIv() {
        List<double[][]> matricesA = RotationMatrixGenerator.generate(IV, COUNT, DIMENSION);
        List<double[][]> matricesB = RotationMatrixGenerator.generate(IV, COUNT, DIMENSION);
        for (int r = 0; r < COUNT; r++) {
            for (int row = 0; row < DIMENSION; row++) {
                for (int col = 0; col < DIMENSION; col++) {
                    assertEquals(matricesA.get(r)[row][col], matricesB.get(r)[row][col]);
                }
            }
        }
    }

    @Test
    void testDifferentIvsProduceDifferentMatrices() {
        double[][] a = RotationMatrixGenerator.generate(IV, 1, DIMENSION).get(0);
        double[][] b = RotationMatrixGenerator.generate(ALT_IV, 1, DIMENSION).get(0);
        boolean anyDiffers = false;
        outer:
        for (int row = 0; row < DIMENSION; row++) {
            for (int col = 0; col < DIMENSION; col++) {
                if (a[row][col] != b[row][col]) {
                    anyDiffers = true;
                    break outer;
                }
            }
        }
        assertTrue(anyDiffers, "Different IVs must produce different matrices");
    }

    @Test
    void testRotationIndicesDiffer() {
        List<double[][]> matrices = RotationMatrixGenerator.generate(IV, 3, DIMENSION);
        boolean zeroOneDiffers = false;
        boolean oneTwoDiffers = false;
        for (int row = 0; row < DIMENSION; row++) {
            for (int col = 0; col < DIMENSION; col++) {
                if (matrices.get(0)[row][col] != matrices.get(1)[row][col]) {
                    zeroOneDiffers = true;
                }
                if (matrices.get(1)[row][col] != matrices.get(2)[row][col]) {
                    oneTwoDiffers = true;
                }
            }
        }
        assertTrue(zeroOneDiffers, "Matrix 0 and matrix 1 must differ");
        assertTrue(oneTwoDiffers, "Matrix 1 and matrix 2 must differ");
    }

    @Test
    void testDimension2() {
        List<double[][]> matrices = RotationMatrixGenerator.generate(IV, 1, 2);
        double[][] m = matrices.get(0);
        int n = 2;
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                double dot = 0.0;
                for (int k = 0; k < n; k++) {
                    dot += m[i][k] * m[j][k];
                }
                double expected = (i == j) ? 1.0 : 0.0;
                assertTrue(Math.abs(dot - expected) < TOLERANCE);
            }
        }
        assertTrue(Math.abs(computeDet(m, n) - 1.0) < TOLERANCE);
    }

    @Test
    void testDimension8() {
        int n = 8;
        for (double[][] m : RotationMatrixGenerator.generate(IV, 2, n)) {
            for (int i = 0; i < n; i++) {
                for (int j = 0; j < n; j++) {
                    double dot = 0.0;
                    for (int k = 0; k < n; k++) {
                        dot += m[i][k] * m[j][k];
                    }
                    double expected = (i == j) ? 1.0 : 0.0;
                    assertTrue(Math.abs(dot - expected) < TOLERANCE);
                }
            }
            assertTrue(Math.abs(computeDet(m, n) - 1.0) < TOLERANCE);
        }
    }

    @Test
    void testThreadSafety() throws InterruptedException {
        int threadCount = 100;
        List<double[][]> results = new ArrayList<>(threadCount);
        for (int i = 0; i < threadCount; i++) {
            results.add(null);
        }
        List<Exception> errors = new ArrayList<>();
        CountDownLatch latch = new CountDownLatch(threadCount);

        ExecutorService pool = Executors.newFixedThreadPool(threadCount);
        for (int i = 0; i < threadCount; i++) {
            final int idx = i;
            pool.submit(() -> {
                try {
                    results.set(idx, RotationMatrixGenerator.generate(IV, 1, DIMENSION).get(0));
                } catch (Exception e) {
                    synchronized (errors) {
                        errors.add(e);
                    }
                } finally {
                    latch.countDown();
                }
            });
        }
        latch.await();
        pool.shutdown();

        assertTrue(errors.isEmpty(), "Thread errors: " + errors);
        double[][] reference = results.get(0);
        for (double[][] r : results) {
            for (int row = 0; row < DIMENSION; row++) {
                for (int col = 0; col < DIMENSION; col++) {
                    assertEquals(reference[row][col], r[row][col]);
                }
            }
        }
    }

    /** Compute determinant via Gaussian elimination for test validation. */
    private static double computeDet(double[][] matrix, int n) {
        double[][] a = new double[n][];
        for (int i = 0; i < n; i++) {
            a[i] = matrix[i].clone();
        }
        double sign = 1.0;
        for (int col = 0; col < n; col++) {
            int maxRow = col;
            for (int row = col + 1; row < n; row++) {
                if (Math.abs(a[row][col]) > Math.abs(a[maxRow][col])) {
                    maxRow = row;
                }
            }
            if (maxRow != col) {
                double[] tmp = a[col];
                a[col] = a[maxRow];
                a[maxRow] = tmp;
                sign = -sign;
            }
            for (int row = col + 1; row < n; row++) {
                double factor = a[row][col] / a[col][col];
                for (int j = col; j < n; j++) {
                    a[row][j] -= factor * a[col][j];
                }
            }
        }
        double det = sign;
        for (int i = 0; i < n; i++) {
            det *= a[i][i];
        }
        return det;
    }
}
