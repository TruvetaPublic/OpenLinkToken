/* SPDX-License-Identifier: MIT */
package org.openlinktoken.tokentransformer.rotation;

import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.List;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * Generates deterministic orthogonal rotation matrices from an initialization vector (IV).
 *
 * <p>The algorithm uses HMAC-SHA256 in counter mode as a PRNG, Box-Muller transform to produce
 * standard-normal values, and Householder QR decomposition for orthonormalization. The
 * resulting columns are normalized by the signs of the QR diagonal to match the persisted
 * PersonMatching rotation-matrix contract.
 *
 * <p>Each returned matrix Q satisfies {@code Q * Q^T = I} and {@code det(Q) = +1}.
 */
public final class RotationMatrixGenerator {

    /**
     * 2^53: used to convert 53-bit integers to uniform doubles.
     * Stored as a long to keep the bit pattern exact.
     */
    private static final long MANTISSA_BITS = 1L << 53;

    private static final double MANTISSA_SCALE = 1.0 / MANTISSA_BITS;

    /** Smallest representable uniform value; avoids log(0) in Box-Muller. */
    private static final double MIN_UNIFORM = MANTISSA_SCALE;

    private static final double TWO_PI = 2.0 * Math.PI;

    private RotationMatrixGenerator() {
    }

    /**
     * Generate a list of deterministic orthogonal rotation matrices from an IV.
     *
     * @param iv            initialization vector string; same IV always produces the same matrices.
     * @param rotationCount number of rotation matrices to generate.
     * @param dimension     number of rows and columns in each matrix (N×N).
     * @return a list of {@code rotationCount} matrices, each a {@code dimension × dimension}
     *         row-major {@code double[][]} where {@code matrix[row][col]} is the element at
     *         (row, col). Each matrix is an orthogonal proper-rotation matrix.
     */
    public static List<double[][]> generate(String iv, int rotationCount, int dimension) {
        byte[] keyMaterial = sha256(iv.getBytes(StandardCharsets.UTF_8));
        List<double[][]> matrices = new ArrayList<>(rotationCount);
        for (int r = 0; r < rotationCount; r++) {
            matrices.add(generateOne(keyMaterial, r, dimension));
        }
        return matrices;
    }

    private static double[][] generateOne(byte[] keyMaterial, int rotationIndex, int n) {
        int pairsPerCol = (n + 1) / 2;

        // Build row-major raw matrix filled column-by-column via Box-Muller.
        double[][] raw = new double[n][n];
        for (int col = 0; col < n; col++) {
            int offset = 0;
            for (int pair = 0; pair < pairsPerCol; pair++) {
                long counter = ((long) (rotationIndex * n + col)) * pairsPerCol + pair;
                byte[] h = hmacSha256(keyMaterial, longToBytes(counter));
                double u1 = Math.max(extractUniform(h, 0), MIN_UNIFORM);
                double u2 = extractUniform(h, 8);
                double rVal = Math.sqrt(-2.0 * Math.log(u1));
                double theta = TWO_PI * u2;
                double z0 = rVal * Math.cos(theta);
                double z1 = rVal * Math.sin(theta);
                raw[offset][col] = z0;
                offset++;
                if (offset < n) {
                    raw[offset][col] = z1;
                    offset++;
                }
            }
        }

        double[][] q = householderQr(raw, n);

        // Ensure det(Q) = +1 (proper rotation, no reflection).
        if (computeDetSign(q, n) < 0) {
            for (int row = 0; row < n; row++) {
                q[row][n - 1] = -q[row][n - 1];
            }
        }

        return q;
    }

    private static double[][] householderQr(double[][] raw, int n) {
        double[][] q = identityMatrix(n);
        double[][] r = copyMatrix(raw, n);

        for (int col = 0; col < n; col++) {
            double[] reflector = new double[n - col];
            for (int row = col; row < n; row++) {
                reflector[row - col] = r[row][col];
            }

            double norm = vectorNorm(reflector);
            if (norm == 0.0) {
                continue;
            }
            reflector[0] += Math.copySign(norm, reflector[0]);
            applyReflectorFromLeft(r, reflector, col, col, n);
            applyReflectorFromRight(q, reflector, col, n);
        }

        for (int col = 0; col < n; col++) {
            if (r[col][col] < 0.0) {
                for (int row = 0; row < n; row++) {
                    q[row][col] = -q[row][col];
                }
            }
        }
        return q;
    }

