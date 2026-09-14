/* SPDX-License-Identifier: MIT */
package org.openlinktoken.core.ai.tokentransformer.rotation;

import java.util.ArrayList;
import java.util.List;

/**
 * Projects a float embedding vector through one or more rotation matrices.
 *
 * <p>Each matrix in the supplied list produces one projected {@code float[]} of
 * length {@code k}.  The input embedding is first mean-centred by subtracting a
 * per-dimension bias (which may be all zeros) and the arithmetic is carried out
 * in {@code double} to preserve precision before the result is cast back to
 * {@code float}.
 */
public final class EmbeddingRotator {

    private EmbeddingRotator() {
    }

    /**
     * Rotate an embedding vector through each matrix in {@code matrices}.
     *
     * <p>The first entry in {@code matrices} may be the {@code [[-1]]} sentinel, which
     * signals a pass-through projection: the first {@code k} values of the bias-centred
     * embedding are returned directly without any rotation.  This matches the cloud
     * backend's index-0 pass-through token.  All subsequent entries must be valid N×N
     * rotation matrices.
     *
     * <p>For each non-sentinel matrix {@code R} (shape N×N, though only the first
     * {@code k} rows are used):
     * <pre>
     *   x_centered[i] = (double) embedding[i] - bias[i]
     *   rotated[row]  = (float) sum_col( R[row][col] * x_centered[col] )
     * </pre>
     *
     * @param embedding the raw CLS embedding vector; length N
     * @param matrices  list whose first entry may be the {@code [[-1]]} sentinel and
     *                  whose remaining entries are N×N rotation matrices; only the first
     *                  {@code k} rows of each rotation matrix are used
     * @param bias      per-dimension bias to subtract before projection;
     *                  must have the same length as {@code embedding}
     * @param k         number of output dimensions per projection (k ≤ N)
     * @return list of projected float vectors, one per entry in {@code matrices}, each of length k
     * @throws IllegalArgumentException if {@code bias.length != embedding.length}
     *                                  or {@code k} exceeds the matrix row count for a non-sentinel entry
     */
    public static List<float[]> rotate(float[] embedding, List<double[][]> matrices, double[] bias, int k) {
        if (bias.length != embedding.length) {
            throw new IllegalArgumentException(
                    "bias.length (" + bias.length + ") must equal embedding.length (" + embedding.length + ")");
        }

        int n = embedding.length;

        // Pre-compute centered vector in double once for all matrices.
        double[] xCentered = new double[n];
        for (int i = 0; i < n; i++) {
            xCentered[i] = (double) embedding[i] - bias[i];
        }

        List<float[]> results = new ArrayList<>(matrices.size());

        for (double[][] r : matrices) {
            if (isSentinel(r)) {
                // Sentinel [-1]: pass-through — return first k values of the centred embedding.
                float[] passThrough = new float[k];
                for (int i = 0; i < k; i++) {
                    passThrough[i] = (float) xCentered[i];
                }
                results.add(passThrough);
            } else {
                if (k > r.length) {
                    throw new IllegalArgumentException(
                            "k (" + k + ") exceeds matrix row count (" + r.length + ")");
                }
                float[] rotated = new float[k];
                for (int row = 0; row < k; row++) {
                    double sum = 0.0;
                    for (int col = 0; col < n; col++) {
                        sum += r[row][col] * xCentered[col];
                    }
                    rotated[row] = (float) sum;
                }
                results.add(rotated);
            }
        }

        return results;
    }

    /**
     * Returns {@code true} when {@code r} is the {@code [[-1]]} sentinel matrix.
     *
     * <p>A sentinel is a 1×1 matrix whose single element equals {@code -1.0}.
     *
     * @param r matrix to test
     * @return {@code true} if {@code r} is the sentinel
     */
    static boolean isSentinel(double[][] r) {
        return r.length == 1 && r[0].length == 1 && r[0][0] == -1.0;
    }
}