    private static double[][] identityMatrix(int n) {
        double[][] identity = new double[n][n];
        for (int row = 0; row < n; row++) {
            identity[row][row] = 1.0;
        }
        return identity;
    }

    private static double[][] copyMatrix(double[][] matrix, int n) {
        double[][] copy = new double[n][];
        for (int row = 0; row < n; row++) {
            copy[row] = matrix[row].clone();
        }
        return copy;
    }

    private static double vectorNorm(double[] values) {
        double scale = 0.0;
        double sumOfSquares = 1.0;
        for (double value : values) {
            double absoluteValue = Math.abs(value);
            if (absoluteValue == 0.0) {
                continue;
            }
            if (scale < absoluteValue) {
                sumOfSquares = 1.0 + sumOfSquares * (scale / absoluteValue) * (scale / absoluteValue);
                scale = absoluteValue;
            } else {
                sumOfSquares += (absoluteValue / scale) * (absoluteValue / scale);
            }
        }
        return scale == 0.0 ? 0.0 : scale * Math.sqrt(sumOfSquares);
    }

    private static void applyReflectorFromLeft(
            double[][] matrix, double[] reflector, int startRow, int startColumn, int n) {
        double squaredNorm = squaredNorm(reflector);
        for (int col = startColumn; col < n; col++) {
            double dotProduct = 0.0;
            for (int row = startRow; row < n; row++) {
                dotProduct += reflector[row - startRow] * matrix[row][col];
            }
            double multiplier = 2.0 * dotProduct / squaredNorm;
            for (int row = startRow; row < n; row++) {
                matrix[row][col] -= multiplier * reflector[row - startRow];
            }
        }
    }

    private static void applyReflectorFromRight(double[][] matrix, double[] reflector, int startColumn, int n) {
        double squaredNorm = squaredNorm(reflector);
        for (int row = 0; row < n; row++) {
            double dotProduct = 0.0;
            for (int col = startColumn; col < n; col++) {
                dotProduct += matrix[row][col] * reflector[col - startColumn];
            }
            double multiplier = 2.0 * dotProduct / squaredNorm;
            for (int col = startColumn; col < n; col++) {
                matrix[row][col] -= multiplier * reflector[col - startColumn];
            }
        }
    }

    private static double squaredNorm(double[] values) {
        double sum = 0.0;
        for (double value : values) {
            sum += value * value;
        }
        return sum;
    }

    /**
     * Extract 53 bits from 8 bytes of HMAC output starting at {@code offset} and scale to [0, 1).
     */
    private static double extractUniform(byte[] hmacBytes, int offset) {
        long value = 0;
        for (int i = 0; i < 8; i++) {
            value = (value << 8) | (hmacBytes[offset + i] & 0xFF);
        }
        return ((value >>> 11) & (MANTISSA_BITS - 1)) * MANTISSA_SCALE;
    }

    /**
     * Return +1 or -1: the sign of det(Q) via Gaussian elimination with partial pivoting.
     */
    private static int computeDetSign(double[][] q, int n) {
        double[][] a = new double[n][];
        for (int i = 0; i < n; i++) {
            a[i] = q[i].clone();
        }
        int sign = 1;
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
        for (int i = 0; i < n; i++) {
            if (a[i][i] < 0) {
                sign = -sign;
            }
        }
        return sign;
    }

    private static byte[] longToBytes(long value) {
        byte[] bytes = new byte[8];
        for (int i = 7; i >= 0; i--) {
            bytes[i] = (byte) (value & 0xFF);
            value >>= 8;
        }
        return bytes;
    }

    private static byte[] sha256(byte[] data) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(data);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    private static byte[] hmacSha256(byte[] key, byte[] data) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(key, "HmacSHA256"));
            return mac.doFinal(data);
        } catch (NoSuchAlgorithmException | InvalidKeyException e) {
            throw new RuntimeException("HmacSHA256 not available", e);
        }
    }
}
